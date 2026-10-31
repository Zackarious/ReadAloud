# tests/test_export_filename.py
import unittest
import datetime
from src.window import ReadAloudWindow

class TestExportFilename(unittest.TestCase):
    def setUp(self):
        self.window = ReadAloudWindow.__new__(ReadAloudWindow)
        self.today_str = datetime.datetime.now().strftime("%d %b %Y")

    def test_hello_world_example(self):
        """Verify the user-specified example: Day - Month - Year - Hello World"""
        res = self.window._generate_default_audio_filename("Hello World")
        expected = f"{self.today_str} - Hello World.mp3"
        self.assertEqual(res, expected)

    def test_first_five_words_selection(self):
        """Verify only the first 5 words are selected when text is longer"""
        text = "The quick brown fox jumps over the lazy dog."
        res = self.window._generate_default_audio_filename(text)
        expected = f"{self.today_str} - The quick brown fox jumps.mp3"
        self.assertEqual(res, expected)

    def test_single_word(self):
        """Verify single word input generates properly"""
        res = self.window._generate_default_audio_filename("ReadAloud")
        expected = f"{self.today_str} - ReadAloud.mp3"
        self.assertEqual(res, expected)

    def test_whitespace_and_newlines(self):
        """Verify multiline text and tabs are split properly into words"""
        text = "  First\nsecond\tthird\n\nfourth   fifth sixth seventh  "
        res = self.window._generate_default_audio_filename(text)
        expected = f"{self.today_str} - First second third fourth fifth.mp3"
        self.assertEqual(res, expected)

    def test_sanitization_of_illegal_characters(self):
        """Verify characters illegal in filenames like / \\ : * ? \" < > | are stripped"""
        text = 'What: "Is" / this? *Special* <file> | test'
        res = self.window._generate_default_audio_filename(text)
        # Slashes, colons, quotes, question marks, asterisks, brackets stripped
        self.assertNotIn("/", res)
        self.assertNotIn(":", res)
        self.assertNotIn('"', res)
        self.assertNotIn("?", res)
        self.assertTrue(res.endswith(".mp3"))
        self.assertTrue(res.startswith(self.today_str))

if __name__ == '__main__':
    unittest.main()
