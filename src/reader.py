# reader.py
#
# Copyright 2025 Walter Bernard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import traceback
import array
import time
import math
import tempfile
import io
import wave
import struct
import numpy as np
import shutil
from pathlib import Path
import threading
import re
import gettext
_ = gettext.gettext

import gi
from gi.repository import GLib

from .pipervoice import VoiceManager
from .vocxpo import convert_text_for_eo_voice
from .paths import get_model_search_paths
from .audio_backend import (
    create_audio_player,
    get_audio_player_chain,
    GStreamerAudioPlayer,
    convert_wav_to_mp3,
    HAS_GST,
)

if HAS_GST:
    from gi.repository import Gst

try:
    from piper import PiperVoice, SynthesisConfig
except ImportError:
    PiperVoice = None
    SynthesisConfig = None

COMMON_ABBREVIATIONS = {
    'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'vs', 'etc',
    'eg', 'ie', 'fig', 'al', 'approx', 'app', 'dept', 'est',
    'govt', 'inc', 'corp', 'co', 'ltd', 'jan', 'feb', 'mar',
    'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'st',
    'am', 'pm'
}

def is_abbreviation_or_initial(text: str, dot_pos: int) -> bool:
    """Check if the dot at dot_pos in text is part of an abbreviation, initial, decimal, or URL."""
    # 1. Decimal number (e.g. 3.14)
    if dot_pos > 0 and dot_pos + 1 < len(text):
        if text[dot_pos - 1].isdigit() and text[dot_pos + 1].isdigit():
            return True

    # 2. Two-letter abbreviations with dots like a.m., p.m., e.g., i.e.
    if dot_pos >= 3 and text[dot_pos - 2] == '.' and text[dot_pos - 1].isalpha() and text[dot_pos - 3].isalpha():
        next_text = text[dot_pos + 1:].lstrip()
        if not next_text or next_text[0].islower() or next_text[0].isdigit():
            return True

    # 3. Extract preceding alphanumeric token
    start = dot_pos - 1
    while start >= 0 and (text[start].isalnum() or text[start] in ('-', '_')):
        start -= 1
    token = text[start + 1:dot_pos].lower()

    if token in COMMON_ABBREVIATIONS:
        return True

    # Single uppercase initial (e.g. 'J.' in 'J. K. Rowling')
    if len(token) == 1 and text[start + 1:dot_pos].isupper():
        return True

    # Multi-dot sequence (e.g. e.g. or i.e.)
    if token in ('e', 'i', 'u', 'p', 'a') and dot_pos + 2 < len(text) and text[dot_pos + 2] == '.':
        return True

    # Check for domain / URL pattern (e.g. .com, .org, .local:8080)
    after = text[dot_pos + 1:dot_pos + 15]
    if re.match(r'^(com|org|net|edu|gov|io|local)(:\d+)?(\b|/|$)', after):
        return True

    return False


def extract_sentences_and_words(text: str, base_offset: int = 0):
    """
    Splits text into sentences and constituent words, recording exact character spans
    in the original text (shifted by base_offset) and estimating phonetic weights for word duration allocation.

    Features:
    - Distinguishes soft line wraps (PDF multi-column lines) from true paragraph breaks.
    - Normalizes soft line breaks for Piper TTS synthesis without awkward pauses.
    - Protects abbreviations, initials, decimals, and URLs from premature sentence splitting.
    - Accurately tracks original buffer character slices for visual word highlighting.
    """
    sentences = []
    if not text:
        return sentences

    # Find paragraphs separated by 2+ newlines or terminal paragraph blocks
    para_pattern = re.compile(r'[^\n\r]+(?:[\r\n]+(?![ \t]*[\r\n])[^\n\r]+)*')
    for pm in para_pattern.finditer(text):
        para_raw = pm.group()
        p_offset = pm.start()

        i = 0
        p_len = len(para_raw)
        s_start = 0

        while i < p_len:
            ch = para_raw[i]
            if ch in ('.', '!', '?'):
                end_punct = i + 1
                while end_punct < p_len and para_raw[end_punct] in ('\"', '\'', '”', '’', ')', ']', '}'):
                    end_punct += 1

                if ch == '.' and is_abbreviation_or_initial(para_raw, i):
                    i = end_punct
                    continue

                following = para_raw[end_punct:].lstrip()
                if ch == '.' and following and following[0].islower():
                    i = end_punct
                    continue

                if end_punct == p_len or para_raw[end_punct] in (' ', '\t', '\n', '\r'):
                    sent_raw = para_raw[s_start:end_punct]
                    stripped = sent_raw.strip()
                    if stripped:
                        lead_ws = len(sent_raw) - len(sent_raw.lstrip())
                        cur_start = base_offset + p_offset + s_start + lead_ws
                        cur_end = cur_start + len(stripped)

                        # Deliver normalized space-joined text to Piper with hyphenated breaks joined
                        synth_text = re.sub(r'(\b\w+)-\s*[\r\n]+\s*(\w+\b)', r'\1\2', stripped)
                        synth_text = re.sub(r'[\r\n]+', ' ', synth_text)
                        synth_text = re.sub(r'[ \t]+', ' ', synth_text).strip()

                        words = _extract_words_from_span(stripped, cur_start)
                        if words:
                            sentences.append({
                                'sentence_text': synth_text if synth_text else stripped,
                                'start_char': cur_start,
                                'end_char': cur_end,
                                'words': words
                            })
                    s_start = end_punct
                    i = end_punct
                    continue
            i += 1

        if s_start < p_len:
            sent_raw = para_raw[s_start:]
            stripped = sent_raw.strip()
            if stripped:
                lead_ws = len(sent_raw) - len(sent_raw.lstrip())
                cur_start = base_offset + p_offset + s_start + lead_ws
                cur_end = cur_start + len(stripped)

                synth_text = re.sub(r'(\b\w+)-\s*[\r\n]+\s*(\w+\b)', r'\1\2', stripped)
                synth_text = re.sub(r'[\r\n]+', ' ', synth_text)
                synth_text = re.sub(r'[ \t]+', ' ', synth_text).strip()

                words = _extract_words_from_span(stripped, cur_start)
                if words:
                    sentences.append({
                        'sentence_text': synth_text if synth_text else stripped,
                        'start_char': cur_start,
                        'end_char': cur_end,
                        'words': words
                    })

    return sentences


def _extract_words_from_span(span_text: str, span_start_char: int):
    """Extracts words from a sentence span with exact buffer coordinates and phonetic weights."""
    words = []
    # Tokenize words, treating hyphenated line wraps (\w+-\n\w+) as single units or word tokens
    token_pattern = re.compile(r'\b\w+-\s*[\r\n]+\s*\w+\b|\S+')
    for wm in token_pattern.finditer(span_text):
        token = wm.group()
        token_start = span_start_char + wm.start()

        # Split tokens containing em-dash (—) or double-hyphen (--) into constituent words
        if '—' in token or '--' in token:
            sub_pattern = re.compile(r'[^\s—\-]+(?:—+|--+)?|[—]+|--+|[^\s—\-]+')
            sub_matches = list(sub_pattern.finditer(token))
        else:
            sub_matches = []

        if not sub_matches:
            sub_tokens = [(token, 0, len(token))]
        else:
            sub_tokens = [(sm.group(), sm.start(), sm.end()) for sm in sub_matches]

        for w_str, sub_start, sub_end in sub_tokens:
            w_start = token_start + sub_start
            w_end = token_start + sub_end

            # Estimate phonetic weight
            alpha = re.findall(r'\w', w_str)
            w = max(1.0, float(len(alpha)))
            vowels = re.findall(r'[aeiouyAEIOUYäöüÄÖÜáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙ]', w_str)
            w += len(vowels) * 0.5
            if w_str.endswith((',', ';', ':')):
                w += 2.0
            elif w_str.endswith(('.', '!', '?')):
                w += 3.0

            words.append({
                'word': w_str,
                'start_char': w_start,
                'end_char': w_end,
                'weight': w
            })

    return words


class Reader():
    # Constructor, initializes input values
    def __init__(self, text, engine, lang_code, selected_voice, pitch, speed, window=None, start_char_offset=0, play_audio=True, on_complete=None, hide_dialog_on_complete=True):
        self.window = window
        self.text = text
        self.engine = engine
        self.lang_code = lang_code  # de, it, eo, en
        self.pitch = pitch
        self.speed = speed
        self.selected_voice = selected_voice
        self.play_audio = play_audio
        self.on_complete = on_complete
        self.hide_dialog_on_complete = hide_dialog_on_complete
        if HAS_GST:
            try:
                Gst.init(None)
                self._init_gstreamer()
            except Exception:
                pass

        self._dialog_ready = threading.Event()
        self._player = None
        self._pipeline = None
        self._current_pipeline = None
        self._is_paused = False   # Pause intent: True even before pipeline exists
        self._stopped = False     # Explicit stop: prevents stale synthesis from playing
        self._cancelled = False   # Explicit cancel: immediately aborts background synthesis loop

        self.voicemanager = VoiceManager(self)

        self.original_text = text
        self.start_char_offset = start_char_offset
        self.word_timings = []

        if lang_code == "eo":
            text = convert_text_for_eo_voice(text)

        self.use_piper(text, lang_code, selected_voice, pitch, speed)

    def _init_gstreamer(self):
        """Initializes GStreamer Pipeline"""
        if not HAS_GST:
            return
        self.pipeline = Gst.Pipeline.new("audio-pipeline")
        self.src = Gst.ElementFactory.make("appsrc", "source")
        convert = Gst.ElementFactory.make("audioconvert", "converter")
        sink = Gst.ElementFactory.make("autoaudiosink", "sink")

        # Build pipeline
        for element in [self.src, convert, sink]:
            self.pipeline.add(element)
        self.src.link(convert)
        convert.link(sink)

    def get_voice_path(self, lang_code: str, voice_id: str) -> tuple[str, str]:
        """Searches for voices in bundled paths or user data."""
        search_paths = get_model_search_paths()

        for base_path in search_paths:
            model_path = base_path / f"{voice_id}.onnx"
            config_path = base_path / f"{voice_id}.onnx.json"
            if model_path.exists() and config_path.exists():
                return str(model_path), str(config_path)

        raise FileNotFoundError(f"Voice '{voice_id}' ({lang_code}) not found.")

    def use_piper(self, text, lang_code, selected_voice, pitch, speed):
        """Main method for speech synthesis"""

        # 1. Lock UI and show dialog
        GLib.idle_add(self._show_processing_ui)

        # 2. Start synthesis in background thread
        threading.Thread(
            target=self._synthesize_audio,
            args=(text, lang_code, selected_voice, pitch, speed),
            daemon=True
        ).start()

    def _reactivate_ui(self):
        """Reactivates the user interface"""
        if hasattr(self, 'window') and self.window:
            self.window.set_sensitive(True)
            self.window.hide_wait_dialog()

    def _show_processing_ui(self):
        """Shows waiting dialog and disables UI"""
        if self.window:
            self.window.set_sensitive(False)
            self.window.show_wait_dialog()
            self._dialog_ready.set()

    def _synthesize_audio(self, text, lang_code, voice, pitch, speed):
        """Audio synthesis in background thread"""
        self.temp_path = None
        try:
            # Wait until dialog is fully visible
            if not self._dialog_ready.wait(timeout=2.0):
                print("Warning: Could not display loading dialog.")

            if getattr(self, '_cancelled', False) or getattr(self, '_stopped', False):
                return

            voices = self.voicemanager.get_installed_voices(lang_code)
            voice_id = None
            # Prioritize exact voice ID match first, then fallback to matching voice name
            for v in voices:
                if v['id'] == self.selected_voice:
                    voice_id = v['id']
                    break
            if not voice_id:
                for v in voices:
                    if v['name'].lower() == self.selected_voice.lower():
                        voice_id = v['id']
                        break

            # Fallback to first available installed voice if selected voice is unavailable
            if not voice_id:
                if voices:
                    voice_id = voices[0]['id']
                else:
                    voice_id = self.selected_voice

            model_path, config_path = self.get_voice_path(lang_code, voice_id)

            if not (os.path.exists(model_path) and os.path.exists(config_path)):
                print("❌ Model or configuration missing.")
                return

            if getattr(self, '_cancelled', False) or getattr(self, '_stopped', False):
                return

            from .paths import get_espeak_data_dir
            espeak_dir = get_espeak_data_dir()
            load_kwargs = {}
            if espeak_dir:
                short_espeak = str(espeak_dir)
                if sys.platform == "win32":
                    try:
                        import ctypes
                        from ctypes import wintypes
                        _buf = ctypes.create_unicode_buffer(1024)
                        if ctypes.windll.kernel32.GetShortPathNameW(str(espeak_dir), _buf, 1024) > 0:
                            short_espeak = _buf.value
                    except Exception:
                        pass
                os.environ["ESPEAK_DATA_PATH"] = short_espeak
                os.environ["ESPEAK_DATA_DIR"] = short_espeak
                load_kwargs["espeak_data_dir"] = short_espeak

            # Enforce pre-flight validation to avoid silent native C exit(1) crash
            if not espeak_dir or not (Path(espeak_dir) / "phontab").is_file():
                raise RuntimeError(
                    f"Phonemization data (espeak-ng-data) not found at: {espeak_dir}. "
                    "Synthesis aborted safely."
                )

            print(f"[Reader] Loading Piper voice: {voice_id} (espeak_data_dir={load_kwargs.get('espeak_data_dir')})")
            self.p = PiperVoice.load(model_path, config_path, **load_kwargs)

            if getattr(self, '_cancelled', False) or getattr(self, '_stopped', False):
                return

            safe_speed = max(0.1, float(speed or 1.0))
            safe_pitch = max(0.1, float(pitch or 1.0))
            length_scale = 0.8 / safe_speed  # Modifies speed

            syn_config = SynthesisConfig(
                length_scale=length_scale
            )

            # Adjust sample rate for pitch modification
            self.p.config.sample_rate = int(safe_pitch * 19000)

            # Tokenize text into sentences and constituent words with exact offsets
            sentence_info = extract_sentences_and_words(self.original_text, base_offset=self.start_char_offset)
            if not sentence_info and text.strip():
                # Fallback if pattern matched no sentences
                sentence_info = [{
                    'sentence_text': text.strip(),
                    'start_char': self.start_char_offset,
                    'end_char': self.start_char_offset + len(text.strip()),
                    'words': [{
                        'word': text.strip(),
                        'start_char': self.start_char_offset,
                        'end_char': self.start_char_offset + len(text.strip()),
                        'weight': 1.0
                    }]
                }]

            self.word_timings = []
            current_audio_time = 0.0

            total_sentences = len(sentence_info)
            start_time = time.time()
            if hasattr(self, 'window') and self.window and hasattr(self.window, 'update_wait_dialog'):
                GLib.idle_add(self.window.update_wait_dialog, 0.0, _("Synthesizing audio..."))

            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                self._current_temp_file = f.name
                with wave.open(f, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)  # 16-bit
                    wav.setframerate(self.p.config.sample_rate)

                    for idx, sent in enumerate(sentence_info):
                        if getattr(self, '_cancelled', False) or getattr(self, '_stopped', False):
                            break

                        sent_text = sent['sentence_text']
                        if lang_code == "eo":
                            sent_text = convert_text_for_eo_voice(sent_text)

                        chunks = list(self.p.synthesize(sent_text, syn_config=syn_config))
                        if not chunks:
                            continue

                        sent_samples = sum(len(c.audio_int16_bytes) // 2 for c in chunks)
                        sent_duration = sent_samples / self.p.config.sample_rate

                        for c in chunks:
                            wav.writeframes(c.audio_int16_bytes)

                        words = sent['words']
                        total_weight = sum(w['weight'] for w in words)
                        if total_weight <= 0:
                            total_weight = 1.0
                        w_time = current_audio_time

                        for w in words:
                            w_dur = (w['weight'] / total_weight) * sent_duration
                            self.word_timings.append({
                                'start_time': w_time,
                                'end_time': w_time + w_dur,
                                'start_char': w['start_char'],
                                'end_char': w['end_char'],
                                'word': w['word']
                            })
                            w_time += w_dur

                        current_audio_time += sent_duration

                        # Update progress bar and estimated time countdown
                        completed = idx + 1
                        fraction = completed / total_sentences if total_sentences > 0 else 1.0
                        elapsed = time.time() - start_time
                        remaining_sents = total_sentences - completed
                        avg_per_sent = elapsed / completed if completed > 0 else 0
                        remaining_time = avg_per_sent * remaining_sents
                        percent = int(fraction * 100)

                        if remaining_sents == 0:
                            msg = _("Finalizing audio...")
                        elif remaining_time >= 1.5:
                            msg = _("Generating audio: {percent}% (~{seconds}s remaining)").format(
                                percent=percent,
                                seconds=max(1, round(remaining_time))
                            )
                        else:
                            msg = _("Generating audio: {percent}% (almost done)").format(
                                percent=percent
                            )

                        if hasattr(self, 'window') and self.window and hasattr(self.window, 'update_wait_dialog'):
                            GLib.idle_add(self.window.update_wait_dialog, fraction, msg)

                    if not (getattr(self, '_cancelled', False) or getattr(self, '_stopped', False)):
                        self.temp_path = f.name

            # Check if cancelled during synthesis
            if getattr(self, '_cancelled', False) or getattr(self, '_stopped', False):
                if getattr(self, '_current_temp_file', None) and os.path.exists(self._current_temp_file):
                    try:
                        os.unlink(self._current_temp_file)
                    except Exception:
                        pass
                self._current_temp_file = None
                self.temp_path = None
                GLib.idle_add(self._reactivate_ui)
                return

            self._current_temp_file = None

            # Close dialog BEFORE playback / completion (always use idle_add from bg thread)
            if self.hide_dialog_on_complete and hasattr(self, 'window') and self.window:
                GLib.idle_add(self.window.hide_wait_dialog)
                GLib.idle_add(self.window.set_sensitive, True)  # Thread-safe GTK call

            if self.play_audio and not getattr(self, '_stopped', False) and not getattr(self, '_cancelled', False):
                # Start playback with reactivation callback
                GLib.idle_add(
                    lambda: self._play_audio_file_async(
                        self.temp_path,
                        callback=lambda: self._reactivate_ui()
                    )
                )
            elif not self.play_audio and not getattr(self, '_stopped', False) and not getattr(self, '_cancelled', False):
                if self.on_complete:
                    GLib.idle_add(self.on_complete, self.temp_path)

        except Exception as e:
            tb_str = traceback.format_exc()
            GLib.idle_add(self._handle_error, str(e), self.temp_path, e, tb_str)

    def _handle_error(self, error_msg, temp_path=None, exc=None, traceback_text=None):
        """Centralized error handling"""
        print(f"Error: {error_msg}")
        if traceback_text:
            print(traceback_text)
        if self.window:
            self.window.hide_wait_dialog()
            self.window.set_sensitive(True)
            self.window.stop_playback()
            self.window._show_error(
                error_msg,
                exc=exc,
                traceback_text=traceback_text,
                context="Speech Synthesis",
            )

        if self.temp_path:
            try:
                os.unlink(self.temp_path)
            except:
                pass

    @staticmethod
    def convert_to_mp3(src_wav_path: str, dest_mp3_path: str, bitrate: int = 64, mono: bool = True):
        """Encodes WAV to MP3 (default 64 kbps mono CBR) with GStreamer and lameenc fallback"""
        convert_wav_to_mp3(src_wav_path, dest_mp3_path, bitrate=bitrate, mono=mono)

    def save_audio_file(self, file):  # Saves audio file with file chooser dialog
        if not self.temp_path or not os.path.exists(self.temp_path):
            raise FileNotFoundError("No synthesized audio is currently available to save.")

        dest_path = file.get_path() if hasattr(file, 'get_path') else str(file)

        if dest_path.lower().endswith(".wav"):
            shutil.copy2(self.temp_path, dest_path)
        else:
            if not dest_path.lower().endswith(".mp3"):
                dest_path = f"{dest_path}.mp3"
            self.convert_to_mp3(self.temp_path, dest_path, bitrate=64, mono=True)

    def play_cached_audio(self):
        """Plays the already synthesized audio file from the beginning."""
        if not self.temp_path or not os.path.exists(self.temp_path):
            return False
        self._stopped = False
        self._is_paused = False
        self._play_audio_file_async(self.temp_path, callback=lambda: self._reactivate_ui())
        return True

    def _play_audio_file_async(self, file_path, callback=None):
        """Secure audio playback with fallback across available audio backends."""
        # Guard: if this reader was explicitly stopped (replaced by a new one), do nothing
        if getattr(self, '_stopped', False):
            return

        # 1. Stop previous playback cleanly
        self.stop_audio()
        self._stopped = False
        start_paused = getattr(self, '_is_paused', False)

        def on_eos():
            print("Playback finished")
            if hasattr(self, 'window') and self.window:
                if getattr(self.window, 'reader', None) is self:
                    self.window.stop_playback()
            if callback:
                GLib.idle_add(callback)

        def on_error(err):
            print(f"Playback error: {err}")
            if hasattr(self, 'window') and self.window:
                if getattr(self.window, 'reader', None) is self:
                    self.window.stop_playback()
            if callback:
                GLib.idle_add(callback)

        # 2. Try players from the fallback chain
        chain = get_audio_player_chain()
        last_error = None
        for player in chain:
            try:
                success = player.play(
                    file_path,
                    on_eos=on_eos,
                    on_error=None,
                    start_paused=start_paused,
                )
                if success:
                    self._player = player
                    if isinstance(player, GStreamerAudioPlayer):
                        self._current_pipeline = player._pipeline
                    else:
                        self._current_pipeline = None
                    return
            except Exception as e:
                last_error = e
                continue

        print(f"Playback error: All audio backends failed to start playback ({last_error})")
        self.stop_audio()
        if callback:
            GLib.idle_add(callback)

    def _on_gst_message(self, bus, message, pipeline, file_path, callback):
        if message.type == Gst.MessageType.EOS:
            print("Playback finished")
            if hasattr(self, 'window') and self.window:
                # Only stop the window if this reader is still the active one
                if getattr(self.window, 'reader', None) is self:
                    self.window.stop_playback()
            if callback:
                GLib.idle_add(callback)
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Playback error: {err}, {debug}")
            pipeline.set_state(Gst.State.NULL)
            self._current_pipeline = None
            if hasattr(self, 'window') and self.window:
                # Only stop the window if this reader is still the active one
                if getattr(self.window, 'reader', None) is self:
                    self.window.stop_playback()
            if callback:
                GLib.idle_add(callback)

    def pause_audio(self):
        """Pauses current playback."""
        self._is_paused = True
        if hasattr(self, '_player') and self._player:
            return self._player.pause()
        if self._current_pipeline:
            ret = self._current_pipeline.set_state(Gst.State.PAUSED)
            return ret != Gst.StateChangeReturn.FAILURE
        # No pipeline yet (still synthesising) — intent recorded, report success
        return True

    def resume_audio(self):
        """Resumes paused playback"""
        self._is_paused = False
        if hasattr(self, '_player') and self._player:
            return self._player.resume()
        if self._current_pipeline:
            ret = self._current_pipeline.set_state(Gst.State.PLAYING)
            return ret != Gst.StateChangeReturn.FAILURE
        return False

    def get_playback_position(self) -> float:
        """Returns current playback position in seconds, or -1.0 if not playing"""
        if hasattr(self, '_player') and self._player:
            pos = self._player.get_position()
            if pos >= 0:
                return pos
        if self._current_pipeline:
            success, pos_ns = self._current_pipeline.query_position(Gst.Format.TIME)
            if success and pos_ns >= 0:
                return pos_ns / Gst.SECOND
        return -1.0

    def seek(self, seconds_delta: float) -> bool:
        """Seeks playback relatively by seconds_delta seconds (+15s forward, -15s backward)."""
        if hasattr(self, '_player') and self._player:
            return self._player.seek(seconds_delta)
        if not self._current_pipeline:
            return False
        try:
            success_pos, pos_ns = self._current_pipeline.query_position(Gst.Format.TIME)
            if not success_pos or pos_ns < 0:
                return False

            success_dur, dur_ns = self._current_pipeline.query_duration(Gst.Format.TIME)
            max_ns = dur_ns if (success_dur and dur_ns > 0) else None

            delta_ns = int(seconds_delta * Gst.SECOND)
            target_ns = max(0, pos_ns + delta_ns)
            if max_ns is not None:
                target_ns = min(target_ns, max(0, max_ns - int(0.2 * Gst.SECOND)))

            flags = Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT
            res = self._current_pipeline.seek_simple(Gst.Format.TIME, flags, target_ns)
            return bool(res)
        except Exception as e:
            print(f"Seek error: {e}")
            return False

    def cancel_synthesis(self):
        """Immediately aborts in-progress synthesis and discards partial artifacts."""
        self._cancelled = True
        self._stopped = True
        self._dialog_ready.set()
        for p in (getattr(self, '_current_temp_file', None), self.temp_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass
        self._current_temp_file = None
        self.temp_path = None
        self.stop_audio()

    def stop_audio(self):
        """Stops current playback."""
        self._stopped = True
        self._cancelled = True
        self._is_paused = False
        if hasattr(self, '_player') and self._player:
            try:
                self._player.stop()
            except Exception:
                pass
            self._player = None

        if self._current_pipeline:
            try:
                bus = self._current_pipeline.get_bus()
                if bus:
                    bus.remove_signal_watch()
            except Exception:
                pass
            self._current_pipeline.set_state(Gst.State.NULL)
            self._current_pipeline = None

    def _cleanup_pipeline(self, pipeline, file_path):
        """Cleans up pipeline resources"""
        if pipeline:
            pipeline.set_state(Gst.State.NULL)
            if hasattr(self, '_current_pipeline'):
                del self._current_pipeline

        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Deletion error: {e}")

    def _play_raw(self, samples, rate):
        """Plays raw audio data with GStreamer"""
        if not samples:
            return

        caps = Gst.Caps.from_string(
            f"audio/x-raw,format=S16LE,channels=1,rate={rate},layout=interleaved"
        )
        self.src.set_property("caps", caps)

        self.pipeline.set_state(Gst.State.PLAYING)
        buffer = Gst.Buffer.new_wrapped(samples.tobytes())
        self.src.emit("push-buffer", buffer)
        self.src.emit("end-of-stream")

        duration = len(samples) / rate
        GLib.timeout_add_seconds(int(duration) + 1, self._stop_audio)

    def _play_test_tone(self):
        """Fallback: 440Hz Sine Wave"""
        samples = array.array('h', [
            int(32767 * math.sin(2 * math.pi * 440 * i / 22050))
            for i in range(22050)
        ])
        self._play_raw(samples, 22050)
