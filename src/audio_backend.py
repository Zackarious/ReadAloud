# audio_backend.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import time
import wave
import threading
from pathlib import Path

# Try importing GStreamer
HAS_GST = False
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    Gst.init(None)
    HAS_GST = True
except Exception:
    HAS_GST = False

# Try importing sounddevice for native fallback playback
HAS_SOUNDDEVICE = False
try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except Exception:
    HAS_SOUNDDEVICE = False

# Try importing lameenc for native WAV->MP3 encoding fallback
HAS_LAMEENC = False
try:
    import lameenc
    HAS_LAMEENC = True
except Exception:
    HAS_LAMEENC = False


class BaseAudioPlayer:
    """Abstract interface for audio playback with position tracking."""
    def play(self, file_path: str, on_eos=None, on_error=None, start_paused=False) -> bool:
        raise NotImplementedError

    def pause(self) -> bool:
        raise NotImplementedError

    def resume(self) -> bool:
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_position(self) -> float:
        """Returns current playback position in seconds, or -1.0 if not playing."""
        return -1.0

    def seek(self, seconds_delta: float) -> bool:
        """Seeks playback relatively by seconds_delta seconds."""
        return False


class GStreamerAudioPlayer(BaseAudioPlayer):
    """Audio player using GStreamer 1.0 (default on Linux and supported on Windows with GStreamer)."""

    def __init__(self):
        self._pipeline = None
        self._is_paused = False
        self._stopped = False
        self._on_eos = None
        self._on_error = None

    def play(self, file_path: str, on_eos=None, on_error=None, start_paused=False) -> bool:
        self.stop()
        self._stopped = False
        self._is_paused = start_paused
        self._on_eos = on_eos
        self._on_error = on_error

        try:
            # Normalize file path for GStreamer pipeline
            clean_path = str(Path(file_path).resolve()).replace("\\", "/")
            pipeline_str = f'filesrc location="{clean_path}" ! decodebin ! audioconvert ! audioresample ! autoaudiosink'
            self._pipeline = Gst.parse_launch(pipeline_str)
            if not self._pipeline:
                raise RuntimeError("Failed to create GStreamer pipeline")

            bus = self._pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message)

            initial_state = Gst.State.PAUSED if start_paused else Gst.State.PLAYING
            ret = self._pipeline.set_state(initial_state)
            if ret == Gst.StateChangeReturn.FAILURE:
                raise RuntimeError("Failed to set GStreamer pipeline state")
            return True
        except Exception as e:
            self.stop()
            if self._on_error:
                self._on_error(str(e))
            return False

    def _on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.stop()
            if self._on_eos:
                self._on_eos()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.stop()
            if self._on_error:
                self._on_error(f"{err}: {debug}")

    def pause(self) -> bool:
        self._is_paused = True
        if self._pipeline:
            ret = self._pipeline.set_state(Gst.State.PAUSED)
            return ret != Gst.StateChangeReturn.FAILURE
        return True

    def resume(self) -> bool:
        self._is_paused = False
        if self._pipeline:
            ret = self._pipeline.set_state(Gst.State.PLAYING)
            return ret != Gst.StateChangeReturn.FAILURE
        return False

    def stop(self):
        self._stopped = True
        self._is_paused = False
        if self._pipeline:
            try:
                bus = self._pipeline.get_bus()
                if bus:
                    bus.remove_signal_watch()
            except Exception:
                pass
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None

    def get_position(self) -> float:
        if self._pipeline:
            success, pos_ns = self._pipeline.query_position(Gst.Format.TIME)
            if success and pos_ns >= 0:
                return pos_ns / Gst.SECOND
        return -1.0

    def seek(self, seconds_delta: float) -> bool:
        if not self._pipeline:
            return False
        try:
            success, pos_ns = self._pipeline.query_position(Gst.Format.TIME)
            if not success or pos_ns < 0:
                return False
            success_dur, dur_ns = self._pipeline.query_duration(Gst.Format.TIME)
            max_ns = dur_ns if (success_dur and dur_ns > 0) else None
            delta_ns = int(seconds_delta * Gst.SECOND)
            target_ns = max(0, pos_ns + delta_ns)
            if max_ns is not None:
                target_ns = min(target_ns, max(0, max_ns - int(0.2 * Gst.SECOND)))
            flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT
            res = self._pipeline.seek_simple(Gst.Format.TIME, flags, target_ns)
            return bool(res)
        except Exception:
            return False


class SoundDeviceAudioPlayer(BaseAudioPlayer):
    """
    Pure Python/C fallback audio player using sounddevice and numpy.
    Provides sample-accurate position tracking on Windows without GStreamer.
    """

    def __init__(self):
        self._stream = None
        self._audio_data = None
        self._sample_rate = 22050
        self._current_frame = 0
        self._is_paused = False
        self._stopped = False
        self._on_eos = None
        self._on_error = None
        self._lock = threading.Lock()

    def play(self, file_path: str, on_eos=None, on_error=None, start_paused=False) -> bool:
        self.stop()
        self._stopped = False
        self._is_paused = start_paused
        self._on_eos = on_eos
        self._on_error = on_error
        self._current_frame = 0

        try:
            with wave.open(file_path, "rb") as wf:
                self._sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                n_frames = wf.getnframes()
                raw_bytes = wf.readframes(n_frames)

            dtype = np.int16 if sampwidth == 2 else np.uint8
            data = np.frombuffer(raw_bytes, dtype=dtype)
            if n_channels > 1:
                data = data.reshape(-1, n_channels)
            else:
                data = data.reshape(-1, 1)

            # Normalize to float32 for sounddevice
            self._audio_data = data.astype(np.float32) / 32768.0

            # Hardware Sample-Rate Auto-Resampling:
            # Shared-mode WASAPI/PortAudio requires hardware device sample rates (e.g. 44100 or 48000 Hz).
            # Interpolate frames dynamically if hardware output rate differs from source WAV.
            try:
                dev_info = sd.query_devices(kind='output')
                dev_sr = int(dev_info.get('default_samplerate', self._sample_rate))
                if dev_sr in (44100, 48000, 96000) and dev_sr != self._sample_rate:
                    orig_len = len(self._audio_data)
                    new_len = int(round(orig_len * dev_sr / self._sample_rate))
                    x_old = np.linspace(0.0, 1.0, orig_len)
                    x_new = np.linspace(0.0, 1.0, new_len)
                    if n_channels == 1:
                        resampled = np.interp(x_new, x_old, self._audio_data[:, 0])
                        self._audio_data = resampled.reshape(-1, 1).astype(np.float32)
                    else:
                        channels = [np.interp(x_new, x_old, self._audio_data[:, ch]) for ch in range(n_channels)]
                        self._audio_data = np.column_stack(channels).astype(np.float32)
                    self._sample_rate = dev_sr
            except Exception:
                pass

            def callback(outdata, frames, time_info, status):
                with self._lock:
                    if self._stopped or self._is_paused or self._audio_data is None:
                        outdata.fill(0)
                        return

                    remaining = len(self._audio_data) - self._current_frame
                    if remaining <= 0:
                        outdata.fill(0)
                        raise sd.CallbackStop()

                    chunk_size = min(frames, remaining)
                    outdata[:chunk_size] = self._audio_data[self._current_frame:self._current_frame + chunk_size]
                    if chunk_size < frames:
                        outdata[chunk_size:].fill(0)
                    self._current_frame += chunk_size

            def finished_callback():
                if not self._stopped and self._current_frame >= len(self._audio_data):
                    if self._on_eos:
                        self._on_eos()

            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=n_channels,
                callback=callback,
                finished_callback=finished_callback,
            )
            self._stream.start()
            return True
        except Exception as e:
            self.stop()
            if self._on_error:
                self._on_error(str(e))
            return False

    def pause(self) -> bool:
        with self._lock:
            self._is_paused = True
        return True

    def resume(self) -> bool:
        with self._lock:
            self._is_paused = False
        return True

    def stop(self):
        with self._lock:
            self._stopped = True
            self._is_paused = False
            self._audio_data = None
            self._current_frame = 0

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def get_position(self) -> float:
        with self._lock:
            if self._audio_data is not None and self._sample_rate > 0:
                return self._current_frame / float(self._sample_rate)
        return -1.0

    def seek(self, seconds_delta: float) -> bool:
        with self._lock:
            if self._audio_data is None or self._sample_rate <= 0:
                return False
            current_sec = self._current_frame / float(self._sample_rate)
            target_sec = max(0.0, current_sec + seconds_delta)
            total_sec = len(self._audio_data) / float(self._sample_rate)
            target_sec = min(target_sec, max(0.0, total_sec - 0.2))
            self._current_frame = int(target_sec * self._sample_rate)
            return True


def create_audio_player() -> BaseAudioPlayer:
    """Factory creating best available audio player."""
    if sys.platform == "win32" and HAS_SOUNDDEVICE:
        return SoundDeviceAudioPlayer()
    if HAS_GST:
        return GStreamerAudioPlayer()
    elif HAS_SOUNDDEVICE:
        return SoundDeviceAudioPlayer()
    else:
        # Fallback dummy player if neither is available
        return BaseAudioPlayer()


def convert_wav_to_mp3(src_wav_path: str, dest_mp3_path: str, bitrate: int = 64, mono: bool = True):
    """
    Converts a WAV file to MP3 (default 64 kbps mono CBR).
    Uses GStreamer lamemp3enc if available; falls back to lameenc Python library.
    """
    # 1. Try GStreamer lamemp3enc
    if HAS_GST:
        try:
            mono_str = "true" if mono else "false"
            clean_src = str(Path(src_wav_path).resolve()).replace("\\", "/")
            clean_dest = str(Path(dest_mp3_path).resolve()).replace("\\", "/")
            pipe_str = (
                f'filesrc location="{clean_src}" ! decodebin ! audioconvert ! audioresample ! '
                f'lamemp3enc bitrate={bitrate} mono={mono_str} cbr=true ! id3v2mux ! filesink location="{clean_dest}"'
            )
            pipeline = Gst.parse_launch(pipe_str)
            if pipeline:
                pipeline.set_state(Gst.State.PLAYING)
                bus = pipeline.get_bus()
                msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)
                pipeline.set_state(Gst.State.NULL)
                if msg and msg.type == Gst.MessageType.EOS:
                    return
                elif msg and msg.type == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    print(f"GStreamer MP3 encoding failed: {err} ({debug}), attempting fallback...")
        except Exception as e:
            print(f"GStreamer encoding error: {e}, attempting fallback...")

    # 2. Try lameenc (Python wheel, highly reliable on Windows without GStreamer plugins)
    if HAS_LAMEENC:
        with wave.open(src_wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            pcm_data = wf.readframes(wf.getnframes())

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(n_channels)
        encoder.set_quality(2)  # High quality encoding
        mp3_data = encoder.encode(pcm_data)
        mp3_data += encoder.flush()

        with open(dest_mp3_path, "wb") as f:
            f.write(mp3_data)
        return

    # 3. Try system lame CLI encoder
    try:
        import subprocess
        cmd = ["lame", "-b", str(bitrate), src_wav_path, dest_mp3_path]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.isfile(dest_mp3_path):
            return
    except Exception:
        pass

    raise RuntimeError(
        "MP3 encoding failed: Neither GStreamer lamemp3enc, lameenc, nor lame CLI encoder is available."
    )
