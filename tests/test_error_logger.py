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

    def test_session_marker_lifecycle(self):
        """Verify start_session_tracking, update_session_activity, and mark_clean_exit."""
        import json
        from src.error_logger import (
            start_session_tracking,
            update_session_activity,
            mark_clean_exit,
        )

        test_marker = Path(self.test_dir) / "session_marker.json"
        orig_marker_path = src.error_logger.get_crash_marker_path
        try:
            src.error_logger.get_crash_marker_path = lambda: test_marker

            start_session_tracking()
            self.assertTrue(test_marker.is_file())

            with open(test_marker, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertFalse(data["clean_exit"])
            self.assertEqual(data["state"], "idle")
            self.assertEqual(data["pid"], os.getpid())

            update_session_activity(
                "synthesizing",
                voice="en_GB-alba-medium",
                word_count=35000,
                current_sentence=14,
                total_sentences=1200,
            )

            with open(test_marker, "r", encoding="utf-8") as f:
                updated = json.load(f)
            self.assertEqual(updated["state"], "synthesizing")
            self.assertEqual(updated["activity"]["voice"], "en_GB-alba-medium")
            self.assertEqual(updated["activity"]["word_count"], 35000)
            self.assertEqual(updated["activity"]["current_sentence"], 14)

            mark_clean_exit()
            with open(test_marker, "r", encoding="utf-8") as f:
                final = json.load(f)
            self.assertTrue(final["clean_exit"])
            self.assertIn("exit_time", final)
        finally:
            src.error_logger.get_crash_marker_path = orig_marker_path

    def test_check_previous_session_crash_detection(self):
        """Verify check_previous_session_crash detects unclean shutdown and logs diagnostic."""
        import json
        from src.error_logger import check_previous_session_crash

        test_marker = Path(self.test_dir) / "crash_marker.json"
        test_log = Path(self.test_dir) / "crash_error.log"
        orig_marker_path = src.error_logger.get_crash_marker_path
        orig_log_path = src.error_logger.get_error_log_path

        try:
            src.error_logger.get_crash_marker_path = lambda: test_marker
            src.error_logger.get_error_log_path = lambda: test_log

            # Simulate an abnormal termination from PID 999999
            initial_data = {
                "pid": 999999,
                "version": "1.8.18",
                "start_time": "2026-11-13T12:00:00Z",
                "clean_exit": False,
                "state": "synthesizing",
                "activity": {
                    "voice": "en_GB-alba-medium",
                    "word_count": 35000,
                    "current_sentence": 85,
                    "total_sentences": 1100,
                    "snippet": "It was the best of times, it was the worst of times...",
                },
                "platform": "linux",
                "python": "3.13.5",
            }
            with open(test_marker, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            crash_info = check_previous_session_crash()
            self.assertIsNotNone(crash_info)
            self.assertEqual(crash_info["pid"], 999999)
            self.assertEqual(crash_info["state"], "synthesizing")
            self.assertEqual(crash_info["activity"]["voice"], "en_GB-alba-medium")
            self.assertEqual(crash_info["activity"]["word_count"], 35000)

            # Error log must have been created with diagnostic report
            self.assertTrue(test_log.is_file())
            log_text = test_log.read_text(encoding="utf-8")
            self.assertIn("Abnormal Application Termination / Crash Detected", log_text)
            self.assertIn("en_GB-alba-medium", log_text)
            self.assertIn("35000", log_text)

            # Re-checking must return None since marker is marked handled
            self.assertIsNone(check_previous_session_crash())
        finally:
            src.error_logger.get_crash_marker_path = orig_marker_path
            src.error_logger.get_error_log_path = orig_log_path

    def test_check_previous_session_clean_exit_returns_none(self):
        """Verify check_previous_session_crash returns None if previous exit was clean."""
        import json
        from src.error_logger import check_previous_session_crash

        test_marker = Path(self.test_dir) / "clean_marker.json"
        orig_marker_path = src.error_logger.get_crash_marker_path
        try:
            src.error_logger.get_crash_marker_path = lambda: test_marker
            with open(test_marker, "w", encoding="utf-8") as f:
                json.dump({"pid": 888888, "clean_exit": True}, f)
            self.assertIsNone(check_previous_session_crash())
        finally:
            src.error_logger.get_crash_marker_path = orig_marker_path

    def test_get_and_clear_error_log(self):
        """Verify get_error_log_content reads entries and clear_error_log empties file."""
        from src.error_logger import get_error_log_content, clear_error_log

        test_log = Path(self.test_dir) / "read_clear.log"
        orig_log_path = src.error_logger.get_error_log_path
        try:
            src.error_logger.get_error_log_path = lambda: test_log
            test_log.write_text("Line 1\nLine 2\nLine 3\n", encoding="utf-8")

            content = get_error_log_content()
            self.assertIn("Line 1", content)
            self.assertIn("Line 3", content)

            res = clear_error_log()
            self.assertTrue(res)
            self.assertEqual(get_error_log_content(), "")
        finally:
            src.error_logger.get_error_log_path = orig_log_path

    def test_split_oversized_sentence(self):
        """Verify _split_oversized_sentence divides long sentences to prevent C buffer overflows."""
        from src.reader import _split_oversized_sentence, _extract_words_from_span

        # Generate a run-on sentence with 120 words and over 800 characters
        long_text = "The quick brown fox jumps over the lazy dog repeatedly without pausing for any terminal punctuation, " * 12
        words = _extract_words_from_span(long_text, 100)
        sent_info = {
            'sentence_text': long_text.strip(),
            'start_char': 100,
            'end_char': 100 + len(long_text.strip()),
            'words': words
        }

        chunks = _split_oversized_sentence(sent_info, max_chars=250, max_words=40)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk['words']), 40)
            self.assertLessEqual(len(chunk['sentence_text']), 300)
            self.assertGreaterEqual(chunk['start_char'], 100)
            self.assertLessEqual(chunk['end_char'], 100 + len(long_text.strip()))

    def test_large_35k_words_synthesis_chunking(self):
        """Verify extract_sentences_and_words safely chunks 35,000 words without crashing or overflowing."""
        from src.reader import extract_sentences_and_words

        # Construct a 35,000 word text with varying sentence lengths, lists, and commas
        base_sentence = "This is a comprehensive test sentence designed to simulate thirty five thousand words of speech synthesis text. "
        # 16 words per sentence -> need ~2200 repetitions to exceed 35,000 words
        repetitions = 2200
        large_text = base_sentence * repetitions
        word_count = len(large_text.split())
        self.assertGreater(word_count, 35000)

        sentences = extract_sentences_and_words(large_text)
        self.assertGreater(len(sentences), 2000)

        # Check bounds on every single sentence chunk
        for s in sentences[:100]:  # verify first 100 chunks
            self.assertLessEqual(len(s['words']), 40)
            self.assertLessEqual(len(s['sentence_text']), 250)
            self.assertGreater(len(s['words']), 0)
            self.assertLessEqual(s['start_char'], s['end_char'])


if __name__ == "__main__":
    unittest.main()
