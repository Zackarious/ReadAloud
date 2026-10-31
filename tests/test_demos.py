import unittest
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

import subprocess
import tempfile

# Dynamically compile and register gresource if needed
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
    res = Gio.Resource.load(tmp_res_path)
    res._register()
    os.unlink(tmp_res_path)

from src.demos import DEMOS
from src.window import ReadAloudWindow

class TestDemos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_demos_metadata(self):
        """Verify all three preset demos have correct texts, voices, pitches, and speeds."""
        self.assertIn("demo_1", DEMOS)
        self.assertIn("demo_2", DEMOS)
        self.assertIn("demo_3", DEMOS)

        # Demo 1
        d1 = DEMOS["demo_1"]
        self.assertEqual(d1["language"], "English (UK)")
        self.assertEqual(d1["voice_id"], "en_GB-jenny_dioco-medium")
        self.assertEqual(d1["pitch"], 1.3)
        self.assertEqual(d1["speed"], 0.6)
        self.assertTrue(d1["text"].startswith("The betrayal of William Wallace"))
        self.assertTrue("Fause Menteith" in d1["text"])

        # Demo 2
        d2 = DEMOS["demo_2"]
        self.assertEqual(d2["language"], "English (UK)")
        self.assertEqual(d2["voice_id"], "en_GB-northern_english_male-medium")
        self.assertEqual(d2["pitch"], 1.2)
        self.assertEqual(d2["speed"], 0.6)
        self.assertTrue(d2["text"].startswith("King Henry VIII died on January 28, 1547"))
        self.assertTrue("chronic osteomyelitis" in d2["text"])

        # Demo 3
        d3 = DEMOS["demo_3"]
        self.assertEqual(d3["language"], "English (US)")
        self.assertEqual(d3["voice_id"], "en_US-joe-medium")
        self.assertEqual(d3["pitch"], 1.2)
        self.assertEqual(d3["speed"], 0.6)
        self.assertTrue(d3["text"].startswith("The original inhabitants of the land"))
        self.assertTrue("Ancestral Puebloans" in d3["text"])

    def test_load_demo_empty_buffer(self):
        """When text buffer is empty, load_demo immediately loads and plays without warning dialog."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.main_text_view = Gtk.TextView()
        buffer = window.main_text_view.get_buffer()
        buffer.set_text("")

        warning_shown = []
        applied_demos = []

        window._show_overwrite_warning = lambda d: warning_shown.append(d)
        window._apply_and_play_demo = lambda d: applied_demos.append(d)

        param = GLib.Variant("s", "demo_1")
        window.on_load_demo_action(None, param)

        self.assertEqual(len(warning_shown), 0, "Warning dialog should NOT be shown for empty buffer")
        self.assertEqual(len(applied_demos), 1, "Demo should be applied immediately")
        self.assertEqual(applied_demos[0]["voice_id"], "en_GB-jenny_dioco-medium")

    def test_load_demo_non_empty_buffer(self):
        """When text buffer contains existing text, load_demo presents overwrite warning dialog."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.main_text_view = Gtk.TextView()
        buffer = window.main_text_view.get_buffer()
        buffer.set_text("Some existing user notes that should not be lost.")

        warning_shown = []
        applied_demos = []

        window._show_overwrite_warning = lambda d: warning_shown.append(d)
        window._apply_and_play_demo = lambda d: applied_demos.append(d)

        param = GLib.Variant("s", "demo_2")
        window.on_load_demo_action(None, param)

        self.assertEqual(len(warning_shown), 1, "Warning dialog SHOULD be shown when buffer has text")
        self.assertEqual(len(applied_demos), 0, "Demo should not be applied until user confirms")
        self.assertEqual(warning_shown[0]["voice_id"], "en_GB-northern_english_male-medium")

    def test_apply_and_play_demo(self):
        """Verify _apply_and_play_demo stops previous playback, sets text, adjustments, voice, and calls read_text."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.main_text_view = Gtk.TextView()
        window.is_playing = True
        window.read_button = Gtk.Button()

        stopped = []
        window.stop_playback = lambda: stopped.append(True)
        window._clear_highlight = lambda: None

        # Adjustments
        window.adjustment_1 = Gtk.Adjustment.new(1.0, 0.4, 1.8, 0.1, 0.5, 0.0)
        window.adjustment_2 = Gtk.Adjustment.new(1.0, 0.1, 2.0, 0.1, 0.5, 0.0)

        # Dropdowns
        lang_model = Gtk.StringList.new(["English (US)", "English (UK)"])
        window.lang_chooser = Gtk.DropDown.new(lang_model, None)
        window.lang_chooser.set_selected(0)

        voice_model = Gtk.StringList.new(["Ryan High", "Jenny Dioco"])
        window.voice_chooser = Gtk.DropDown.new(voice_model, None)
        window.current_voices = [
            {"id": "en_US-ryan-high", "raw_voice_name": "ryan"},
            {"id": "en_GB-jenny_dioco-medium", "raw_voice_name": "jenny_dioco"}
        ]

        def fake_update_voice_chooser(lang):
            if lang == "English (UK)":
                window.current_voices = [
                    {"id": "en_GB-northern_english_male-medium", "raw_voice_name": "northern_english_male"},
                    {"id": "en_GB-jenny_dioco-medium", "raw_voice_name": "jenny_dioco"}
                ]
                window.voice_chooser.set_model(Gtk.StringList.new(["Northern Male", "Jenny"]))
        window._update_voice_chooser = fake_update_voice_chooser

        read_text_called = []
        window.read_text = lambda btn: read_text_called.append(btn)

        # Apply Demo 1
        d1 = DEMOS["demo_1"]
        window._apply_and_play_demo(d1)

        # 1. Stopped previous playback
        self.assertEqual(len(stopped), 1)

        # 2. Text buffer matches demo text
        buf = window.main_text_view.get_buffer()
        start, end = buf.get_bounds()
        self.assertEqual(buf.get_text(start, end, False), d1["text"])

        # 3. Cursor placed at start
        cursor_iter = buf.get_iter_at_mark(buf.get_insert())
        self.assertEqual(cursor_iter.get_offset(), 0)

        # 4. Language selected
        selected_lang_idx = window.lang_chooser.get_selected()
        self.assertEqual(lang_model.get_string(selected_lang_idx), "English (UK)")

        # 5. Voice selected matches Jenny
        selected_voice_idx = window.voice_chooser.get_selected()
        self.assertEqual(window.current_voices[selected_voice_idx]["id"], "en_GB-jenny_dioco-medium")

        # 6. Pitch and Speed
        self.assertAlmostEqual(window.adjustment_1.get_value(), 1.3)
        self.assertAlmostEqual(window.adjustment_2.get_value(), 0.6)

        # 7. read_text invoked
        self.assertEqual(len(read_text_called), 1)

    def test_voice_id_resolution_high_quality(self):
        """Verify that Reader voice matching prefers exact voice_id so ryan-high is not shadowed by ryan-low."""
        voices = [
            {'id': 'en_US-ryan-low', 'name': 'Ryan'},
            {'id': 'en_US-ryan-medium', 'name': 'Ryan'},
            {'id': 'en_US-ryan-high', 'name': 'Ryan'}
        ]
        target = "en_US-ryan-high"

        voice_id = None
        for v in voices:
            if v['id'] == target:
                voice_id = v['id']
                break
        if not voice_id:
            for v in voices:
                if v['name'].lower() == target.lower():
                    voice_id = v['id']
                    break

        self.assertEqual(voice_id, "en_US-ryan-high")

    def test_update_wait_dialog_progress_and_countdown(self):
        """Verify update_wait_dialog updates progress bar fraction and countdown status label."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.wait_dialog = Gtk.Window()
        window.progress_bar = Gtk.ProgressBar()
        window.progress_label = Gtk.Label()

        # Update to 40% with countdown
        msg = "Generating audio: 40% (~5s remaining)"
        window.update_wait_dialog(0.4, msg)

        self.assertAlmostEqual(window.progress_bar.get_fraction(), 0.4)
        self.assertEqual(window.progress_label.get_text(), msg)

        # Clamping test
        window.update_wait_dialog(1.5, "Finalizing audio...")
        self.assertAlmostEqual(window.progress_bar.get_fraction(), 1.0)
        self.assertEqual(window.progress_label.get_text(), "Finalizing audio...")

if __name__ == '__main__':
    unittest.main()
