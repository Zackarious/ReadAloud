# test_auto_remove_tags_and_font_popup.py
#
# Automated unit tests for automatic tag removal toggle, import triggers,
# real-time typing/pasting tag removal, and font zoom hover popup buttons.

import unittest
from unittest.mock import MagicMock, patch
import os
import tempfile
import subprocess

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

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

from src.window import ReadAloudWindow, HighlightTextView, clean_all_tags


class TestAutoRemoveTagsAndFontPopup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = Adw.Application(application_id="im.zackarious.ReadAloud.TestAutoRemoveTags")
        cls.app.register()

    def setUp(self):
        self.window = ReadAloudWindow(application=self.app)
        self.drain_main_loop()

    def tearDown(self):
        if hasattr(self.window, '_cleanup_temp_audio'):
            self.window._cleanup_temp_audio()
        self.window.destroy()
        self.drain_main_loop()

    def drain_main_loop(self):
        ctx = GLib.MainContext.default()
        while ctx.iteration(False):
            pass

    # =========================================================================
    # 1. Automatic tag removal toggle tests
    # =========================================================================

    def test_auto_remove_tags_defaults_to_true(self):
        """auto_remove_tags defaults to True and win.auto-remove-tags stateful action is True."""
        self.assertTrue(self.window.auto_remove_tags)
        action = self.window.lookup_action("auto-remove-tags")
        self.assertIsNotNone(action)
        self.assertTrue(action.get_state().get_boolean())

    def test_auto_remove_tags_toggle_and_action(self):
        """Toggling win.auto-remove-tags action updates window property and vice-versa."""
        action = self.window.lookup_action("auto-remove-tags")
        self.assertIsNotNone(action)

        # Toggle off
        action.change_state(GLib.Variant.new_boolean(False))
        self.drain_main_loop()
        self.assertFalse(self.window.auto_remove_tags)
        self.assertFalse(action.get_state().get_boolean())

        # Toggle on
        self.window.set_auto_remove_tags(True)
        self.drain_main_loop()
        self.assertTrue(self.window.auto_remove_tags)
        self.assertTrue(action.get_state().get_boolean())

    def test_auto_remove_tags_saved_in_settings(self):
        """Window settings dictionary persists auto_remove_tags."""
        with patch("json.dump") as mock_json_dump, patch("builtins.open"):
            self.window.set_auto_remove_tags(False)
            self.window._save_settings()
            args, _ = mock_json_dump.call_args
            saved_dict = args[0]
            self.assertIn("auto_remove_tags", saved_dict)
            self.assertFalse(saved_dict["auto_remove_tags"])

    def test_toggling_auto_remove_tags_cleans_current_buffer(self):
        """Enabling auto-remove-tags immediately cleans tags from current buffer."""
        self.window.set_auto_remove_tags(False)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("Title (comment) [1] #header *bold*")

        # Now enable
        action = self.window.lookup_action("auto-remove-tags")
        action.change_state(GLib.Variant.new_boolean(True))
        self.drain_main_loop()

        cleaned = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertNotIn("(comment)", cleaned)
        self.assertNotIn("[1]", cleaned)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("*", cleaned)

    # =========================================================================
    # 2. Import triggers auto-selection
    # =========================================================================

    def test_open_file_dialog_auto_selects_auto_remove_tags(self):
        """Calling open_file_dialog ensures auto_remove_tags is set to True."""
        self.window.set_auto_remove_tags(False)
        self.assertFalse(self.window.auto_remove_tags)

        with patch.object(Gtk.FileDialog, 'open'):
            self.window.open_file_dialog()
            self.assertTrue(self.window.auto_remove_tags)

    def test_dropped_files_auto_selects_auto_remove_tags(self):
        """Dropping files onto window ensures auto_remove_tags is set to True."""
        self.window.set_auto_remove_tags(False)
        self.assertFalse(self.window.auto_remove_tags)

        f = Gio.File.new_for_path("/tmp/test.txt")
        with patch.object(Gio.File, 'load_contents', return_value=(True, b"hello", None)), \
             patch.object(self.window, '_prompt_empty_tab_import'):
            self.window._on_files_dropped(None, [f], 0, 0)
            self.assertTrue(self.window.auto_remove_tags)

    def test_wikipedia_import_auto_selects_auto_remove_tags(self):
        """Triggering Wikipedia import ensures auto_remove_tags is set to True."""
        self.window.set_auto_remove_tags(False)
        self.assertFalse(self.window.auto_remove_tags)

        with patch.object(Adw.AlertDialog, 'choose'):
            self.window.on_import_wikipedia_action()
            self.assertTrue(self.window.auto_remove_tags)

    def test_open_file_complete_cleans_tags_when_enabled(self):
        """open_file_complete cleans all tags when auto_remove_tags is True."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("")  # empty untitled tab

        fake_file = Gio.File.new_for_path("/tmp/notes.txt")
        raw_content = b"# Main Title\nThis has (note) and [ref] and *emphasis*."

        # Simulate load_contents_finish
        fake_file.load_contents_finish = MagicMock(return_value=(True, raw_content, "etag"))
        self.window.open_file_complete(fake_file, None)
        self.drain_main_loop()

        loaded_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertNotIn("#", loaded_text)
        self.assertNotIn("(note)", loaded_text)
        self.assertNotIn("[ref]", loaded_text)
        self.assertNotIn("*", loaded_text)
        self.assertIn("Main Title", loaded_text)

    # =========================================================================
    # 3. Real-time typing & pasting tag removal
    # =========================================================================

    def test_typing_hash_and_star_blocked_when_enabled(self):
        """Typing '#' and '*' is blocked when auto_remove_tags is True."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view

        # Keypress for '#'
        key_ctrl = None
        for c in tv.observe_controllers():
            if isinstance(c, Gtk.EventControllerKey):
                key_ctrl = c
                break
        self.assertIsNotNone(key_ctrl)

        # '#' keypress
        consumed = tv._on_key_pressed(key_ctrl, Gdk.KEY_numbersign, 0, Gdk.ModifierType(0))
        self.assertTrue(consumed)

        # '*' keypress
        consumed_star = tv._on_key_pressed(key_ctrl, Gdk.KEY_asterisk, 0, Gdk.ModifierType(0))
        self.assertTrue(consumed_star)

    def test_typing_hash_and_star_allowed_when_disabled(self):
        """Typing '#' and '*' is allowed when auto_remove_tags is False."""
        self.window.set_auto_remove_tags(False)
        tv = self.window.main_text_view

        key_ctrl = None
        for c in tv.observe_controllers():
            if isinstance(c, Gtk.EventControllerKey):
                key_ctrl = c
                break

        consumed = tv._on_key_pressed(key_ctrl, Gdk.KEY_numbersign, 0, Gdk.ModifierType(0))
        self.assertFalse(consumed)

        consumed_star = tv._on_key_pressed(key_ctrl, Gdk.KEY_asterisk, 0, Gdk.ModifierType(0))
        self.assertFalse(consumed_star)

    def test_completing_round_bracket_removes_tag_at_cursor(self):
        """Closing ')' triggers removal of the completed (tag) at cursor."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("Hello (world)")
        # Place cursor at end right after ')'
        end_iter = buf.get_end_iter()
        buf.place_cursor(end_iter)

        tv._clean_completed_tag_at_cursor(')')
        self.drain_main_loop()

        result = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertEqual(result, "Hello")

    def test_completing_square_bracket_removes_tag_at_cursor(self):
        """Closing ']' triggers removal of the completed [tag] at cursor."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("Important [citation 1] facts")
        # Place cursor right after ']'
        end_sq = buf.get_iter_at_offset(len("Important [citation 1]"))
        buf.place_cursor(end_sq)

        tv._clean_completed_tag_at_cursor(']')
        self.drain_main_loop()

        result = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertEqual(result, "Important facts")

    def test_completing_pipe_bracket_removes_tag_at_cursor(self):
        """Closing second '|' triggers removal of completed |tag| at cursor."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("Report |internal only| summary")
        # Place cursor right after second '|'
        end_pipe = buf.get_iter_at_offset(len("Report |internal only|"))
        buf.place_cursor(end_pipe)

        tv._clean_completed_tag_at_cursor('|')
        self.drain_main_loop()

        result = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertEqual(result, "Report summary")

    def test_pasting_cleans_all_tags_when_enabled(self):
        """Pasting text automatically cleans all tags when auto_remove_tags is True."""
        self.window.set_auto_remove_tags(True)
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("")

        raw_clipboard_text = "# Header\nHello (secret) [12] *starred* and |table| end."

        with patch.object(Gdk.Clipboard, 'read_text_async') as mock_read:
            def fake_read_async(cancellable, callback, user_data):
                mock_res = MagicMock()
                with patch.object(Gdk.Clipboard, 'read_text_finish', return_value=raw_clipboard_text):
                    callback(tv.get_clipboard(), mock_res, user_data)

            mock_read.side_effect = fake_read_async
            tv._on_paste_clipboard(tv)
            self.drain_main_loop()

        result = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertNotIn("#", result)
        self.assertNotIn("(secret)", result)
        self.assertNotIn("[12]", result)
        self.assertNotIn("*", result)
        self.assertNotIn("|table|", result)
        self.assertIn("Header", result)
        self.assertIn("starred and end.", result)

    # =========================================================================
    # 4. Font zoom controls in tab bar tests
    # =========================================================================

    def test_font_zoom_elements_exist_in_tab_bar(self):
        """Font zoom controls exist in window template and are placed in tab bar before new tab button."""
        self.assertIsNotNone(self.window.font_zoom_popup)
        self.assertIsNotNone(self.window.font_decrease_btn)
        self.assertIsNotNone(self.window.font_zoom_label)
        self.assertIsNotNone(self.window.font_increase_btn)
        self.assertEqual(self.window.font_zoom_label.get_label(), f"{self.window.text_zoom_level}%")

        # Verify font_zoom_popup is inside tab_bar end action widget
        end_widget = self.window.tab_bar.get_end_action_widget()
        self.assertIsNotNone(end_widget)

        # In GtkBox, font_zoom_popup should be first child and new_tab_button should follow it
        first_child = end_widget.get_first_child()
        self.assertEqual(first_child, self.window.font_zoom_popup)
        next_sibling = first_child.get_next_sibling()
        self.assertEqual(next_sibling, self.window.new_tab_button)

    def test_font_zoom_always_visible(self):
        """Font zoom controls are always visible in the tab bar."""
        self.assertTrue(self.window.is_font_zoom_popup_showing())
        self.assertTrue(self.window.font_zoom_popup.get_visible())

    def test_font_zoom_circular_buttons_and_styling(self):
        """Font zoom buttons have circular class and correct capsule styling."""
        self.assertTrue(self.window.font_decrease_btn.has_css_class("circular"))
        self.assertTrue(self.window.font_increase_btn.has_css_class("circular"))
        self.assertTrue(self.window.font_zoom_popup.has_css_class("font-zoom-tab-bar"))

    def test_font_zoom_increase_and_decrease_buttons(self):
        """Clicking zoom in/out buttons adjusts text zoom by 20% and updates label."""
        initial_zoom = self.window.text_zoom_level
        self.assertEqual(self.window.font_zoom_label.get_label(), f"{initial_zoom}%")

        # Click increase button (adds 20%)
        self.window.font_increase_btn.emit("clicked")
        self.drain_main_loop()
        self.assertEqual(self.window.text_zoom_level, initial_zoom + 20)
        self.assertEqual(self.window.font_zoom_label.get_label(), f"{initial_zoom + 20}%")

        # Click decrease button (removes 20%)
        self.window.font_decrease_btn.emit("clicked")
        self.drain_main_loop()
        self.assertEqual(self.window.text_zoom_level, initial_zoom)
        self.assertEqual(self.window.font_zoom_label.get_label(), f"{initial_zoom}%")

    def test_font_zoom_backward_compatibility_stubs(self):
        """show_font_zoom_popup, hide_font_zoom_popup, and dismiss_font_zoom_popup run safely as stubs."""
        # None of these should raise an exception
        self.window.show_font_zoom_popup()
        self.window.hide_font_zoom_popup()
        self.window.dismiss_font_zoom_popup()
        self.assertTrue(self.window.is_font_zoom_popup_showing())


if __name__ == '__main__':
    unittest.main()
