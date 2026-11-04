import unittest
import os
import tempfile
import subprocess
from unittest.mock import MagicMock, patch

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

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


class TestTabSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow()

    def tearDown(self):
        if hasattr(self.window, 'stop_playback') and self.window.is_playing:
            self.window.stop_playback()

    def test_initial_tab(self):
        """Verify window starts with exactly 1 tab titled 'Untitled Document' and a valid main_text_view."""
        self.assertEqual(self.window.tab_view.get_n_pages(), 1)
        first_page = self.window.tab_view.get_nth_page(0)
        self.assertEqual(first_page.get_title(), "Untitled Document")
        self.assertIsNotNone(self.window.main_text_view)
        self.assertIsInstance(self.window.main_text_view, Gtk.TextView)

    def test_create_and_switch_tabs(self):
        """Verify creating a tab increments page count and focuses the new tab's text view."""
        page2 = self.window.create_new_tab(title="Second Document", text="Content in second tab")
        self.assertEqual(self.window.tab_view.get_n_pages(), 2)
        self.assertEqual(self.window.tab_view.get_selected_page(), page2)
        self.assertEqual(page2.get_title(), "Second Document")

        # Verify main_text_view returns the active tab's text view
        buf2 = self.window.main_text_view.get_buffer()
        text2 = buf2.get_text(buf2.get_start_iter(), buf2.get_end_iter(), False)
        self.assertEqual(text2, "Content in second tab")

        # Switch back to first page
        page1 = self.window.tab_view.get_nth_page(0)
        self.window.tab_view.set_selected_page(page1)
        self.assertEqual(self.window.tab_view.get_selected_page(), page1)
        buf1 = self.window.main_text_view.get_buffer()
        text1 = buf1.get_text(buf1.get_start_iter(), buf1.get_end_iter(), False)
        self.assertEqual(text1, "")

    def test_tab_switch_pauses_playback(self):
        """Verify switching active tabs automatically pauses audio playback instead of stopping."""
        page1 = self.window.tab_view.get_nth_page(0)
        self.window._active_tab_page = page1
        self.window.is_playing = True
        self.window.is_paused = False

        mock_reader = MagicMock()
        mock_reader.pause_audio.return_value = True
        self.window.reader = mock_reader
        self.window._get_current_playback_char_offset = MagicMock(return_value=12)

        # Create Tab 2 (switches selected page)
        page2 = self.window.create_new_tab(title="Second Tab", text="Hello world")

        mock_reader.pause_audio.assert_called_once()
        self.assertTrue(page1._is_playing)
        self.assertTrue(page1._is_paused)
        self.assertEqual(page1._paused_offset, 12)
        self.assertFalse(self.window.is_playing)
        self.assertFalse(self.window.is_paused)

    def test_new_tab_pauses_playback_and_resume_on_return(self):
        """Verify creating a new tab pauses playback, keeps text position, and returning resumes."""
        page1 = self.window.tab_view.get_nth_page(0)
        tv1 = self.window._get_text_view_for_page(page1)
        buf1 = tv1.get_buffer()
        buf1.set_text("First sentence to read. Second sentence to read.")
        self.window._active_tab_page = page1

        self.window.is_playing = True
        self.window.is_paused = False
        mock_reader = MagicMock()
        mock_reader.pause_audio.return_value = True
        mock_reader.resume_audio.return_value = True
        mock_reader.word_timings = [
            {'start_time': 0.0, 'end_time': 1.0, 'start_char': 0, 'end_char': 5},
            {'start_time': 1.0, 'end_time': 2.0, 'start_char': 6, 'end_char': 14},
        ]
        mock_reader.selected_voice = self.window._get_selected_voice_name()
        mock_reader.lang_code = self.window.lang_code
        mock_reader.pitch = self.window._get_pitch_for_voice(mock_reader.selected_voice)
        mock_reader.speed = self.window.speed_chooser.get_value()
        self.window.reader = mock_reader
        self.window._get_current_playback_char_offset = MagicMock(return_value=6)

        # 1. User clicks '+' (create_new_tab)
        page2 = self.window.create_new_tab(title="New Tab", text="")

        # Verify Tab 1 was paused and pause_resume_mark created
        mock_reader.pause_audio.assert_called_once()
        self.assertTrue(page1._is_paused)
        mark = buf1.get_mark("pause_resume_mark")
        self.assertIsNotNone(mark)
        self.assertEqual(buf1.get_iter_at_mark(mark).get_offset(), 6)

        # Tab 2 is active and not playing
        self.assertFalse(self.window.is_playing)
        self.assertFalse(self.window.is_paused)

        # 2. User returns to Tab 1
        self.window.tab_view.set_selected_page(page1)

        # Tab 1 is restored in paused state
        self.assertTrue(self.window.is_playing)
        self.assertTrue(self.window.is_paused)
        self.assertIs(self.window.reader, mock_reader)
        self.assertTrue(self.window.pause_button.get_sensitive())

        # 3. User hits play again (e.g. clicks Resume or calls read_text)
        self.window.read_text(self.window.read_button)

        # Playback is resumed
        mock_reader.resume_audio.assert_called_once()
        self.assertFalse(self.window.is_paused)

    def test_new_tab_pauses_playback_and_resume_with_new_voice_settings(self):
        """Verify returning to a paused tab and resuming with changed settings resumes from paused mark."""
        page1 = self.window.tab_view.get_nth_page(0)
        tv1 = self.window._get_text_view_for_page(page1)
        buf1 = tv1.get_buffer()
        buf1.set_text("First sentence to read. Second sentence to read.")
        self.window._active_tab_page = page1

        self.window.is_playing = True
        self.window.is_paused = False
        mock_reader = MagicMock()
        mock_reader.pause_audio.return_value = True
        mock_reader.selected_voice = "OldVoice"
        mock_reader.lang_code = self.window.lang_code
        mock_reader.pitch = 1.0
        mock_reader.speed = 1.0
        mock_reader.original_text = "First sentence to read. Second sentence to read."
        mock_reader.start_char_offset = 0
        self.window.reader = mock_reader
        self.window._get_current_playback_char_offset = MagicMock(return_value=6)

        # 1. Switch to new tab (pauses Tab 1)
        page2 = self.window.create_new_tab(title="New Tab", text="")
        self.assertTrue(page1._is_paused)

        # 2. Return to Tab 1
        self.window.tab_view.set_selected_page(page1)

        # 3. Resume with new settings mock
        resumed_calls = []
        self.window._resume_with_new_settings = lambda *args: resumed_calls.append(args)

        # User changed voice
        self.window._get_selected_voice_name = lambda: "NewVoice"

        # Hit play
        self.window.read_text(self.window.read_button)

        self.assertEqual(len(resumed_calls), 1)
        self.assertEqual(resumed_calls[0][0], "NewVoice")

    def test_close_empty_tab_closes_without_prompt(self):
        """Verify closing an empty tab does not prompt with an AlertDialog and completes immediately."""
        page2 = self.window.create_new_tab(title="Empty Tab", text="")
        self.window.tab_view.close_page_finish = MagicMock()

        result = self.window._on_close_page(self.window.tab_view, page2)
        self.assertTrue(result)
        self.window.tab_view.close_page_finish.assert_called_once_with(page2, True)

    def test_close_tab_with_content_shows_dialog(self):
        """Verify closing a tab with text prompts an AlertDialog with export options."""
        page2 = self.window.create_new_tab(title="Document With Text", text="Some important notes")
        self.window.tab_view.close_page_finish = MagicMock()

        with patch('src.window.Adw.AlertDialog') as mock_dialog_cls:
            mock_dialog_instance = MagicMock()
            mock_dialog_cls.return_value = mock_dialog_instance

            result = self.window._on_close_page(self.window.tab_view, page2)
            self.assertTrue(result)
            mock_dialog_cls.assert_called_once()
            mock_dialog_instance.choose.assert_called_once()

    def test_save_audio_dialog_single_tab(self):
        """When only one tab exists, save_audio_dialog invokes single tab export directly."""
        self.assertEqual(self.window.tab_view.get_n_pages(), 1)
        self.window._save_single_audio_dialog = MagicMock()
        self.window._export_all_tabs_audio_dialog = MagicMock()

        self.window.save_audio_dialog()
        self.window._save_single_audio_dialog.assert_called_once()
        self.window._export_all_tabs_audio_dialog.assert_not_called()

    def test_save_audio_dialog_multi_tab_prompts(self):
        """When multiple tabs exist, save_audio_dialog presents choice between current and all tabs."""
        self.window.create_new_tab(title="Tab 2", text="Tab 2 text")
        self.assertGreater(self.window.tab_view.get_n_pages(), 1)

        with patch('src.window.Adw.AlertDialog') as mock_dialog_cls:
            mock_dialog_instance = MagicMock()
            mock_dialog_cls.return_value = mock_dialog_instance

            self.window.save_audio_dialog()
            mock_dialog_cls.assert_called_once()
            mock_dialog_instance.choose.assert_called_once()

    def test_tab_actions_registered(self):
        """Verify win.new-tab and win.close-tab actions are registered on the window."""
        new_tab_action = self.window.lookup_action("new-tab")
        close_tab_action = self.window.lookup_action("close-tab")
        self.assertIsNotNone(new_tab_action)
        self.assertIsNotNone(close_tab_action)

    def test_open_file_complete_behavior(self):
        """Verify open_file_complete uses empty untitled tab or creates new tab if content exists."""
        mock_file = MagicMock()
        mock_file.get_basename.return_value = "chapter1.txt"
        mock_file.load_contents_finish.return_value = (True, b"Content of chapter 1")

        # Tab 0 is empty and untitled, should reuse it
        self.window.open_file_complete(mock_file, None)
        self.assertEqual(self.window.tab_view.get_n_pages(), 1)
        first_page = self.window.tab_view.get_nth_page(0)
        self.assertEqual(first_page.get_title(), "chapter1.txt")

        # Now tab 0 has text; opening another file should open in a new tab
        mock_file2 = MagicMock()
        mock_file2.get_basename.return_value = "chapter2.txt"
        mock_file2.load_contents_finish.return_value = (True, b"Content of chapter 2")

        self.window.open_file_complete(mock_file2, None)
        self.assertEqual(self.window.tab_view.get_n_pages(), 2)
        second_page = self.window.tab_view.get_nth_page(1)
        self.assertEqual(second_page.get_title(), "chapter2.txt")


    def test_show_wait_dialog_with_batch_text(self):
        """Verify show_wait_dialog creates and updates batch_label with 'Generating file X of Y'."""
        self.window.show_wait_dialog(batch_text="Generating file 1 of 30")
        self.assertIsNotNone(self.window.wait_dialog)
        self.assertIsNotNone(self.window.batch_label)
        self.assertTrue(self.window.batch_label.get_visible())
        self.assertEqual(self.window.batch_label.get_text(), "Generating file 1 of 30")

        # Test updating existing wait dialog with next file
        self.window.show_wait_dialog(batch_text="Generating file 2 of 30")
        self.assertEqual(self.window.batch_label.get_text(), "Generating file 2 of 30")

        # Test hide_wait_dialog cleans up batch state
        self.window.hide_wait_dialog()
        self.assertIsNone(self.window.wait_dialog)
        self.assertIsNone(self.window.batch_label)
        self.assertIsNone(getattr(self.window, '_batch_export_status', None))

    def test_batch_export_tabs_audio_progresses_through_files(self):
        """Verify _batch_export_tabs_audio sequentially updates status to 'Generating file X of Y'."""
        pages_to_export = [
            (MagicMock(), f"Paragraph content for tab {i}")
            for i in range(1, 31)
        ]
        self.assertEqual(len(pages_to_export), 30)

        recorded_statuses = []
        recorded_hide_flags = []

        with tempfile.TemporaryDirectory() as tmpdir:
            def fake_reader_constructor(text, engine, lang_code, voice, pitch, speed,
                                        window=None, play_audio=True, on_complete=None,
                                        start_char_offset=0, hide_dialog_on_complete=True):
                mock_instance = MagicMock()
                recorded_statuses.append(getattr(window, '_batch_export_status', None))
                recorded_hide_flags.append(hide_dialog_on_complete)
                mock_instance.save_audio_file = MagicMock()
                # Run completion asynchronously via GLib.idle_add
                if on_complete:
                    GLib.idle_add(on_complete, "/tmp/fake.wav")
                return mock_instance

            with patch('src.window.Reader', side_effect=fake_reader_constructor):
                self.window._batch_export_tabs_audio(pages_to_export, tmpdir)

                # Process all GLib main context iterations until complete
                ctx = GLib.MainContext.default()
                while ctx.pending():
                    ctx.iteration(False)

        self.assertEqual(len(recorded_statuses), 30)
        self.assertEqual(recorded_statuses[0], "Generating file 1 of 30")
        self.assertEqual(recorded_statuses[14], "Generating file 15 of 30")
        self.assertEqual(recorded_statuses[29], "Generating file 30 of 30")
        self.assertTrue(all(flag is False for flag in recorded_hide_flags))
        self.assertIsNone(self.window.wait_dialog)
        self.assertIsNone(self.window._batch_export_status)


    def test_close_request_no_unexported_audio_closes_immediately(self):
        """Verify _on_close_request returns False and saves settings when no tabs have unexported text."""
        # By default tab 0 has empty text
        self.assertEqual(len(self.window._get_unexported_audio_pages()), 0)
        self.window._save_settings = MagicMock()
        result = self.window._on_close_request(self.window)
        self.assertFalse(result)
        self.window._save_settings.assert_called_once()

    def test_close_request_with_unexported_audio_prompts_dialog(self):
        """Verify _on_close_request shows export dialog with 'current' and 'all' options when text exists."""
        self.window.create_new_tab(title="Notes", text="Unexported notes content")
        self.assertGreater(len(self.window._get_unexported_audio_pages()), 0)

        with patch('src.window.Adw.AlertDialog') as mock_dialog_cls:
            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            result = self.window._on_close_request(self.window)
            self.assertTrue(result)
            mock_dialog_cls.assert_called_once()

            # Verify responses added to dialog
            response_ids = [call[0][0] for call in mock_dialog.add_response.call_args_list]
            self.assertIn("cancel", response_ids)
            self.assertIn("discard", response_ids)
            self.assertIn("current", response_ids)
            self.assertIn("all", response_ids)
            mock_dialog.choose.assert_called_once()

    def test_close_request_dialog_responses(self):
        """Verify dialog responses trigger discard, current tab export, and all tabs export."""
        page1 = self.window.tab_view.get_nth_page(0)
        buf1 = self.window.main_text_view.get_buffer()
        buf1.set_text("Text in tab 1")
        page2 = self.window.create_new_tab(title="Tab 2", text="Text in tab 2")

        with patch('src.window.Adw.AlertDialog') as mock_dialog_cls:
            mock_dialog = MagicMock()
            mock_dialog_cls.return_value = mock_dialog

            self.window._on_close_request(self.window)
            on_choose_callback = mock_dialog.choose.call_args[0][2]

            # 1. Test "discard" response
            self.window._do_close = MagicMock()
            mock_dialog.choose_finish.return_value = "discard"
            on_choose_callback(mock_dialog, None)
            self.window._do_close.assert_called_once()

            # 2. Test "current" response
            self.window._export_audio_for_page = MagicMock()
            mock_dialog.choose_finish.return_value = "current"
            on_choose_callback(mock_dialog, None)
            self.window._export_audio_for_page.assert_called_once_with(
                page2,
                on_complete=self.window._do_close
            )

            # 3. Test "all" response
            self.window._export_all_tabs_audio_dialog = MagicMock()
            mock_dialog.choose_finish.return_value = "all"
            on_choose_callback(mock_dialog, None)
            self.window._export_all_tabs_audio_dialog.assert_called_once()
            called_kwargs = self.window._export_all_tabs_audio_dialog.call_args[1]
            self.assertEqual(len(called_kwargs['pages_to_export']), 2)
            self.assertEqual(called_kwargs['on_complete'], self.window._do_close)

    def test_page_exported_audio_text_tracking(self):
        """Verify _page_has_unexported_audio tracks audio export state accurately."""
        page = self.window.tab_view.get_nth_page(0)
        buf = self.window.main_text_view.get_buffer()

        # Empty tab: no unexported audio
        self.assertFalse(self.window._page_has_unexported_audio(page))

        # Add text: now unexported
        buf.set_text("Exportable speech text")
        self.assertTrue(self.window._page_has_unexported_audio(page))

        # Mark exported
        page._exported_audio_text = "Exportable speech text"
        self.assertFalse(self.window._page_has_unexported_audio(page))

        # Modify text: becomes unexported again
        buf.set_text("Exportable speech text with revisions")
        self.assertTrue(self.window._page_has_unexported_audio(page))

    def test_tab_tooltip_matches_full_tab_name(self):
        """Verify tab tooltip is set to the full tab title upon creation and modification."""
        page0 = self.window.tab_view.get_nth_page(0)
        self.assertEqual(page0.get_title(), "Untitled Document")
        self.assertEqual(page0.get_tooltip(), "Untitled Document")

        long_title = "Quick Read: Lubuntu is a variant of Ubuntu that uses the LXQt desktop environment."
        page = self.window.create_new_tab(title=long_title)
        self.assertEqual(page.get_title(), long_title)
        self.assertEqual(page.get_tooltip(), long_title)

    def test_load_text_and_play_preserves_full_first_line_in_title_and_tooltip(self):
        """Verify load_text_and_play sets the full first line in tab title and tooltip without premature truncation."""
        text = "Lubuntu is a variant of Ubuntu that uses the LXQt desktop environment.\nAdditional details follow."
        with patch.object(self.window, 'read_text'):
            page = self.window.load_text_and_play(text)
            expected_title = "Quick Read: Lubuntu is a variant of Ubuntu that uses the LXQt desktop environment."
            self.assertEqual(page.get_title(), expected_title)
            self.assertEqual(page.get_tooltip(), expected_title)


if __name__ == '__main__':
    unittest.main()
