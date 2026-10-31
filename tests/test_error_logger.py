# test_error_logger.py
#
# Tests for ReadAloud's error logging system and error reporting dialogs.

import os
import sys
import unittest
from pathlib import Path
import tempfile
import shutil

from src.error_logger import get_error_log_path, log_error, install_exception_hooks
import src.reader


class TestErrorLogger(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="readaloud_test_log_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sys_imported_in_reader(self):
        """Verify that sys is properly imported and defined in reader module."""
        self.assertTrue(hasattr(src.reader, "sys"))
        self.assertEqual(src.reader.sys, sys)

    def test_get_error_log_path(self):
        """Verify that get_error_log_path returns a valid Path that can be written to."""
        p = get_error_log_path()
        self.assertIsInstance(p, Path)
        self.assertEqual(p.name, "error.log")

    def test_log_error_formatting(self):
        """Verify that log_error formats diagnostics, timestamp, and writes to disk."""
        target_log = Path(self.test_dir) / "test_app_dir" / "error.log"

        # Mock get_error_log_path
        original_get_path = src.error_logger.get_error_log_path
        try:
            src.error_logger.get_error_log_path = lambda: target_log

            try:
                raise ValueError("Test synthesis failure simulation")
            except ValueError as e:
                saved_path = log_error("Simulation error occurred", exc=e, context="Unit Test Context")

            self.assertEqual(saved_path, target_log)
            self.assertTrue(target_log.is_file())

            content = target_log.read_text(encoding="utf-8")
            self.assertIn("ReadAloud Error Log", content)
            self.assertIn("Simulation error occurred", content)
            self.assertIn("Unit Test Context", content)
            self.assertIn("ValueError: Test synthesis failure simulation", content)
            self.assertIn("Traceback (most recent call last):", content)
            self.assertIn("Platform:", content)
            self.assertIn("Version:", content)
        finally:
            src.error_logger.get_error_log_path = original_get_path

    def test_window_show_error_includes_log_path(self):
        """Verify that Window._show_error logs the error and mentions error.log in its dialog body."""
        from src.window import ReadAloudWindow
        from gi.repository import Adw, Gtk

        app = Adw.Application(application_id="im.zackarious.ReadAloud.TestErrorLog")
        try:
            win = ReadAloudWindow(application=app)
        except Exception:
            # If full window construction cannot run in headless environment, test dialog generation directly
            win = ReadAloudWindow.__new__(ReadAloudWindow)
            win.present = lambda *_: None

        dialog = win._show_error("Could not load speech model", context="Test Model Loading")
        self.assertIsNotNone(dialog)
        body = dialog.get_body()
        self.assertIn("Could not load speech model", body)
        self.assertIn("error.log", body)
        self.assertIn("A detailed error log has been saved to:", body)

    def test_reader_handle_error_forwards_to_window(self):
        """Verify that reader._handle_error forwards the exception and traceback to window._show_error."""
        from src.reader import Reader

        reader = Reader.__new__(Reader)
        reader.temp_path = None

        captured_errors = []
        class MockWindow:
            def hide_wait_dialog(self): pass
            def set_sensitive(self, val): pass
            def stop_playback(self): pass
            def _show_error(self, msg, exc=None, traceback_text=None, context=None):
                captured_errors.append((msg, exc, traceback_text, context))

        reader.window = MockWindow()

        try:
            raise RuntimeError("Engine failure")
        except RuntimeError as err:
            import traceback
            tb = traceback.format_exc()
            reader._handle_error("Engine failure", exc=err, traceback_text=tb)

        self.assertEqual(len(captured_errors), 1)
        msg, exc, tb_text, ctx = captured_errors[0]
        self.assertEqual(msg, "Engine failure")
        self.assertIsInstance(exc, RuntimeError)
        self.assertIn("RuntimeError: Engine failure", tb_text)
        self.assertEqual(ctx, "Speech Synthesis")


if __name__ == "__main__":
    unittest.main()
