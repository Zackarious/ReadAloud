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

class TestSystemIntegrity(unittest.TestCase):
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

        self.error_messages = []
        self.window._show_error = lambda msg: self.error_messages.append(msg)

        self.tab_view = MagicMock()
        self.window.tab_view = self.tab_view
        self.mock_page = MagicMock()
        self.mock_page._reader = None
        self.mock_page.get_title.return_value = "Untitled Document"
        self.tab_view.get_selected_page.return_value = self.mock_page
        self.window._get_text_for_page = lambda p: ""

    def tearDown(self):
        if getattr(self.window, '_highlight_timeout_id', None) is not None:
            GLib.source_remove(self.window._highlight_timeout_id)
            self.window._highlight_timeout_id = None
        self.window.is_playing = False

    def test_open_response_cancelled_handled_cleanly(self):
        """When user dismisses open file dialog, on_open_response handles the GError without crashing."""
        mock_dialog = MagicMock()
        mock_dialog.open_finish.side_effect = GLib.GError("Dismissed by user")
        
        # Must not raise an unhandled exception
        self.window.on_open_response(mock_dialog, MagicMock())
        self.assertEqual(len(self.error_messages), 0)

    def test_save_text_response_cancelled_handled_cleanly(self):
        """When user dismisses save file dialog, on_save_text_response handles the GError without crashing."""
        mock_dialog = MagicMock()
        mock_dialog.save_finish.side_effect = GLib.GError("Dismissed by user")
        
        # Must not raise an unhandled exception
        self.window.on_save_text_response(mock_dialog, MagicMock())
        self.assertEqual(len(self.error_messages), 0)

    def test_open_file_complete_load_error_shows_friendly_message(self):
        """When file loading raises a Gio error (e.g. missing file), shows error dialog cleanly."""
        mock_file = MagicMock()
        mock_file.load_contents_finish.side_effect = GLib.GError("No such file or directory")

        self.window.open_file_complete(mock_file, MagicMock())
        self.assertEqual(len(self.error_messages), 1)
        self.assertIn("Unable to open file", self.error_messages[0])

    def test_open_file_complete_latin1_fallback(self):
        """When a file is encoded in Latin-1 instead of UTF-8, it falls back and decodes successfully."""
        mock_file = MagicMock()
        mock_file.get_basename.return_value = "latin1_sample.txt"
        latin1_bytes = "Café résumé".encode("latin-1")
        mock_file.load_contents_finish.return_value = (True, latin1_bytes, "etag")

        self.window.open_file_complete(mock_file, MagicMock())
        buffer = self.window.main_text_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        self.assertEqual(text, "Café résumé")
        self.mock_page.set_title.assert_called_with("latin1_sample.txt")

    def test_save_text_complete_error_shows_friendly_message(self):
        """When saving text fails, shows error message without crashing."""
        mock_file = MagicMock()
        mock_file.replace_contents_finish.side_effect = GLib.GError("Permission denied")

        self.window.save_text_complete(mock_file, MagicMock())
        self.assertEqual(len(self.error_messages), 1)
        self.assertIn("Unable to save file", self.error_messages[0])

    def test_read_text_none_text_view_is_safe(self):
        """read_text handles None main_text_view without raising AttributeError."""
        self.window._override_main_text_view = None
        self.tab_view.get_selected_page.return_value = None
        # Should return safely
        self.window.read_text(self.window.read_button)
        self.assertEqual(len(self.error_messages), 0)

    def test_save_text_none_text_view_is_safe(self):
        """save_text handles None main_text_view without raising AttributeError."""
        self.window._override_main_text_view = None
        self.tab_view.get_selected_page.return_value = None
        self.window.save_text(MagicMock())
        self.assertEqual(len(self.error_messages), 0)

    def test_read_text_when_playing_stops_playback_directly(self):
        """When read_button is clicked during playback, it stops playback immediately."""
        self.window.is_playing = True
        stopped = []
        self.window.stop_playback = lambda btn: stopped.append(True)
        # Empty text buffer
        self.window.main_text_view.get_buffer().set_text("")

        self.window.read_text(self.window.read_button)
        self.assertEqual(len(stopped), 1)
        self.assertEqual(len(self.error_messages), 0)

    def test_read_text_empty_shows_friendly_error(self):
        """When user clicks Read Text on empty buffer, friendly error is displayed."""
        self.window.main_text_view.get_buffer().set_text("   \n\t  ")
        self.window.read_text(self.window.read_button)
        self.assertEqual(len(self.error_messages), 1)
        self.assertEqual(self.error_messages[0], "No text to read!")

    def test_get_current_playback_char_offset_handles_non_numeric_position(self):
        """Non-numeric position query returns fallback start offset without raising TypeError."""
        reader = MagicMock()
        reader.get_playback_position.return_value = MagicMock()  # Not a float/int
        reader.word_timings = [{'start_time': 0.0, 'end_time': 1.0, 'start_char': 0, 'end_char': 4}]
        reader.start_char_offset = 12
        self.window.reader = reader

        offset = self.window._get_current_playback_char_offset()
        self.assertEqual(offset, 12)

    def test_export_all_tabs_empty_shows_friendly_error(self):
        """When attempting to export all tabs with no text in any tab, friendly error is displayed."""
        self.window._get_text_for_page = lambda p: ""
        self.tab_view.get_n_pages.return_value = 2
        self.window._export_all_tabs_audio_dialog()
        self.assertEqual(len(self.error_messages), 1)
        self.assertEqual(self.error_messages[0], "No text in any open tab to export!")

    def test_default_window_dimensions_on_load(self):
        """Default window dimensions in window.ui has default-height 700 (extended by 200px) and default-width 700."""
        import xml.etree.ElementTree as ET
        ui_path = os.path.join(os.path.dirname(__file__), "..", "src", "window.ui")
        tree = ET.parse(ui_path)
        root = tree.getroot()
        template = root.find(".//template[@class='ReadAloudWindow']")
        self.assertIsNotNone(template)
        height_prop = template.find("./property[@name='default-height']")
        width_prop = template.find("./property[@name='default-width']")
        self.assertIsNotNone(height_prop)
        self.assertEqual(height_prop.text, "700")
        self.assertEqual(width_prop.text, "700")

if __name__ == '__main__':
    unittest.main()
