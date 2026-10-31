import unittest
import os
import tempfile
import subprocess
from unittest.mock import MagicMock, patch

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

# Ensure gresource is compiled and loaded
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
xml_path = os.path.join(src_dir, 'readaloud.gresource.xml')

if os.path.exists(xml_path):
    with tempfile.NamedTemporaryFile(suffix='.gresource', delete=False) as tmp_res:
        tmp_res_path = tmp_res.name
    subprocess.run([
        'glib-compile-resources',
        f'--target={tmp_res_path}',
        f'--sourcedir={src_dir}',
        xml_path
    ], check=True)
    try:
        res = Gio.Resource.load(tmp_res_path)
        res._register()
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_res_path):
            os.unlink(tmp_res_path)

from src.window import ReadAloudWindow
from src.reader import Reader


class TestGenerationCancellation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow()

    def tearDown(self):
        if hasattr(self.window, 'hide_wait_dialog'):
            self.window.hide_wait_dialog()
        if hasattr(self.window, 'stop_playback') and self.window.is_playing:
            self.window.stop_playback()

    def test_wait_dialog_has_cancel_button(self):
        """Verify show_wait_dialog creates a Cancel button with appropriate CSS styling."""
        self.window.show_wait_dialog()
        self.assertIsNotNone(self.window.wait_dialog)
        self.assertIsNotNone(self.window.cancel_button)
        self.assertEqual(self.window.cancel_button.get_label(), "Cancel")
        self.assertTrue(self.window.cancel_button.has_css_class("pill"))
        self.assertTrue(self.window.cancel_button.has_css_class("cancel-generation-button"))

    def test_hide_wait_dialog_cleans_up_cancel_button(self):
        """Verify hide_wait_dialog properly clears the cancel_button reference."""
        self.window.show_wait_dialog()
        self.assertIsNotNone(self.window.cancel_button)
        self.window.hide_wait_dialog()
        self.assertIsNone(self.window.cancel_button)
        self.assertIsNone(self.window.wait_dialog)

    def test_reader_cancel_synthesis_cleans_up_files_and_flags(self):
        """Verify Reader.cancel_synthesis sets flags and deletes active temp files."""
        fd1, path1 = tempfile.mkstemp(suffix=".wav")
        os.close(fd1)
        fd2, path2 = tempfile.mkstemp(suffix=".wav")
        os.close(fd2)

        reader = Reader.__new__(Reader)
        reader.window = self.window
        reader._dialog_ready = MagicMock()
        reader._current_pipeline = None
        reader._stopped = False
        reader._cancelled = False
        reader._is_paused = False
        reader._current_temp_file = path1
        reader.temp_path = path2

        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))

        reader.cancel_synthesis()

        self.assertTrue(reader._cancelled)
        self.assertTrue(reader._stopped)
        self.assertIsNone(reader._current_temp_file)
        self.assertIsNone(reader.temp_path)
        self.assertFalse(os.path.exists(path1))
        self.assertFalse(os.path.exists(path2))

    def test_on_cancel_generation_clicked_resets_ui(self):
        """Verify clicking cancel restores sensitivity, hides HUD, and stops reader."""
        self.window.set_sensitive(False)
        self.window.show_wait_dialog()

        mock_reader = MagicMock()
        self.window.reader = mock_reader

        self.window._on_cancel_generation_clicked()

        self.assertTrue(self.window.get_sensitive())
        self.assertIsNone(self.window.wait_dialog)
        mock_reader.cancel_synthesis.assert_called_once()
        self.assertTrue(self.window._batch_export_cancelled)
        self.assertFalse(self.window.is_playing)

    def test_synthesize_audio_early_abort_when_cancelled(self):
        """Verify _synthesize_audio halts immediately when cancelled and does not start playback."""
        reader = Reader.__new__(Reader)
        reader.window = self.window
        reader._dialog_ready = MagicMock()
        reader._dialog_ready.wait.return_value = True
        reader._cancelled = True
        reader._stopped = False
        reader.voicemanager = MagicMock()
        reader.play_audio = True

        reader._synthesize_audio("Hello world", "en", "dummy-voice", 1.0, 1.0)
        reader.voicemanager.get_installed_voices.assert_not_called()

    def test_batch_export_cancelled_stops_chain(self):
        """Verify setting _batch_export_cancelled prevents further tab exports."""
        self.window._batch_export_cancelled = True
        self.window.show_wait_dialog(batch_text="Generating file 1 of 5")
        self.window.set_sensitive(False)

        pages = [(self.window.tab_view.get_nth_page(0), "Sample text")]
        with tempfile.TemporaryDirectory() as tmpdir:
            self.window._batch_export_tabs_audio(pages, tmpdir)
            self.window._on_cancel_generation_clicked()

        self.assertTrue(self.window.get_sensitive())
        self.assertIsNone(self.window.wait_dialog)
        self.assertTrue(self.window._batch_export_cancelled)


if __name__ == '__main__':
    unittest.main()
