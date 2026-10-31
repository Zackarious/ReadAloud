# tests/test_editable_during_playback.py
import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from src.window import ReadAloudWindow

class TestEditableDuringPlayback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_text_view_locked_during_playback_and_unlocked_on_stop(self):
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.main_text_view = Gtk.TextView()
        window.read_button = Gtk.Button()
        window.pause_button = Gtk.Button()
        window.is_playing = False
        window.is_paused = False
        window._highlight_timeout_id = None
        window.lang_code = "en_GB"

        # Mock helper methods to avoid full GTK/Reader pipeline startup
        window._set_button_icon = lambda *args: None
        window._clear_highlight = lambda: None

        # 1. Initially editable
        self.assertTrue(window.main_text_view.get_editable())

        # 2. Start playback - should disable editing
        # Create a mock Reader to avoid disk/sound synthesis in unit test
        class DummyReader:
            def __init__(self, *args, **kwargs):
                pass
            def stop_audio(self):
                pass

        orig_reader_cls = None
        import src.window
        orig_reader_cls = src.window.Reader
        src.window.Reader = DummyReader
        try:
            window.start_playback(
                window.read_button,
                "Test text",
                "piper",
                "en_GB",
                "en_GB-alan-low",
                1.0,
                1.0
            )

            self.assertTrue(window.is_playing)
            self.assertFalse(window.main_text_view.get_editable(), "Text view must be locked during playback")

            # 3. Stop playback - should re-enable editing
            window.stop_playback(window.read_button)
            self.assertFalse(window.is_playing)
            self.assertTrue(window.main_text_view.get_editable(), "Text view must be unlocked when playback stops")
        finally:
            src.window.Reader = orig_reader_cls

if __name__ == "__main__":
    unittest.main()
