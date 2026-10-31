import unittest
import os
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, Gdk

from src.window import ReadAloudWindow
from src.main import ReadAloudApplication


class TestKeyboardShortcuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow.__new__(ReadAloudWindow)
        self.window.is_playing = False
        self.window.is_paused = False
        self.window.read_button = Gtk.Button()
        self.window.pause_button = Gtk.Button()
        self.window.save_button = Gtk.Button()
        self.window.main_text_view = Gtk.TextView()
        self.window.adjustment_2 = Gtk.Adjustment.new(1.0, 0.1, 2.0, 0.1, 0.5, 0.0)

    def test_increase_speed_step(self):
        """increase_speed increments speed by 0.1 correctly."""
        self.window.adjustment_2.set_value(1.0)
        self.window.increase_speed(0.1)
        self.assertAlmostEqual(self.window.adjustment_2.get_value(), 1.1)

        # Increment up to upper bound
        self.window.adjustment_2.set_value(1.95)
        self.window.increase_speed(0.1)
        self.assertAlmostEqual(self.window.adjustment_2.get_value(), 2.0)

    def test_decrease_speed_step(self):
        """decrease_speed decrements speed by 0.1 correctly."""
        self.window.adjustment_2.set_value(1.0)
        self.window.decrease_speed(0.1)
        self.assertAlmostEqual(self.window.adjustment_2.get_value(), 0.9)

        # Decrement down to lower bound
        self.window.adjustment_2.set_value(0.15)
        self.window.decrease_speed(0.1)
        self.assertAlmostEqual(self.window.adjustment_2.get_value(), 0.1)

    def test_play_audio_starts_playback_when_stopped(self):
        """play_audio calls read_text when not currently playing."""
        read_text_called = []
        self.window.read_text = lambda *args: read_text_called.append(True)
        self.window.play_audio()
        self.assertEqual(len(read_text_called), 1)

    def test_play_audio_toggles_pause_when_playing(self):
        """play_audio calls toggle_pause when currently playing."""
        self.window.is_playing = True
        toggle_pause_called = []
        self.window.toggle_pause = lambda: toggle_pause_called.append(True)
        self.window.play_audio()
        self.assertEqual(len(toggle_pause_called), 1)

    def test_key_pressed_ctrl_p(self):
        """Ctrl + P triggers play_audio and returns True."""
        play_called = []
        self.window.play_audio = lambda: play_called.append(True)
        handled = self.window._on_key_pressed(None, Gdk.KEY_p, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled)
        self.assertEqual(len(play_called), 1)

        handled_upper = self.window._on_key_pressed(None, Gdk.KEY_P, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_upper)
        self.assertEqual(len(play_called), 2)

    def test_key_pressed_ctrl_e(self):
        """Ctrl + E triggers save_audio_dialog and returns True."""
        save_called = []
        self.window.save_audio_dialog = lambda *args: save_called.append(True)
        handled = self.window._on_key_pressed(None, Gdk.KEY_e, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled)
        self.assertEqual(len(save_called), 1)

        handled_upper = self.window._on_key_pressed(None, Gdk.KEY_E, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_upper)
        self.assertEqual(len(save_called), 2)

    def test_key_pressed_ctrl_up(self):
        """Ctrl + Up triggers increase_speed and returns True."""
        inc_called = []
        self.window.increase_speed = lambda: inc_called.append(True)
        handled = self.window._on_key_pressed(None, Gdk.KEY_Up, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled)
        self.assertEqual(len(inc_called), 1)

        handled_kp = self.window._on_key_pressed(None, Gdk.KEY_KP_Up, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_kp)
        self.assertEqual(len(inc_called), 2)

    def test_key_pressed_ctrl_down(self):
        """Ctrl + Down triggers decrease_speed and returns True."""
        dec_called = []
        self.window.decrease_speed = lambda: dec_called.append(True)
        handled = self.window._on_key_pressed(None, Gdk.KEY_Down, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled)
        self.assertEqual(len(dec_called), 1)

        handled_kp = self.window._on_key_pressed(None, Gdk.KEY_KP_Down, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_kp)
        self.assertEqual(len(dec_called), 2)

    def test_unhandled_keys_return_false(self):
        """Keys other than shortcuts return False for standard handling."""
        handled = self.window._on_key_pressed(None, Gdk.KEY_a, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertFalse(handled)
        handled_arrow = self.window._on_key_pressed(None, Gdk.KEY_Up, 0, Gdk.ModifierType.NO_MODIFIER_MASK)
        self.assertFalse(handled_arrow)

    def test_application_action_accelerators(self):
        """Application registers accelerators for play-audio, save-audio-as, speed-up, speed-down."""
        app = ReadAloudApplication()
        accels_play = app.get_accels_for_action("win.play-audio")
        accels_save_audio = app.get_accels_for_action("win.save-audio-as")
        accels_speed_up = app.get_accels_for_action("win.speed-up")
        accels_speed_down = app.get_accels_for_action("win.speed-down")

        self.assertIn("<Control>p", accels_play)
        self.assertIn("<Control>e", accels_save_audio)
        self.assertIn("<Control>Up", accels_speed_up)
        self.assertIn("<Control>Down", accels_speed_down)

    def test_help_overlay_shortcuts_xml(self):
        """Help overlay UI defines shortcuts for File and Playback."""
        ui_path = os.path.join(os.path.dirname(__file__), "..", "src", "gtk", "help-overlay.ui")
        tree = ET.parse(ui_path)
        root = tree.getroot()

        shortcuts = {}
        for s in root.findall(".//object[@class='GtkShortcutsShortcut']"):
            action = None
            accel = None
            for prop in s.findall("property"):
                if prop.attrib.get("name") == "action-name":
                    action = prop.text
                elif prop.attrib.get("name") == "accelerator":
                    accel = prop.text
            if action:
                shortcuts[action] = accel

        self.assertIn("win.save-audio-as", shortcuts)
        self.assertEqual(shortcuts["win.save-audio-as"], "<primary>e")
        self.assertIn("win.play-audio", shortcuts)
        self.assertIn("<primary>p", shortcuts["win.play-audio"])
        self.assertIn("win.speed-up", shortcuts)
        self.assertEqual(shortcuts["win.speed-up"], "<primary>Up")
        self.assertIn("win.speed-down", shortcuts)
        self.assertEqual(shortcuts["win.speed-down"], "<primary>Down")
        self.assertIn("win.toggle-maximize", shortcuts)
        self.assertEqual(shortcuts["win.toggle-maximize"], "F11")

    def test_header_bar_decoration_layout(self):
        """HeaderBar specifies :minimize,maximize,close decoration-layout."""
        window = ReadAloudWindow()
        self.assertTrue(hasattr(window, "header_bar"))
        self.assertEqual(window.header_bar.get_decoration_layout(), ":minimize,maximize,close")

    def test_window_controls_tooltips(self):
        """WindowControls buttons have appropriate tooltips for Minimize, Maximize/Restore, and Close."""
        window = ReadAloudWindow()
        self.assertTrue(hasattr(window, "_btn_minimize"))
        self.assertTrue(hasattr(window, "_btn_maximize"))
        self.assertTrue(hasattr(window, "_btn_close"))

        self.assertEqual(window._btn_minimize.get_tooltip_text(), "Minimize")
        self.assertEqual(window._btn_maximize.get_tooltip_text(), "Maximize")
        self.assertEqual(window._btn_close.get_tooltip_text(), "Close")

        # When window is maximized, maximize button tooltip changes to "Restore"
        window.is_maximized = lambda: True
        window._update_window_controls_tooltips()
        self.assertEqual(window._btn_maximize.get_tooltip_text(), "Restore")

        # When unmaximized, it reverts to "Maximize"
        window.is_maximized = lambda: False
        window._update_window_controls_tooltips()
        self.assertEqual(window._btn_maximize.get_tooltip_text(), "Maximize")

    def test_minimize_and_maximize_actions(self):
        """Window defines win.minimize and win.toggle-maximize actions and methods."""
        window = ReadAloudWindow()
        self.assertTrue(window.has_action("minimize"))
        self.assertTrue(window.has_action("toggle-maximize"))

        min_called = []
        max_called = []
        window.minimize_window = lambda: min_called.append(True)
        window.toggle_maximize_window = lambda: max_called.append(True)

        min_action = window.lookup_action("minimize")
        min_action.activate(None)
        self.assertEqual(len(min_called), 1)

        max_action = window.lookup_action("toggle-maximize")
        max_action.activate(None)
        self.assertEqual(len(max_called), 1)

    def test_f11_shortcut_toggles_maximize(self):
        """Pressing F11 triggers toggle_maximize_window."""
        window = ReadAloudWindow()
        toggle_called = []
        window.toggle_maximize_window = lambda: toggle_called.append(True)

        handled = window._on_key_pressed(None, Gdk.KEY_F11, 0, 0)
        self.assertTrue(handled)
        self.assertEqual(len(toggle_called), 1)

    def test_text_zoom_levels_and_shortcuts(self):
        """set_text_zoom scales up to 1000% and down to 70%, with zoom_in/out/reset operations."""
        window = ReadAloudWindow()
        window.zoom_reset()
        self.assertEqual(window.text_zoom_level, 130)

        # Zoom in increases by 10
        window.zoom_in()
        self.assertEqual(window.text_zoom_level, 140)

        # Zoom out decreases by 10
        window.zoom_out()
        self.assertEqual(window.text_zoom_level, 130)

        # Test maximum font size limit (1000%)
        window.set_text_zoom(800)
        self.assertEqual(window.text_zoom_level, 800)
        window.set_text_zoom(1000)
        self.assertEqual(window.text_zoom_level, 1000)
        window.set_text_zoom(1500)
        self.assertEqual(window.text_zoom_level, 1000)

        # Test minimum font size limit (70%)
        window.set_text_zoom(20)
        self.assertEqual(window.text_zoom_level, 70)

        # Test keyboard shortcuts
        window.zoom_reset()
        handled_plus = window._on_key_pressed(None, Gdk.KEY_plus, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_plus)
        self.assertEqual(window.text_zoom_level, 140)

        handled_minus = window._on_key_pressed(None, Gdk.KEY_minus, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_minus)
        self.assertEqual(window.text_zoom_level, 130)

        window.set_text_zoom(500)
        handled_zero = window._on_key_pressed(None, Gdk.KEY_0, 0, Gdk.ModifierType.CONTROL_MASK)
        self.assertTrue(handled_zero)
        self.assertEqual(window.text_zoom_level, 130)


if __name__ == '__main__':
    unittest.main()
