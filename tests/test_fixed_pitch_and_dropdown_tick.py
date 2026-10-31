import unittest
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

from src.window import ReadAloudWindow, FIXED_VOICE_PITCHES, get_pitch_for_voice


class TestFixedPitchAndDropdownTick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_all_35_model_pitches_exact(self):
        """Verify all 35 Piper models match the user's exact required fixed pitches."""
        expected_pitches = {
            "en_GB-alan-low": 1.0,
            "en_GB-alan-medium": 1.2,
            "en_GB-alba-medium": 1.2,
            "en_GB-aru-medium": 1.3,
            "en_GB-cori-high": 1.2,
            "en_GB-cori-medium": 1.2,
            "en_GB-jenny_dioco-medium": 1.2,
            "en_GB-northern_english_male-medium": 1.2,
            "en_GB-semaine-medium": 1.0,
            "en_GB-southern_english_female-low": 0.8,
            "en_GB-vctk-medium": 1.2,
            "en_US-amy-low": 0.9,
            "en_US-amy-medium": 1.2,
            "en_US-arctic-medium": 1.4,
            "en_US-bryce-medium": 1.3,
            "en_US-danny-low": 1.0,
            "en_US-hfc_female-medium": 1.1,
            "en_US-hfc_male-medium": 1.1,
            "en_US-joe-medium": 1.2,
            "en_US-john-medium": 1.1,
            "en_US-kathleen-low": 0.9,
            "en_US-kristin-medium": 1.0,
            "en_US-kusal-medium": 1.3,
            "en_US-l2arctic-medium": 1.3,
            "en_US-lessac-high": 1.2,
            "en_US-lessac-low": 0.9,
            "en_US-lessac-medium": 1.1,
            "en_US-libritts-high": 1.3,
            "en_US-libritts_r-medium": 1.2,
            "en_US-ljspeech-high": 1.2,
            "en_US-ljspeech-medium": 1.2,
            "en_US-norman-medium": 1.4,
            "en_US-ryan-high": 1.2,
            "en_US-ryan-low": 0.8,
            "en_US-ryan-medium": 1.2,
        }

        self.assertEqual(len(FIXED_VOICE_PITCHES), 35)
        for model_id, expected_pitch in expected_pitches.items():
            self.assertIn(model_id, FIXED_VOICE_PITCHES, f"Missing model: {model_id}")
            self.assertAlmostEqual(
                FIXED_VOICE_PITCHES[model_id],
                expected_pitch,
                places=2,
                msg=f"Pitch mismatch for {model_id}"
            )
            # Also verify helper resolves with or without .onnx
            self.assertAlmostEqual(get_pitch_for_voice(model_id), expected_pitch)
            self.assertAlmostEqual(get_pitch_for_voice(f"{model_id}.onnx"), expected_pitch)

    def test_unknown_voice_fallback(self):
        """Unknown or empty voice IDs must safely fall back to pitch 1.0."""
        self.assertEqual(get_pitch_for_voice("non-existent-voice"), 1.0)
        self.assertEqual(get_pitch_for_voice(""), 1.0)
        self.assertEqual(get_pitch_for_voice(None), 1.0)

    def test_pitch_ui_button_removed_from_window(self):
        """Verify pitch button and slider are removed from window UI while speed button remains."""
        window = ReadAloudWindow()
        self.assertFalse(hasattr(window, 'pitch_button') and isinstance(window.pitch_button, Gtk.Widget),
                         "pitch_button should no longer be a template child widget")
        self.assertIsNotNone(window.speed_button)
        self.assertIsNotNone(window.speed_chooser)

    def test_voice_chooser_dropdown_selection_tick(self):
        """Verify the voice chooser popup list places a tick mark next to the currently selected model."""
        window = ReadAloudWindow()
        dropdown = window.voice_chooser
        list_factory = dropdown.get_list_factory()
        self.assertIsNotNone(list_factory)

        # Create dummy list items that implement get_position()
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

        str0 = Gtk.StringObject.new("Alan Voice - Low quality")
        str1 = MockListItem(1)
        str1 = Gtk.StringObject.new("Alan Voice - Medium quality")

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
        self.assertTrue(label0.get_text().startswith("✓ "), f"Selected item should have tick: {label0.get_text()}")
        self.assertFalse(label1.get_text().startswith("✓ "), f"Unselected item should not have tick: {label1.get_text()}")

        # Change selection to 1 -> tick updates dynamically
        dropdown.set_selected(1)
        self.assertFalse(label0.get_text().startswith("✓ "), "Item 0 should no longer have tick")
        self.assertTrue(label1.get_text().startswith("✓ "), "Item 1 should now have tick")


if __name__ == '__main__':
    unittest.main()
