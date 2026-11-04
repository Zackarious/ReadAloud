import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

from src.window import ReadAloudWindow
from src.reader import Reader

class TestCachedPlayback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow.__new__(ReadAloudWindow)
        self.window.main_text_view = Gtk.TextView()
        self.window.read_button = Gtk.Button()
        self.window.pause_button = Gtk.Button()
        self.window.is_playing = False
        self.window.is_paused = False
        self.window._highlight_timeout_id = None
        self.window._current_highlight_index = None
        self.window.lang_code = "en_GB"

        self.window._set_button_icon = lambda *args: None
        self.window._clear_highlight = lambda: None

        self.window.speed_chooser = MagicMock()
        self.window.speed_chooser.get_value.return_value = 1.0

        self.window._get_selected_voice_name = lambda: "en_GB-alan-low"
        self.window._get_pitch_for_voice = lambda v: 1.0

        # Tab view mock
        self.tab_view = MagicMock()
        self.window.tab_view = self.tab_view
        self.mock_page = MagicMock()
        self.mock_page._reader = None
        self.tab_view.get_selected_page.return_value = self.mock_page

    def tearDown(self):
        if getattr(self.window, '_highlight_timeout_id', None) is not None:
            GLib.source_remove(self.window._highlight_timeout_id)
            self.window._highlight_timeout_id = None
        self.window.is_playing = False

    def test_replaying_unmodified_text_reuses_cached_audio(self):
        """When text and speech settings are identical, start_playback reuses cached audio without creating a new Reader."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            # Create a mock cached reader
            cached_reader = MagicMock()
            cached_reader.temp_path = tmp_audio_path
            cached_reader.original_text = "Sample speech text"
            cached_reader.start_char_offset = 0
            cached_reader.selected_voice = "en_GB-alan-low"
            cached_reader.pitch = 1.0
            cached_reader.speed = 1.0
            cached_reader.lang_code = "en_GB"
            cached_reader.play_cached_audio.return_value = True

            self.window.reader = cached_reader
            self.mock_page._reader = cached_reader

            with patch('src.window.Reader') as mock_reader_cls:
                self.window.start_playback(
                    self.window.read_button,
                    "Sample speech text",
                    "piper",
                    "en_GB",
                    "en_GB-alan-low",
                    1.0,
                    1.0,
                    start_char_offset=0
                )

                # Reader constructor should NOT be called
                mock_reader_cls.assert_not_called()
                # play_cached_audio must be called
                cached_reader.play_cached_audio.assert_called_once()
                self.assertTrue(self.window.is_playing)
                self.assertFalse(self.window.is_paused)
                self.assertIs(self.window.reader, cached_reader)
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_modified_text_triggers_new_synthesis(self):
        """When text is modified, start_playback does not reuse cached audio and creates a new Reader."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            cached_reader = MagicMock()
            cached_reader.temp_path = tmp_audio_path
            cached_reader.original_text = "Old speech text"
            cached_reader.start_char_offset = 0
            cached_reader.selected_voice = "en_GB-alan-low"
            cached_reader.pitch = 1.0
            cached_reader.speed = 1.0
            cached_reader.lang_code = "en_GB"

            self.window.reader = cached_reader
            self.mock_page._reader = cached_reader

            new_reader_instance = MagicMock()
            with patch('src.window.Reader', return_value=new_reader_instance) as mock_reader_cls:
                self.window.start_playback(
                    self.window.read_button,
                    "New modified text",
                    "piper",
                    "en_GB",
                    "en_GB-alan-low",
                    1.0,
                    1.0,
                    start_char_offset=0
                )

                # New Reader must be instantiated
                mock_reader_cls.assert_called_once()
                self.assertIs(self.window.reader, new_reader_instance)
                self.assertIs(self.mock_page._reader, new_reader_instance)
                cached_reader.play_cached_audio.assert_not_called()
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_modified_voice_triggers_new_synthesis(self):
        """When voice is changed, start_playback creates a new Reader."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            cached_reader = MagicMock()
            cached_reader.temp_path = tmp_audio_path
            cached_reader.original_text = "Same speech text"
            cached_reader.start_char_offset = 0
            cached_reader.selected_voice = "en_GB-alan-low"
            cached_reader.pitch = 1.0
            cached_reader.speed = 1.0
            cached_reader.lang_code = "en_GB"

            self.window.reader = cached_reader
            self.mock_page._reader = cached_reader

            new_reader_instance = MagicMock()
            with patch('src.window.Reader', return_value=new_reader_instance) as mock_reader_cls:
                self.window.start_playback(
                    self.window.read_button,
                    "Same speech text",
                    "piper",
                    "en_GB",
                    "en_GB-cori-medium",
                    1.0,
                    1.0,
                    start_char_offset=0
                )

                mock_reader_cls.assert_called_once()
                self.assertIs(self.window.reader, new_reader_instance)
                cached_reader.play_cached_audio.assert_not_called()
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_modified_speed_triggers_new_synthesis(self):
        """When speed is changed, start_playback creates a new Reader."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            cached_reader = MagicMock()
            cached_reader.temp_path = tmp_audio_path
            cached_reader.original_text = "Same speech text"
            cached_reader.start_char_offset = 0
            cached_reader.selected_voice = "en_GB-alan-low"
            cached_reader.pitch = 1.0
            cached_reader.speed = 1.0
            cached_reader.lang_code = "en_GB"

            self.window.reader = cached_reader
            self.mock_page._reader = cached_reader

            new_reader_instance = MagicMock()
            with patch('src.window.Reader', return_value=new_reader_instance) as mock_reader_cls:
                self.window.start_playback(
                    self.window.read_button,
                    "Same speech text",
                    "piper",
                    "en_GB",
                    "en_GB-alan-low",
                    1.0,
                    1.25,
                    start_char_offset=0
                )

                mock_reader_cls.assert_called_once()
                self.assertIs(self.window.reader, new_reader_instance)
                cached_reader.play_cached_audio.assert_not_called()
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_modified_char_offset_triggers_new_synthesis(self):
        """When cursor starting offset changes, start_playback creates a new Reader."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            cached_reader = MagicMock()
            cached_reader.temp_path = tmp_audio_path
            cached_reader.original_text = "Same speech text"
            cached_reader.start_char_offset = 0
            cached_reader.selected_voice = "en_GB-alan-low"
            cached_reader.pitch = 1.0
            cached_reader.speed = 1.0
            cached_reader.lang_code = "en_GB"

            self.window.reader = cached_reader
            self.mock_page._reader = cached_reader

            new_reader_instance = MagicMock()
            with patch('src.window.Reader', return_value=new_reader_instance) as mock_reader_cls:
                self.window.start_playback(
                    self.window.read_button,
                    "Same speech text",
                    "piper",
                    "en_GB",
                    "en_GB-alan-low",
                    1.0,
                    1.0,
                    start_char_offset=5
                )

                mock_reader_cls.assert_called_once()
                self.assertIs(self.window.reader, new_reader_instance)
                cached_reader.play_cached_audio.assert_not_called()
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_reader_play_cached_audio_resets_stopped_and_invokes_playback(self):
        """Reader.play_cached_audio resets _stopped and _is_paused, and starts playback."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            tmp_audio_path = tmp_audio.name

        try:
            reader = Reader.__new__(Reader)
            reader.temp_path = tmp_audio_path
            reader._stopped = True
            reader._is_paused = True
            reader.window = self.window
            reader._play_audio_file_async = MagicMock()

            result = reader.play_cached_audio()

            self.assertTrue(result)
            self.assertFalse(reader._stopped)
            self.assertFalse(reader._is_paused)
            reader._play_audio_file_async.assert_called_once()
        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

    def test_tab_switch_syncs_reader_and_pauses_playback(self):
        """Switching tabs pauses active playback and updates window.reader to the active tab's cached reader."""
        self.window.is_playing = True
        mock_reader = MagicMock()
        self.window.reader = mock_reader
        self.window._get_current_playback_char_offset = MagicMock(return_value=15)

        page1 = MagicMock()
        page1._reader = mock_reader
        page1.get_child.return_value.get_child.return_value = Gtk.TextView()
        self.window._active_tab_page = page1

        page2_reader = MagicMock()
        page2 = MagicMock()
        page2._reader = page2_reader
        page2._is_playing = False
        page2._is_paused = False
        self.tab_view.get_selected_page.return_value = page2

        self.window._on_selected_page_changed(self.tab_view, None)

        mock_reader.pause_audio.assert_called_once()
        self.assertTrue(page1._is_paused)
        self.assertEqual(page1._paused_offset, 15)
        self.assertIs(self.window.reader, page2_reader)
        self.assertFalse(self.window.is_playing)

if __name__ == '__main__':
    unittest.main()
