import unittest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

from src.window import (
    ReadAloudWindow,
    SPEED_CHOICES,
    VOICE_MODEL_SPEEDS,
    get_speed_for_voice,
)


class TestSpeedDropdown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_all_35_model_speeds_exact(self):
        """Verify all 35 Piper models match the user's exact required Slower, Slow, Normal, Fast, and Super Fast speeds."""
        expected_speeds = {
            "en_GB-alan-low": (0.6, 0.7, 0.8, 1.0, 1.2),
            "en_GB-alan-medium": (0.8, 0.9, 1.0, 1.2, 1.4),
            "en_GB-alba-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_GB-aru-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_GB-cori-high": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_GB-cori-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_GB-jenny_dioco-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_GB-northern_english_male-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_GB-semaine-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_GB-southern_english_female-low": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_GB-vctk-medium": (0.2, 0.3, 0.4, 0.9, 1.2),
            "en_US-amy-low": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-amy-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-arctic-medium": (0.4, 0.5, 0.6, 0.9, 1.2),
            "en_US-bryce-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-danny-low": (0.4, 0.5, 0.6, 0.9, 1.2),
            "en_US-hfc_female-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-hfc_male-medium": (0.7, 0.8, 0.9, 1.2, 1.5),
            "en_US-joe-medium": (0.7, 0.8, 0.9, 1.2, 1.5),
            "en_US-john-medium": (0.8, 0.9, 1.0, 1.2, 1.4),
            "en_US-kathleen-low": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-kristin-medium": (0.8, 0.9, 1.0, 1.2, 1.4),
            "en_US-kusal-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-l2arctic-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-lessac-high": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-lessac-low": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-lessac-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-libritts-high": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-libritts_r-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-ljspeech-high": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-ljspeech-medium": (0.6, 0.7, 0.8, 1.1, 1.4),
            "en_US-norman-medium": (0.4, 0.5, 0.6, 0.9, 1.2),
            "en_US-ryan-high": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-ryan-low": (0.5, 0.6, 0.7, 1.0, 1.3),
            "en_US-ryan-medium": (0.5, 0.6, 0.7, 1.0, 1.3),
        }

        self.assertEqual(len(VOICE_MODEL_SPEEDS), 35)
        for model_id, (slw, sl, n, f, sf) in expected_speeds.items():
            self.assertIn(model_id, VOICE_MODEL_SPEEDS, f"Missing model: {model_id}")
            entry = VOICE_MODEL_SPEEDS[model_id]
            self.assertAlmostEqual(entry["Slower"], slw, places=2, msg=f"Slower speed mismatch for {model_id}")
            self.assertAlmostEqual(entry["Slow"], sl, places=2, msg=f"Slow speed mismatch for {model_id}")
            self.assertAlmostEqual(entry["Normal"], n, places=2, msg=f"Normal speed mismatch for {model_id}")
            self.assertAlmostEqual(entry["Fast"], f, places=2, msg=f"Fast speed mismatch for {model_id}")
            self.assertAlmostEqual(entry["Super Fast"], sf, places=2, msg=f"Super Fast speed mismatch for {model_id}")

            # Verify get_speed_for_voice helper resolves with and without .onnx
            self.assertAlmostEqual(get_speed_for_voice(model_id, "Slower"), slw)
            self.assertAlmostEqual(get_speed_for_voice(f"{model_id}.onnx", "Slower"), slw)
            self.assertAlmostEqual(get_speed_for_voice(model_id, "Slow"), sl)
            self.assertAlmostEqual(get_speed_for_voice(f"{model_id}.onnx", "Slow"), sl)
            self.assertAlmostEqual(get_speed_for_voice(model_id, "Normal"), n)
            self.assertAlmostEqual(get_speed_for_voice(f"{model_id}.onnx", "Normal"), n)
            self.assertAlmostEqual(get_speed_for_voice(model_id, "Fast"), f)
            self.assertAlmostEqual(get_speed_for_voice(f"{model_id}.onnx", "Fast"), f)
            self.assertAlmostEqual(get_speed_for_voice(model_id, "Super Fast"), sf)
            self.assertAlmostEqual(get_speed_for_voice(f"{model_id}.onnx", "Super Fast"), sf)

    def test_unknown_voice_fallback(self):
        """Unknown or empty voice IDs must safely fall back to default speeds."""
        self.assertEqual(get_speed_for_voice("non-existent-voice", "Slower"), 0.8)
        self.assertEqual(get_speed_for_voice("non-existent-voice", "Slow"), 0.9)
        self.assertEqual(get_speed_for_voice("non-existent-voice", "Normal"), 1.0)
        self.assertEqual(get_speed_for_voice("non-existent-voice", "Fast"), 1.2)
        self.assertEqual(get_speed_for_voice("non-existent-voice", "Super Fast"), 1.4)
        self.assertEqual(get_speed_for_voice("", "Normal"), 1.0)
        self.assertEqual(get_speed_for_voice(None, "Normal"), 1.0)

    def test_speed_dropdown_ui_elements(self):
        """Verify speed_button and speed_chooser dropdown exist in window with all 5 options."""
        window = ReadAloudWindow()
        self.assertIsNotNone(window.speed_button)
        self.assertIsNotNone(window.speed_chooser)
        self.assertIsInstance(window.speed_chooser, Gtk.DropDown)

        # Check model items
        model = window.speed_chooser.get_model()
        self.assertIsNotNone(model)
        self.assertEqual(model.get_n_items(), 5)
        self.assertEqual(model.get_string(0), "Slower")
        self.assertEqual(model.get_string(1), "Slow")
        self.assertEqual(model.get_string(2), "Normal")
        self.assertEqual(model.get_string(3), "Fast")
        self.assertEqual(model.get_string(4), "Super Fast")

        # Initial selection should default to Normal (index 2)
        self.assertEqual(window.speed_chooser.get_selected(), 2)

    def test_speed_chooser_get_and_set_value(self):
        """Verify get_value() and set_value() on speed_chooser."""
        window = ReadAloudWindow()
        # Mock voice to en_GB-alan-low (Slower: 0.6, Slow: 0.7, Normal: 0.8, Fast: 1.0, Super Fast: 1.2)
        window._get_selected_voice_name = lambda: "en_GB-alan-low"

        # Initially Normal (2)
        window.speed_chooser.set_selected(2)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.8)

        # Select Slower (0)
        window.speed_chooser.set_selected(0)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.6)

        # Select Slow (1)
        window.speed_chooser.set_selected(1)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.7)

        # Select Fast (3)
        window.speed_chooser.set_selected(3)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 1.0)

        # Select Super Fast (4)
        window.speed_chooser.set_selected(4)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 1.2)

        # Test set_value with string
        window.speed_chooser.set_value("Slower")
        self.assertEqual(window.speed_chooser.get_selected(), 0)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.6)

        window.speed_chooser.set_value("Slow")
        self.assertEqual(window.speed_chooser.get_selected(), 1)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.7)

        window.speed_chooser.set_value("Normal")
        self.assertEqual(window.speed_chooser.get_selected(), 2)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 0.8)

        window.speed_chooser.set_value("Fast")
        self.assertEqual(window.speed_chooser.get_selected(), 3)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 1.0)

        window.speed_chooser.set_value("Super Fast")
        self.assertEqual(window.speed_chooser.get_selected(), 4)
        self.assertAlmostEqual(window.speed_chooser.get_value(), 1.2)

        # Test set_value with float (closest match)
        window.speed_chooser.set_value(0.62)
        self.assertEqual(window.speed_chooser.get_selected(), 0)

        window.speed_chooser.set_value(0.71)
        self.assertEqual(window.speed_chooser.get_selected(), 1)

        window.speed_chooser.set_value(0.82)
        self.assertEqual(window.speed_chooser.get_selected(), 2)

        window.speed_chooser.set_value(1.18)
        self.assertEqual(window.speed_chooser.get_selected(), 4)

    def test_speed_chooser_dropdown_selection_tick(self):
        """Verify the speed chooser popup list places a tick mark next to the currently selected option."""
        window = ReadAloudWindow()
        dropdown = window.speed_chooser
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

        items = [MockListItem(i) for i in range(5)]
        labels = ["Slower", "Slow", "Normal", "Fast", "Super Fast"]
        for item, lbl in zip(items, labels):
            item.set_item(Gtk.StringObject.new(lbl))
            list_factory.emit("setup", item)

        dropdown.set_selected(2)  # Normal
        for item in items:
            list_factory.emit("bind", item)

        # Item 2 (Normal) is selected -> has tick
        self.assertFalse(items[0].get_child().get_text().startswith("✓ "))
        self.assertFalse(items[1].get_child().get_text().startswith("✓ "))
        self.assertTrue(items[2].get_child().get_text().startswith("✓ "))
        self.assertFalse(items[3].get_child().get_text().startswith("✓ "))
        self.assertFalse(items[4].get_child().get_text().startswith("✓ "))

        # Switch to Slow (1) -> tick updates dynamically
        dropdown.set_selected(1)
        self.assertTrue(items[1].get_child().get_text().startswith("✓ "))
        self.assertFalse(items[2].get_child().get_text().startswith("✓ "))

        # Switch to Slower (0) -> tick updates dynamically
        dropdown.set_selected(0)
        self.assertTrue(items[0].get_child().get_text().startswith("✓ "))
        self.assertFalse(items[1].get_child().get_text().startswith("✓ "))

    def test_increase_and_decrease_speed_stepping(self):
        """increase_speed and decrease_speed step between Slower (0), Slow (1), Normal (2), Fast (3), and Super Fast (4)."""
        window = ReadAloudWindow()
        window.speed_chooser.set_selected(2)  # Normal

        window.increase_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 3)  # Fast

        window.increase_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 4)  # Super Fast

        # Increase past bound stays at Super Fast
        window.increase_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 4)

        window.decrease_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 3)  # Fast

        window.decrease_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 2)  # Normal

        window.decrease_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 1)  # Slow

        window.decrease_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 0)  # Slower

        # Decrease past bound stays at Slower
        window.decrease_speed()
        self.assertEqual(window.speed_chooser.get_selected(), 0)


if __name__ == '__main__':
    unittest.main()
