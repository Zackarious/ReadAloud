# test_audio_playback_fallback.py
#
# Copyright 2026 Walter Bernard / zackarious
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import tempfile
import unittest
import wave
from unittest.mock import MagicMock, patch

from src.audio_backend import (
    BaseAudioPlayer,
    GStreamerAudioPlayer,
    SoundDeviceAudioPlayer,
    WinSoundAudioPlayer,
    SubprocessAudioPlayer,
    get_best_gst_audio_sink,
    get_gst_audio_sink_candidates,
    get_audio_player_chain,
    create_audio_player,
)
from src.reader import Reader


class TestAudioPlaybackFallback(unittest.TestCase):
    """Test suite for audio sink discovery, player fallback chain, and Reader resilience."""

    @classmethod
    def setUpClass(cls):
        # Create a small valid WAV file for testing
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_wav = os.path.join(cls.temp_dir.name, "test.wav")
        with wave.open(cls.test_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b"\x00\x00" * 2205)  # 0.1 second of silence

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_gst_audio_sink_candidates(self):
        """Verify candidate list contains platform-specific sinks and standard elements."""
        candidates = get_gst_audio_sink_candidates()
        self.assertIsInstance(candidates, list)
        self.assertIn("autoaudiosink", candidates)
        self.assertIn("directsoundsink", candidates)
        self.assertIn("wasapisink", candidates)
        self.assertIn("pulsesink", candidates)

    def test_get_best_gst_audio_sink(self):
        """Verify best GStreamer audio sink returns an available element or None."""
        sink = get_best_gst_audio_sink()
        if sink is not None:
            self.assertIsInstance(sink, str)
            self.assertIn(sink, get_gst_audio_sink_candidates())

    def test_gstreamer_player_fallback_across_sinks(self):
        """Verify GStreamerAudioPlayer tries candidate sinks when autoaudiosink is absent."""
        from gi.repository import Gst

        player = GStreamerAudioPlayer()

        with patch("src.audio_backend.get_gst_audio_sink_candidates", return_value=["missingaudiosink", "autoaudiosink"]):
            with patch.object(Gst.ElementFactory, "find", side_effect=lambda name: True if name == "autoaudiosink" else None):
                success = player.play(self.test_wav)
                self.assertTrue(success)
                self.assertIsNotNone(player._pipeline)
                player.stop()

    def test_winsound_player_interface(self):
        """Verify WinSoundAudioPlayer methods when HAS_WINSOUND is simulated."""
        mock_winsound = MagicMock()
        with patch("src.audio_backend.HAS_WINSOUND", True):
            with patch.dict(sys.modules, {"winsound": mock_winsound}):
                import src.audio_backend as ab
                ab.winsound = mock_winsound

                p = WinSoundAudioPlayer()
                success = p.play(self.test_wav)
                self.assertTrue(success)
                self.assertGreater(p._duration, 0.0)

                mock_winsound.PlaySound.assert_called()

                pos = p.get_position()
                self.assertGreaterEqual(pos, 0.0)

                self.assertTrue(p.pause())
                self.assertTrue(p.resume())
                p.stop()
                self.assertFalse(p.seek(15))

    def test_subprocess_player_interface(self):
        """Verify SubprocessAudioPlayer methods and fallback behavior."""
        p = SubprocessAudioPlayer()
        self.assertFalse(p.seek(15))
        self.assertFalse(p.pause())
        self.assertFalse(p.resume())
        self.assertEqual(p.get_position(), -1.0)

    def test_get_audio_player_chain(self):
        """Verify fallback player chain returns an ordered list with at least one player."""
        chain = get_audio_player_chain()
        self.assertIsInstance(chain, list)
        self.assertGreater(len(chain), 0)
        for player in chain:
            self.assertIsInstance(player, BaseAudioPlayer)

    def test_create_audio_player(self):
        """Verify create_audio_player returns the primary player from chain."""
        player = create_audio_player()
        self.assertIsInstance(player, BaseAudioPlayer)

    def test_reader_play_fallback_when_gstreamer_fails(self):
        """
        Verify Reader._play_audio_file_async falls back to the next backend in chain
        when GStreamer fails with 'no element autoaudiosink'.
        """
        reader = Reader.__new__(Reader)
        reader._stopped = False
        reader._is_paused = False
        reader._current_pipeline = None
        reader._player = None

        mock_failing_gst = MagicMock(spec=GStreamerAudioPlayer)
        mock_failing_gst.play.side_effect = RuntimeError("gst_parse_error: no element \"autoaudiosink\" (1)")

        mock_fallback_player = MagicMock(spec=BaseAudioPlayer)
        mock_fallback_player.play.return_value = True
        mock_fallback_player.get_position.return_value = 1.25

        with patch("src.reader.get_audio_player_chain", return_value=[mock_failing_gst, mock_fallback_player]):
            reader._play_audio_file_async(self.test_wav)

            mock_failing_gst.play.assert_called_once()
            mock_fallback_player.play.assert_called_once()
            self.assertEqual(reader._player, mock_fallback_player)
            self.assertEqual(reader.get_playback_position(), 1.25)


if __name__ == "__main__":
    unittest.main()
