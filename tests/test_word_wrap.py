# tests/test_word_wrap.py
#
# Copyright 2025-2026 Walter Bernard / zackarious
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from src.reader import extract_sentences_and_words
from src.window import unwrap_text, ReadAloudWindow


class TestWordWrapAndSentenceSegmentation(unittest.TestCase):
    """Unit test suite verifying intelligent sentence segmentation, PDF line-break smoothing,
    and interactive text unwrapping."""

    def test_pdf_sentence_consolidation(self):
        """Verify soft line wraps in multi-column PDF text are consolidated into a single sentence for Piper TTS."""
        text = "This is line one\nof a multi-column PDF document\nthat forms a single coherent sentence."
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 1)
        self.assertEqual(
            sentences[0]["sentence_text"],
            "This is line one of a multi-column PDF document that forms a single coherent sentence."
        )

    def test_character_offset_preservation_across_line_breaks(self):
        """Verify each word's start_char and end_char exactly match slices in the original text buffer."""
        text = "First line here.\nSecond line follows\nthird line continues."
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 2)

        for sent in sentences:
            for w in sent["words"]:
                slice_text = text[w["start_char"]:w["end_char"]]
                self.assertEqual(
                    slice_text, w["word"],
                    f"Slice '{slice_text}' must match word '{w['word']}' at [{w['start_char']}:{w['end_char']}]"
                )

    def test_abbreviation_initial_decimal_protection(self):
        """Verify abbreviations (Dr., p.m.), initials (J. K.), decimals (3.14), and URLs are protected."""
        text = "Dr. Smith met with J. K. Rowling at 3.14 p.m. to discuss machine.local:8080 updates. Then they departed."
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 2)
        self.assertIn("Dr. Smith", sentences[0]["sentence_text"])
        self.assertIn("J. K. Rowling", sentences[0]["sentence_text"])
        self.assertIn("3.14", sentences[0]["sentence_text"])
        self.assertEqual(sentences[1]["sentence_text"], "Then they departed.")

    def test_hyphenated_line_break_consolidation(self):
        """Verify hyphenated line breaks (e.g. diffu-\nsion) are joined cleanly for natural speech synthesis."""
        text = "This represents the diffu-\nsion process in physics."
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 1)
        self.assertIn("diffusion", sentences[0]["sentence_text"])

    def test_paragraph_gap_preservation(self):
        """Verify true paragraph breaks (2+ newlines) remain separate sentences."""
        text = "Paragraph one with line one\nand line two.\n\nParagraph two with another sentence."
        sentences = extract_sentences_and_words(text)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0]["sentence_text"], "Paragraph one with line one and line two.")
        self.assertEqual(sentences[1]["sentence_text"], "Paragraph two with another sentence.")

    def test_unwrap_text_utility(self):
        """Verify unwrap_text() joins physical line breaks and removes hyphens while keeping paragraphs."""
        raw_text = "The quick brown fox\njumps over the diffu-\nsion model.\n\nSecond paragraph here\nwith wrapped text."
        result = unwrap_text(raw_text)
        expected = "The quick brown fox jumps over the diffusion model.\n\nSecond paragraph here with wrapped text."
        self.assertEqual(result, expected)

    def test_unwrap_text_empty_and_none(self):
        """Verify unwrap_text handles empty and None gracefully."""
        self.assertIsNone(unwrap_text(None))
        self.assertEqual(unwrap_text(""), "")

    def test_window_unwrap_action_entire_buffer(self):
        """Verify ReadAloudWindow.unwrap_text() transforms the entire buffer and allows atomic undo."""
        tv = Gtk.TextView()
        buf = tv.get_buffer()
        buf.set_text("Line one\nline two\nline three.")

        win = ReadAloudWindow.__new__(ReadAloudWindow)
        win._override_main_text_view = tv

        win.unwrap_text()
        self.assertEqual(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True), "Line one line two line three.")

        # Test single-stroke atomic undo
        if hasattr(buf, "can_undo") and buf.can_undo():
            buf.undo()
            self.assertEqual(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True), "Line one\nline two\nline three.")

    def test_window_unwrap_action_selective(self):
        """Verify ReadAloudWindow.unwrap_text() selectively unwraps only selected text when selection exists."""
        tv = Gtk.TextView()
        buf = tv.get_buffer()
        buf.set_text("Prefix.\nLine A\nLine B.\nSuffix.")

        win = ReadAloudWindow.__new__(ReadAloudWindow)
        win._override_main_text_view = tv

        # Select 'Line A\nLine B.'
        start_iter = buf.get_iter_at_offset(8)
        end_iter = buf.get_iter_at_offset(22)
        buf.select_range(start_iter, end_iter)

        win.unwrap_text()
        full_result = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        self.assertIn("Line A Line B.", full_result)
        self.assertTrue(full_result.startswith("Prefix.\n"))
        self.assertTrue(full_result.endswith("\nSuffix."))


    def test_headerbar_buttons(self):
        """Verify the redundant burger-like unwrap button is not present on the header bar."""
        import xml.etree.ElementTree as ET
        tree = ET.parse("src/window.ui")
        root = tree.getroot()
        header_bar = root.find(".//object[@id='header_bar']")
        self.assertIsNotNone(header_bar)
        start_button_ids = [
            child.find("object").attrib.get("id")
            for child in header_bar.findall("./child[@type='start']")
            if child.find("object") is not None
        ]
        self.assertEqual(start_button_ids, ["open_button", "wiki_button", "save_text_button"])
        self.assertNotIn("unwrap_button", start_button_ids)


if __name__ == '__main__':
    unittest.main()
