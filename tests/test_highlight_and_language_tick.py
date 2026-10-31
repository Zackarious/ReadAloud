import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from src.window import ReadAloudWindow, HighlightTextView


class TestHighlightAndLanguageTick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_text_view_is_highlight_text_view(self):
        """Verify created tabs use HighlightTextView subclass."""
        window = ReadAloudWindow()
        tv = window.main_text_view
        self.assertIsInstance(tv, HighlightTextView)
        self.assertIsNone(tv._highlight_range)

    def test_highlight_word_and_clear(self):
        """Verify _highlight_word sets range on HighlightTextView and _clear_highlight resets it."""
        window = ReadAloudWindow()
        tv = window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("This is sample text for word highlighting.")

        window._highlight_word(8, 14)
        self.assertEqual(tv._highlight_range, (8, 14))

        window._clear_highlight()
        self.assertIsNone(tv._highlight_range)

    def test_language_chooser_dropdown_selection_tick(self):
        """Verify the language chooser popup list places a tick mark next to the selected language."""
        window = ReadAloudWindow()
        dropdown = window.lang_chooser
        list_factory = dropdown.get_list_factory()
        self.assertIsNotNone(list_factory)

        class MockListItem(Gtk.ListItem):
            def __init__(self, pos):
                super().__init__()
                self._pos = pos
                self._child = None
                self._item = None

            def get_position(self):
                return self._pos

            def set_child(self, c):
                self._child = c

            def get_child(self):
                return self._child

            def set_item(self, it):
                self._item = it

            def get_item(self):
                return self._item

        item0 = MockListItem(0)
        item1 = MockListItem(1)

        str0 = Gtk.StringObject.new("English (UK)")
        str1 = Gtk.StringObject.new("English (US)")

        item0.set_item(str0)
        item1.set_item(str1)

        list_factory.emit("setup", item0)
        list_factory.emit("setup", item1)

        dropdown.set_selected(0)
        list_factory.emit("bind", item0)
        list_factory.emit("bind", item1)

        # Item 0 is selected -> has tick
        label0 = item0.get_child()
        label1 = item1.get_child()
        self.assertTrue(label0.get_text().startswith("✓ "), f"Selected language should have tick: {label0.get_text()}")
        self.assertFalse(label1.get_text().startswith("✓ "), f"Unselected language should not have tick: {label1.get_text()}")

        # Switch selection to index 1 -> tick updates dynamically
        dropdown.set_selected(1)
        self.assertFalse(label0.get_text().startswith("✓ "), "Item 0 should no longer have tick")
        self.assertTrue(label1.get_text().startswith("✓ "), "Item 1 should now have tick")

    def test_highlight_word_centers_in_middle_of_screen(self):
        """Verify _highlight_word positions the scroller so the highlighted text stays in the middle of the screen (50% vertically)."""
        from unittest.mock import MagicMock
        window = ReadAloudWindow()
        tv = window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("First line.\n" * 30 + "Middle target line.\n" + "Last line.\n" * 30)

        # Mock scroll_to_iter to record arguments
        scroll_args = []
        tv.scroll_to_iter = lambda iter_obj, margin, use_align, xalign, yalign: scroll_args.append(
            (margin, use_align, xalign, yalign)
        )

        # Find target word offset
        target_str = "Middle target line."
        offset = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).find(target_str)
        window._highlight_word(offset, offset + len("Middle"))

        # Verify scroll_to_iter was invoked with use_align=True and yalign=0.5 (dead center)
        self.assertEqual(len(scroll_args), 1)
        margin, use_align, xalign, yalign = scroll_args[0]
        self.assertTrue(use_align, "scroll_to_iter must use alignment (use_align=True)")
        self.assertEqual(yalign, 0.5, "yalign must be 0.5 to keep highlighted text in the middle of the screen")

    def test_highlight_word_adjustment_and_bottom_margin_at_document_end(self):
        """Verify that at the bottom of the document, bottom_margin allows the active line to reach the vertical middle."""
        from unittest.mock import MagicMock
        window = ReadAloudWindow()
        tv = window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("Short preamble.\n" * 5 + "Final word at the very end.")

        # Simulate ScrolledWindow with 600px viewport
        parent = tv.get_parent()
        vadj = parent.get_vadjustment()
        vadj.set_page_size(600)
        vadj.set_upper(2000)

        # Simulate target line location near end of document (y = 1200, height = 30)
        mock_rect = MagicMock()
        mock_rect.x = 0
        mock_rect.y = 1200
        mock_rect.width = 50
        mock_rect.height = 30
        tv.get_iter_location = MagicMock(return_value=mock_rect)
        tv.scroll_to_iter = MagicMock()

        set_val_mock = MagicMock()
        vadj.set_value = set_val_mock

        # Target near the end of the buffer
        end_offset = buf.get_char_count() - 5
        window._highlight_word(end_offset, buf.get_char_count())

        # Verify bottom_margin was dynamically updated to at least half the page size (300px)
        self.assertGreaterEqual(tv.get_bottom_margin(), 300)

        # Verify scroll_to_iter was invoked with use_align=True and yalign=0.5
        self.assertTrue(tv.scroll_to_iter.called)
        call_args = tv.scroll_to_iter.call_args[0]
        margin, use_align, xalign, yalign = call_args[1:]
        self.assertTrue(use_align)
        self.assertEqual(yalign, 0.5)

    def test_highlight_word_no_jumping_on_same_line(self):
        """Verify consecutive words on the same visual line do not re-trigger scrolling, eliminating jumping and flickering."""
        from unittest.mock import MagicMock
        window = ReadAloudWindow()
        tv = window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("First word on line.\nSecond line with many words across it.\nThird line.")

        scroll_calls = []
        tv.scroll_to_iter = lambda iter_obj, margin, use_align, xalign, yalign: scroll_calls.append(
            (margin, use_align, xalign, yalign)
        )

        full_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        idx_second = full_text.find("Second")
        idx_line = full_text.find("line with")
        idx_many = full_text.find("many")

        # First word on line 2 -> triggers scroll to center the new line
        window._highlight_word(idx_second, idx_second + len("Second"))
        self.assertEqual(len(scroll_calls), 1)

        # Subsequent words on the exact same line -> DO NOT re-trigger scroll
        window._highlight_word(idx_line, idx_line + len("line"))
        self.assertEqual(len(scroll_calls), 1, "Word on same line must not re-trigger scroll")

        window._highlight_word(idx_many, idx_many + len("many"))
        self.assertEqual(len(scroll_calls), 1, "Word on same line must not re-trigger scroll")

        # Moving to line 3 -> triggers scroll to center line 3
        idx_third = full_text.find("Third")
        window._highlight_word(idx_third, idx_third + len("Third"))
        self.assertEqual(len(scroll_calls), 2, "Transition to next line must trigger scroll")

    def test_highlight_rectangles_on_wrapped_lines(self):
        """Verify _get_highlight_rectangles produces bounding boxes for each visual display line when text wraps."""
        from gi.repository import GLib
        window = ReadAloudWindow()
        tv = window.main_text_view
        buf = tv.get_buffer()
        text = "Total Denial of Remedies (No Apology, No Redress): Farrar took a strict civil-litigation approach—arguing that because no court deadline was struck out."
        buf.set_text(text)

        # Force allocate a narrow size to guarantee wrapping
        window.set_default_size(350, 400)
        window.present()
        ctx = GLib.MainContext.default()
        for _ in range(10):
            ctx.iteration(False)

        # Span across 'approach—arguing' which wraps across lines
        start_c = text.index("approach—arguing")
        end_c = start_c + len("approach—arguing")
        it1 = buf.get_iter_at_offset(start_c)
        it2 = buf.get_iter_at_offset(end_c)

        rects = tv._get_highlight_rectangles(buf, it1, it2)
        self.assertGreaterEqual(len(rects), 1, "Must produce bounding rectangles")
        for bx, by, bw, bh in rects:
            self.assertGreater(bw, 0, "Rectangle width must be greater than zero")
            self.assertGreater(bh, 0, "Rectangle height must be greater than zero")

        # Verify do_snapshot_layer executes cleanly with wrapped range
        tv.set_highlight_range(start_c, end_c)
        snapshot = Gtk.Snapshot()
        tv.do_snapshot_layer(Gtk.TextViewLayer.BELOW_TEXT, snapshot)

    def test_extract_sentences_and_words_dash_splitting(self):
        """Verify words connected by em-dashes (—) or double hyphens (--) are properly tokenized with exact character offsets."""
        from src.reader import extract_sentences_and_words
        text = "strict civil-litigation approach—arguing that test--again and one—two—three!"
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 1)

        words = sentences[0]["words"]
        extracted_words = [w["word"] for w in words]

        # Verify compound hyphenated word is preserved
        self.assertIn("civil-litigation", extracted_words)

        # Verify em-dash separated words are split
        self.assertIn("approach—", extracted_words)
        self.assertIn("arguing", extracted_words)

        # Verify double-hyphen separated words are split
        self.assertIn("test--", extracted_words)
        self.assertIn("again", extracted_words)

        # Verify all character spans exactly match original text slices
        for w in words:
            span_text = text[w["start_char"]:w["end_char"]]
            self.assertEqual(span_text, w["word"], f"Span slice '{span_text}' must match word '{w['word']}'")


if __name__ == '__main__':
    unittest.main()

