import unittest
from unittest.mock import MagicMock, patch
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, Adw

from src.window import ReadAloudWindow


class TestPlaybackSeekButtons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Adw.Application(application_id="im.zackarious.ReadAloud.TestSeekButtons")

    def setUp(self):
        self.window = ReadAloudWindow.__new__(ReadAloudWindow)
        # Setup mock widgets
        self.window.rewind_button = Gtk.Button()
        self.window.forward_button = Gtk.Button()
        self.window.stop_button = Gtk.Button()
        self.window.read_button = Gtk.Button()
        self.window.pause_button = Gtk.Button()
        self.window.save_button = Gtk.Button()
        self.window.playback_toolbar_revealer = Gtk.Revealer()
        self.window.playback_toolbar = Gtk.Box()
        self.window.main_text_view = Gtk.TextView()
        self.window.tab_view = MagicMock()
        self.window.is_playing = False
        self.window.is_paused = False
        self.window._highlight_timeout_id = None
        self.window._current_highlight_index = None
        self.window.default_settings = {}
        self.window.lang_code = "en"
        self.window.bubble = None

    def tearDown(self):
        if hasattr(self, "window") and self.window:
            self.window.is_playing = False
            self.window.is_paused = False

    def test_initial_visibility_is_hidden(self):
        """Popup toolbar should be hidden and read_button visible initially when playback is not in progress."""
        self.window._update_playback_toolbar_visibility()
        self.assertFalse(self.window.playback_toolbar_revealer.get_reveal_child())
        self.assertTrue(self.window.read_button.get_visible())
        self.assertFalse(self.window.rewind_button.get_visible())
        self.assertFalse(self.window.forward_button.get_visible())
        self.assertFalse(self.window.stop_button.get_visible())

    def test_buttons_visible_when_playback_starts(self):
        """Starting playback should reveal popup toolbar and hide read_button on fixed bar."""
        mock_reader = MagicMock()
        mock_reader.temp_path = None
        with patch("src.window.Reader", return_value=mock_reader):
            self.window.start_playback(
                self.window.read_button,
                "Test sentence for playback.",
                "piper",
                "en",
                "en_GB-alba-medium",
                1.0,
                1.0
            )
            self.assertTrue(self.window.is_playing)
            self.assertTrue(self.window.playback_toolbar_revealer.get_reveal_child())
            self.assertFalse(self.window.read_button.get_visible())
            self.assertTrue(self.window.rewind_button.get_visible())
            self.assertTrue(self.window.forward_button.get_visible())
            self.assertTrue(self.window.stop_button.get_visible())
            self.assertTrue(self.window.pause_button.get_sensitive())

    def test_buttons_hidden_when_playback_stops(self):
        """Stopping playback should collapse popup toolbar and restore read_button on fixed bar."""
        self.window.is_playing = True
        self.window._update_playback_toolbar_visibility()

        self.window.stop_playback(self.window.read_button)
        self.assertFalse(self.window.is_playing)
        self.assertFalse(self.window.playback_toolbar_revealer.get_reveal_child())
        self.assertTrue(self.window.read_button.get_visible())
        self.assertFalse(self.window.rewind_button.get_visible())
        self.assertFalse(self.window.forward_button.get_visible())
        self.assertFalse(self.window.stop_button.get_visible())
        self.assertFalse(self.window.pause_button.get_sensitive())

    def test_buttons_remain_visible_when_paused(self):
        """When playback is paused, popup toolbar remains revealed."""
        self.window.is_playing = True
        self.window.is_paused = True
        self.window._update_playback_toolbar_visibility()

        self.assertTrue(self.window.playback_toolbar_revealer.get_reveal_child())
        self.assertFalse(self.window.read_button.get_visible())
        self.assertTrue(self.window.rewind_button.get_visible())
        self.assertTrue(self.window.forward_button.get_visible())
        self.assertTrue(self.window.stop_button.get_visible())

    def test_rewind_15s_delegates_to_seek_playback(self):
        """rewind_15s calls seek_playback with -15 seconds."""
        with patch.object(self.window, "seek_playback", return_value=True) as mock_seek:
            res = self.window.rewind_15s()
            mock_seek.assert_called_once_with(-15)
            self.assertTrue(res)

    def test_forward_15s_delegates_to_seek_playback(self):
        """forward_15s calls seek_playback with +15 seconds."""
        with patch.object(self.window, "seek_playback", return_value=True) as mock_seek:
            res = self.window.forward_15s()
            mock_seek.assert_called_once_with(15)
            self.assertTrue(res)

    def test_tab_switch_updates_playback_toolbar_visibility(self):
        """Switching tabs updates popup toolbar visibility based on the active tab playback state."""
        page1 = MagicMock()
        page1._reader = MagicMock()
        page1._is_playing = True
        page1._is_paused = True
        page1._highlight_index = 0

        page2 = MagicMock()
        page2._reader = None
        page2._is_playing = False
        page2._is_paused = False
        page2._highlight_index = None

        self.window.tab_view.get_selected_page.return_value = page2
        self.window._on_selected_page_changed(self.window.tab_view, None)
        self.assertFalse(self.window.playback_toolbar_revealer.get_reveal_child())
        self.assertTrue(self.window.read_button.get_visible())

        self.window.tab_view.get_selected_page.return_value = page1
        self.window._on_selected_page_changed(self.window.tab_view, None)
        self.assertTrue(self.window.playback_toolbar_revealer.get_reveal_child())
        self.assertFalse(self.window.read_button.get_visible())

    def test_ctrl_left_right_shortcuts_during_playback(self):
        """Ctrl+Left and Ctrl+Right trigger rewind and forward when playback is in progress."""
        self.window.is_playing = True
        with patch.object(self.window, "rewind_15s") as mock_rewind,              patch.object(self.window, "forward_15s") as mock_forward:

            handled = self.window._on_key_pressed(None, Gdk.KEY_Left, 0, Gdk.ModifierType.CONTROL_MASK)
            self.assertTrue(handled)
            mock_rewind.assert_called_once()

            handled = self.window._on_key_pressed(None, Gdk.KEY_Right, 0, Gdk.ModifierType.CONTROL_MASK)
            self.assertTrue(handled)
            mock_forward.assert_called_once()

    def test_ctrl_left_right_shortcuts_ignored_when_idle(self):
        """Ctrl+Left and Ctrl+Right do not trigger seeking when playback is stopped."""
        self.window.is_playing = False
        with patch.object(self.window, "rewind_15s") as mock_rewind,              patch.object(self.window, "forward_15s") as mock_forward:

            handled_left = self.window._on_key_pressed(None, Gdk.KEY_Left, 0, Gdk.ModifierType.CONTROL_MASK)
            self.assertFalse(handled_left)
            mock_rewind.assert_not_called()

            handled_right = self.window._on_key_pressed(None, Gdk.KEY_Right, 0, Gdk.ModifierType.CONTROL_MASK)
            self.assertFalse(handled_right)
            mock_forward.assert_not_called()

    def test_template_instantiation_has_popup_toolbar_and_stop_button(self):
        """Verify ReadAloudWindow template initializes popup toolbar revealer, buttons and styling."""
        app = Adw.Application(application_id="im.zackarious.ReadAloud.TemplateSeekTest")
        app.connect("activate", lambda a: None)
        app.register(None)
        win = ReadAloudWindow(application=app)
        self.assertIsNotNone(win.playback_toolbar_revealer)
        self.assertIsNotNone(win.playback_toolbar)
        self.assertIsNotNone(win.stop_button)
        self.assertFalse(win.playback_toolbar_revealer.get_reveal_child())
        self.assertTrue(win.read_button.get_visible())


if __name__ == "__main__":
    unittest.main()
