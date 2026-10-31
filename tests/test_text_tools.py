import unittest
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.window import (
    ReadAloudWindow,
    HighlightTextView,
    ensure_paragraph_gaps,
    clean_round_brackets,
    clean_square_brackets,
    clean_hash_symbols,
    clean_pipe_brackets,
    clean_star_symbols,
    clean_all_tags,
    apply_text_tag_stripping,
)


class TestTextTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Adw.Application(application_id="im.zackarious.ReadAloud.TestTextTools")
        cls.app.register(None)

    def test_clean_round_brackets_user_example(self):
        sample = (
            "Cyrus II of Persia[b] (c. 600 – 530 BC), commonly known as "
            "Cyrus the Great,[7] was the founder of the Achaemenid Empire.[8]"
        )
        expected = (
            "Cyrus II of Persia[b], commonly known as "
            "Cyrus the Great,[7] was the founder of the Achaemenid Empire.[8]"
        )
        self.assertEqual(clean_round_brackets(sample), expected)

    def test_clean_square_brackets_user_example(self):
        sample = (
            "Cyrus II of Persia[b] (c. 600 – 530 BC), commonly known as "
            "Cyrus the Great,[7] was the founder of the Achaemenid Empire.[8]"
        )
        expected = (
            "Cyrus II of Persia(c. 600 – 530 BC), commonly known as "
            "Cyrus the Great, was the founder of the Achaemenid Empire."
        )
        self.assertEqual(clean_square_brackets(sample), expected)

    def test_sequential_bracket_cleaning(self):
        sample = (
            "Cyrus II of Persia[b] (c. 600 – 530 BC), commonly known as "
            "Cyrus the Great,[7] was the founder of the Achaemenid Empire.[8]"
        )
        cleaned = clean_round_brackets(clean_square_brackets(sample))
        expected = "Cyrus II of Persia, commonly known as Cyrus the Great, was the founder of the Achaemenid Empire."
        self.assertEqual(cleaned, expected)

    def test_nested_round_brackets(self):
        text = "Alpha (beta (gamma) delta) epsilon"
        self.assertEqual(clean_round_brackets(text), "Alpha epsilon")

    def test_nested_square_brackets(self):
        text = "Alpha [beta [gamma] delta] epsilon"
        self.assertEqual(clean_square_brackets(text), "Alpha epsilon")

    def test_multiline_brackets(self):
        text_round = "Start (\nline 1\nline 2\n) end."
        self.assertEqual(clean_round_brackets(text_round), "Start end.")

        text_square = "Start [\nline 1\nline 2\n] end."
        self.assertEqual(clean_square_brackets(text_square), "Start end.")

    def test_punctuation_spacing_cleanup(self):
        text = "Hello (world) , how are you (doing) ? Good ."
        self.assertEqual(clean_round_brackets(text), "Hello, how are you? Good.")

        text_sq = "Citation[1] , reference[2] . Done !"
        self.assertEqual(clean_square_brackets(text_sq), "Citation, reference. Done!")

    def test_empty_and_none_input(self):
        self.assertEqual(clean_round_brackets(""), "")
        self.assertEqual(clean_round_brackets(None), "")
        self.assertEqual(clean_square_brackets(""), "")
        self.assertEqual(clean_square_brackets(None), "")

    def test_unmatched_brackets_preserved(self):
        self.assertEqual(clean_round_brackets("Unmatched ( here"), "Unmatched ( here")
        self.assertEqual(clean_square_brackets("Unmatched [ here"), "Unmatched [ here")

    def test_tools_actions_registered(self):
        win = ReadAloudWindow(application=self.app)
        self.assertFalse(hasattr(win, "tools_button") and win.tools_button is not None)

        self.assertTrue(win.has_action("remove-round-brackets"))
        self.assertTrue(win.has_action("remove-square-brackets"))
        self.assertTrue(win.has_action("remove-pipe-brackets"))
        self.assertTrue(win.has_action("remove-hashes"))
        self.assertTrue(win.has_action("remove-stars"))
        self.assertTrue(win.has_action("remove-all-tags"))

    def test_apply_tool_to_current_tab_and_undo(self):
        win = ReadAloudWindow(application=self.app)
        buf = win.main_text_view.get_buffer()
        original_text = "Testing (parentheses removal) tool."
        buf.set_text(original_text)

        win._apply_bracket_tool_to_current_tab("round")
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Testing tool.")

        if hasattr(buf, 'undo') and hasattr(buf, 'get_can_undo') and buf.get_can_undo():
            buf.undo()
            start, end = buf.get_bounds()
            self.assertEqual(buf.get_text(start, end, True), original_text)

    def test_apply_tool_to_all_tabs(self):
        win = ReadAloudWindow(application=self.app)
        page1 = win.tab_view.get_selected_page()
        tv1 = page1.get_child().get_child()
        tv1.get_buffer().set_text("Tab 1 with (note 1) here.")

        page2 = win.create_new_tab(title="Tab 2", text="Tab 2 with (note 2) here.")
        tv2 = page2.get_child().get_child()

        win._apply_bracket_tool_to_all_tabs("round")

        b1 = tv1.get_buffer()
        b2 = tv2.get_buffer()
        self.assertEqual(b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True), "Tab 1 with here.")
        self.assertEqual(b2.get_text(b2.get_start_iter(), b2.get_end_iter(), True), "Tab 2 with here.")

    def test_clean_hash_symbols(self):
        sample = "# Heading 1\n## Heading 2\n### Subheading\nIssue #123 with #hashtag and C# code."
        expected = "Heading 1\nHeading 2\nSubheading\nIssue 123 with hashtag and C code."
        self.assertEqual(clean_hash_symbols(sample), expected)

    def test_clean_hash_symbols_empty_and_spacing(self):
        self.assertEqual(clean_hash_symbols(""), "")
        self.assertEqual(clean_hash_symbols(None), "")
        self.assertEqual(clean_hash_symbols("   #    Title   "), "Title")
        self.assertEqual(clean_hash_symbols("Line 1\n\n# Line 2\n\nLine 3"), "Line 1\n\nLine 2\n\nLine 3")

    def test_remove_hashes_action_registered(self):
        win = ReadAloudWindow(application=self.app)
        self.assertTrue(win.has_action("remove-hashes"))

    def test_apply_hash_tool_to_current_tab_and_undo(self):
        win = ReadAloudWindow(application=self.app)
        buf = win.main_text_view.get_buffer()
        original_text = "# Chapter 1: The #Beginning"
        buf.set_text(original_text)

        win._apply_bracket_tool_to_current_tab("hash")
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Chapter 1: The Beginning")

        if hasattr(buf, 'undo') and hasattr(buf, 'get_can_undo') and buf.get_can_undo():
            buf.undo()
            start, end = buf.get_bounds()
            self.assertEqual(buf.get_text(start, end, True), original_text)

    def test_apply_hash_tool_to_all_tabs(self):
        win = ReadAloudWindow(application=self.app)
        page1 = win.tab_view.get_selected_page()
        tv1 = page1.get_child().get_child()
        tv1.get_buffer().set_text("# Tab 1 Heading")

        page2 = win.create_new_tab(title="Tab 2", text="## Tab 2 Heading")
        tv2 = page2.get_child().get_child()

        win._apply_bracket_tool_to_all_tabs("hash")

        b1 = tv1.get_buffer()
        b2 = tv2.get_buffer()
        self.assertEqual(b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True), "Tab 1 Heading")
        self.assertEqual(b2.get_text(b2.get_start_iter(), b2.get_end_iter(), True), "Tab 2 Heading")

    def test_clean_pipe_brackets(self):
        sample = "Here is some |note or tag| text."
        expected = "Here is some text."
        self.assertEqual(clean_pipe_brackets(sample), expected)

    def test_clean_pipe_brackets_multiple(self):
        sample = "|Tag 1| First part |Tag 2| second part |Tag 3|."
        expected = "First part second part."
        self.assertEqual(clean_pipe_brackets(sample), expected)

    def test_clean_pipe_brackets_multiline(self):
        sample = "Start |\nmultiline\npipe block\n| end."
        expected = "Start end."
        self.assertEqual(clean_pipe_brackets(sample), expected)

    def test_clean_pipe_brackets_empty_and_spacing(self):
        self.assertEqual(clean_pipe_brackets(""), "")
        self.assertEqual(clean_pipe_brackets(None), "")
        self.assertEqual(clean_pipe_brackets("Hello |world| , how are you |fine| ?"), "Hello, how are you?")
        self.assertEqual(clean_pipe_brackets("Word || next"), "Word next")

    def test_clean_pipe_brackets_unmatched(self):
        self.assertEqual(clean_pipe_brackets("Preserve | single pipe"), "Preserve | single pipe")

    def test_remove_pipe_brackets_action_registered(self):
        win = ReadAloudWindow(application=self.app)
        self.assertTrue(win.has_action("remove-pipe-brackets"))

    def test_apply_pipe_tool_to_current_tab_and_undo(self):
        win = ReadAloudWindow(application=self.app)
        buf = win.main_text_view.get_buffer()
        original_text = "Article title |draft v1| final."
        buf.set_text(original_text)

        win._apply_bracket_tool_to_current_tab("pipe")
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Article title final.")

        if hasattr(buf, 'undo') and hasattr(buf, 'get_can_undo') and buf.get_can_undo():
            buf.undo()
            start, end = buf.get_bounds()
            self.assertEqual(buf.get_text(start, end, True), original_text)

    def test_apply_pipe_tool_to_all_tabs(self):
        win = ReadAloudWindow(application=self.app)
        page1 = win.tab_view.get_selected_page()
        tv1 = page1.get_child().get_child()
        tv1.get_buffer().set_text("Tab 1 |p1| text")

        page2 = win.create_new_tab(title="Tab 2", text="Tab 2 |p2| text")
        tv2 = page2.get_child().get_child()

        win._apply_bracket_tool_to_all_tabs("pipe")

        b1 = tv1.get_buffer()
        b2 = tv2.get_buffer()
        self.assertEqual(b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True), "Tab 1 text")
        self.assertEqual(b2.get_text(b2.get_start_iter(), b2.get_end_iter(), True), "Tab 2 text")

    def test_apply_text_tag_stripping_all_options(self):
        sample = "# Heading (note) [ref] |meta| text"
        # Strip all
        stripped_all = apply_text_tag_stripping(sample, strip_round=True, strip_square=True, strip_pipe=True, strip_hash=True)
        self.assertEqual(stripped_all, "Heading text")

        # Strip only pipe
        stripped_pipe = apply_text_tag_stripping(sample, strip_pipe=True)
        self.assertEqual(stripped_pipe, "# Heading (note) [ref] text")

        # Strip none
        self.assertEqual(apply_text_tag_stripping(sample), sample)

    def test_clean_pipe_brackets_markdown_table_user_example(self):
        sample = (
            "# Rinoa Heartilly\n\n"
            "| Rinoa Heartilly |  |\n"
            "| --- | --- |\n"
            "| Final Fantasy character |  |\n"
            "| ![image](images/250px-RinoaDissidiaNT.png)  Rinoa as drawn by Tetsuya Nomura |  |\n"
            "| First\xa0game | Final Fantasy VIII (1999) |\n"
            "| Created\xa0by | Kazushige Nojima |\n"
            "| Designed\xa0by | Tetsuya Nomura |\n"
            "| Voiced\xa0by | EN: Skyler DavenportJA: Kana Hanazawa |\n"
            "| In-universe information |  |\n"
            "| Weapon | Blaster Edge |\n"
            "| Home | Galbadia |\n"
        )
        # Testing clean_pipe_brackets directly: table and its contents are cleanly removed
        self.assertEqual(clean_pipe_brackets(sample), "# Rinoa Heartilly")

        # Testing with full tag stripping (round, square, pipe, hash)
        cleaned = apply_text_tag_stripping(
            sample,
            strip_round=True,
            strip_square=True,
            strip_pipe=True,
            strip_hash=True
        )
        self.assertEqual(cleaned, "Rinoa Heartilly")

    def test_clean_pipe_brackets_table_without_outer_pipes(self):
        sample = (
            "Intro paragraph.\n\n"
            "Column A | Column B\n"
            "--- | ---\n"
            "Value 1 | Value 2\n"
            "Value 3 | Value 4\n\n"
            "Outro paragraph."
        )
        expected = "Intro paragraph.\n\nOutro paragraph."
        self.assertEqual(clean_pipe_brackets(sample), expected)

    def test_markdown_image_no_orphan_exclamation_screenshot_example(self):
        sample = (
            "## Character design\n\n"
            "![image](images/250px-Hanazawa_Kana_from_Human_Lost_at_Opening_Ceremony_of_the_Tokyo_International_Film_Festival_2019_49013612766.jpg)\n\n"
            "Kana Hanazawa voiced Rinoa in Japanese in Dissidia Final Fantasy NT."
        )
        # 1. Full tag stripping (round, square, pipe, hash)
        cleaned = apply_text_tag_stripping(
            sample,
            strip_round=True,
            strip_square=True,
            strip_pipe=True,
            strip_hash=True
        )
        expected = (
            "Character design\n\n"
            "Kana Hanazawa voiced Rinoa in Japanese in Dissidia Final Fantasy NT."
        )
        self.assertEqual(cleaned, expected)
        self.assertNotIn("!", cleaned)

        # 2. Square brackets cleaner alone should remove the markdown image without leaving '!'
        sq_cleaned = clean_square_brackets(sample)
        self.assertNotIn("!\n", sq_cleaned)
        self.assertNotIn("![image]", sq_cleaned)

        # 3. Round brackets cleaner alone should remove the markdown image without leaving '!'
        rd_cleaned = clean_round_brackets(sample)
        self.assertNotIn("!\n", rd_cleaned)

    def test_orphan_exclamation_mark_cleaned(self):
        # Even if text already has a stranded orphan '!' on its own line (as in screenshot 2)
        sample = (
            "Character design\n\n"
            "!\n\n"
            "Kana Hanazawa voiced Rinoa in Japanese in Dissidia Final Fantasy NT."
        )
        expected = (
            "Character design\n\n"
            "Kana Hanazawa voiced Rinoa in Japanese in Dissidia Final Fantasy NT."
        )
        self.assertEqual(clean_square_brackets(sample), expected)
        self.assertEqual(clean_round_brackets(sample), expected)
        self.assertEqual(clean_hash_symbols(sample), expected)
        self.assertEqual(apply_text_tag_stripping(sample, strip_square=True), expected)

    def test_sentence_exclamation_marks_preserved(self):
        # Legitimate exclamation marks in prose and citations must be preserved
        prose = "Hello world! What a great day! Attention! Important notice."
        self.assertEqual(clean_square_brackets(prose), prose)
        self.assertEqual(clean_round_brackets(prose), prose)

        citation_with_exclamation = "Look at that![1] Wonderful!"
        expected_citation = "Look at that! Wonderful!"
        self.assertEqual(clean_square_brackets(citation_with_exclamation), expected_citation)

    def test_clean_star_symbols(self):
        sample = "**Bold text** and *italic text* and ***bold-italic***."
        expected = "Bold text and italic text and bold-italic."
        self.assertEqual(clean_star_symbols(sample), expected)

    def test_clean_star_symbols_bullets_and_spacing(self):
        sample = "* First item\n* Second item\n* Third item"
        expected = "First item\nSecond item\nThird item"
        self.assertEqual(clean_star_symbols(sample), expected)

    def test_clean_star_symbols_empty_and_hr(self):
        self.assertEqual(clean_star_symbols(""), "")
        self.assertEqual(clean_star_symbols(None), "")
        sample_hr = "Paragraph 1\n***\nParagraph 2"
        expected_hr = "Paragraph 1\n\nParagraph 2"
        self.assertEqual(clean_star_symbols(sample_hr), expected_hr)

    def test_clean_all_tags(self):
        sample = (
            "# Chapter 1: Introduction\n\n"
            "This is a paragraph with (an aside note) and [citation 1] and | markdown table col |.\n"
            "Here is **bold speech** and *emphasis*.\n"
            "***\n"
            "Conclusion line."
        )
        expected = (
            "Chapter 1: Introduction\n\n"
            "This is a paragraph with and and.\n"
            "Here is bold speech and emphasis.\n\n"
            "Conclusion line."
        )
        self.assertEqual(clean_all_tags(sample), expected)

    def test_apply_star_tool_to_current_tab(self):
        win = ReadAloudWindow(application=self.app)
        buf = win.main_text_view.get_buffer()
        buf.set_text("Hello **world** and *everyone*!")
        win._apply_bracket_tool_to_current_tab("star")
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Hello world and everyone!")

    def test_apply_remove_all_to_current_tab(self):
        win = ReadAloudWindow(application=self.app)
        buf = win.main_text_view.get_buffer()
        buf.set_text("# Section (note) [ref] **bold** text")
        win._apply_bracket_tool_to_current_tab("all")
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Section bold text")

    def test_apply_remove_all_to_all_tabs(self):
        win = ReadAloudWindow(application=self.app)
        page1 = win.tab_view.get_selected_page()
        tv1 = page1.get_child().get_child()
        tv1.get_buffer().set_text("# Tab 1 (aside) **important**")

        page2 = win.create_new_tab(title="Tab 2", text="# Tab 2 [ref] *italic*")
        tv2 = page2.get_child().get_child()

        win._apply_bracket_tool_to_all_tabs("all")

        b1 = tv1.get_buffer()
        b2 = tv2.get_buffer()
        self.assertEqual(b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True), "Tab 1 important")
        self.assertEqual(b2.get_text(b2.get_start_iter(), b2.get_end_iter(), True), "Tab 2 italic")

    def test_remove_all_menu_item_only_in_tools_submenu(self):
        """Verify 'Remove All' only appears under the Tools submenu and not on the top-level menu."""
        import xml.etree.ElementTree as ET
        ui_path = os.path.join(src_dir, "window.ui")
        tree = ET.parse(ui_path)
        root = tree.getroot()
        primary_menu = root.find(".//menu[@id='primary_menu']")
        self.assertIsNotNone(primary_menu)

        top_level_actions = []
        tools_submenu_actions = []

        for section in primary_menu.findall("section"):
            for item in section.findall("item"):
                act = item.find("attribute[@name='action']")
                if act is not None:
                    top_level_actions.append(act.text)
            for submenu in section.findall("submenu"):
                sub_label = submenu.find("attribute[@name='label']")
                if sub_label is not None and "Tools" in sub_label.text:
                    for sub_sec in submenu.findall("section"):
                        for sub_item in sub_sec.findall("item"):
                            sub_act = sub_item.find("attribute[@name='action']")
                            if sub_act is not None:
                                tools_submenu_actions.append(sub_act.text)

        # Must NOT appear at top level
        self.assertNotIn("win.remove-all-tags", top_level_actions)
        # Must appear exactly once under Tools submenu
        self.assertEqual(tools_submenu_actions.count("win.remove-all-tags"), 1)

    def test_ensure_paragraph_gaps_user_example(self):
        """Single newlines become double newlines creating a separate line with a gap."""
        input_text = "This is the first paragraph.\nThis is the second paragraph."
        expected = "This is the first paragraph.\n\nThis is the second paragraph."
        self.assertEqual(ensure_paragraph_gaps(input_text), expected)

    def test_ensure_paragraph_gaps_preserves_double_newlines(self):
        """Already spaced paragraphs are preserved without adding extra lines."""
        text = "This is the first paragraph.\n\nThis is the second paragraph."
        self.assertEqual(ensure_paragraph_gaps(text), text)

    def test_ensure_paragraph_gaps_normalizes_excessive_newlines(self):
        """More than 2 newlines are normalized down to 2 newlines."""
        text = "Paragraph 1\n\n\n\n\nParagraph 2"
        expected = "Paragraph 1\n\nParagraph 2"
        self.assertEqual(ensure_paragraph_gaps(text), expected)

    def test_ensure_paragraph_gaps_crlf_and_whitespace_lines(self):
        """CRLF line endings and whitespace-only lines are normalized cleanly."""
        text = "Line 1\r\n   \r\nLine 2\rLine 3"
        expected = "Line 1\n\nLine 2\n\nLine 3"
        self.assertEqual(ensure_paragraph_gaps(text), expected)

    def test_ensure_paragraph_gaps_empty_and_none(self):
        """Empty or None text returns empty string or unmodified."""
        self.assertEqual(ensure_paragraph_gaps(""), "")
        self.assertEqual(ensure_paragraph_gaps(None), None)

    def test_highlight_text_view_return_key_inserts_gap(self):
        """Pressing Return inserts a separate line with an empty line gap (\\n\\n)."""
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("Hello")
        end_iter = buf.get_end_iter()
        buf.place_cursor(end_iter)

        handled = tv._on_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
        self.assertTrue(handled)

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Hello\n\n")

    def test_highlight_text_view_kp_enter_inserts_gap(self):
        """Pressing Keypad Enter also inserts a separate line with a gap (\\n\\n)."""
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("Prefix")
        end_iter = buf.get_end_iter()
        buf.place_cursor(end_iter)

        handled = tv._on_key_pressed(None, Gdk.KEY_KP_Enter, 0, Gdk.ModifierType(0))
        self.assertTrue(handled)

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Prefix\n\n")

    def test_highlight_text_view_shift_return_inserts_single_newline(self):
        """Pressing Shift+Return allows inserting a single newline (\\n)."""
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("First line")
        end_iter = buf.get_end_iter()
        buf.place_cursor(end_iter)

        handled = tv._on_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType.SHIFT_MASK)
        self.assertTrue(handled)

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "First line\n")

    def test_highlight_text_view_return_replaces_selection(self):
        """Return key replaces any active selection with \\n\\n."""
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("Alpha BETA Gamma")
        # Select "BETA"
        it1 = buf.get_iter_at_offset(6)
        it2 = buf.get_iter_at_offset(10)
        buf.select_range(it1, it2)

        handled = tv._on_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
        self.assertTrue(handled)

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Alpha \n\n Gamma")

    def test_highlight_text_view_non_editable_ignores_return(self):
        """Non-editable text view does not intercept or mutate on Return."""
        tv = HighlightTextView()
        tv.set_editable(False)
        buf = tv.get_buffer()
        buf.set_text("Immutable")

        handled = tv._on_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0))
        self.assertFalse(handled)

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Immutable")

    def test_highlight_text_view_ctrl_return_not_intercepted(self):
        """Modifier keys like Ctrl+Return pass through unhandled."""
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("Text")

        handled = tv._on_key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertFalse(handled)

    def test_create_new_tab_applies_paragraph_gaps(self):
        """Importing text via create_new_tab formats single newlines with gaps."""
        win = ReadAloudWindow(application=self.app)
        raw_text = "This is line 1.\nThis is line 2.\nThis is line 3."
        page = win.create_new_tab(title="Test Gap Tab", text=raw_text)
        tv = page.get_child().get_child()
        buf = tv.get_buffer()
        start, end = buf.get_bounds()
        expected = "This is line 1.\n\nThis is line 2.\n\nThis is line 3."
        self.assertEqual(buf.get_text(start, end, True), expected)

    def test_dropped_file_into_empty_tab_applies_paragraph_gaps(self):
        """Dropped file into an empty tab formats single newlines with gaps."""
        win = ReadAloudWindow(application=self.app)
        page0 = win.tab_view.get_nth_page(0)
        file_mock = Gio.File.new_for_path("/tmp/test_para.txt")
        norm_items = [("test_para.txt", "Paragraph A\nParagraph B", file_mock)]

        win._import_dropped_files_into_empty_tab(norm_items, page0)
        text = win._get_text_for_page(page0)
        self.assertEqual(text, "Paragraph A\n\nParagraph B")

    def test_highlight_text_view_paste_clipboard_formats_gaps(self):
        """Pasting clipboard content formats single newlines into paragraph gaps."""
        from unittest.mock import MagicMock, patch
        tv = HighlightTextView()
        buf = tv.get_buffer()
        buf.set_text("Initial: ")
        buf.place_cursor(buf.get_end_iter())

        mock_clipboard = MagicMock()
        def mock_read_text_async(cancellable, callback, user_data):
            mock_res = MagicMock()
            mock_clipboard.read_text_finish.return_value = "Pasted Para 1\nPasted Para 2"
            callback(mock_clipboard, mock_res, user_data)

        mock_clipboard.read_text_async.side_effect = mock_read_text_async

        with patch.object(tv, 'get_clipboard', return_value=mock_clipboard):
            tv.emit("paste-clipboard")

        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, True), "Initial: Pasted Para 1\n\nPasted Para 2")

    def test_open_file_complete_applies_paragraph_gaps(self):
        """Opening a text file ensures single newlines have paragraph gaps."""
        from unittest.mock import MagicMock
        win = ReadAloudWindow(application=self.app)
        mock_file = MagicMock()
        mock_file.load_contents_finish.return_value = (True, b"File Line 1\nFile Line 2", None)
        mock_file.get_basename.return_value = "document.txt"

        win.open_file_complete(mock_file, None)
        text = win._get_text_for_page(win.tab_view.get_selected_page())
        self.assertEqual(text, "File Line 1\n\nFile Line 2")


if __name__ == '__main__':
    unittest.main()

