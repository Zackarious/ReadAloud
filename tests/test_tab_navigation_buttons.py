import unittest
import os
import tempfile
import subprocess

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


class TestTabNavigationButtons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow()

    def tearDown(self):
        if hasattr(self.window, 'stop_playback') and self.window.is_playing:
            self.window.stop_playback()

    def test_widgets_exist(self):
        """Verify tab navigation overlay and button widgets are bound from template."""
        self.assertIsNotNone(self.window.tab_bar_overlay)
        self.assertIsInstance(self.window.tab_bar_overlay, Gtk.Overlay)
        self.assertIsNotNone(self.window.tab_nav_prev_revealer)
        self.assertIsInstance(self.window.tab_nav_prev_revealer, Gtk.Revealer)
        self.assertIsNotNone(self.window.tab_nav_prev_btn)
        self.assertIsInstance(self.window.tab_nav_prev_btn, Gtk.Button)
        self.assertIsNotNone(self.window.tab_nav_next_revealer)
        self.assertIsInstance(self.window.tab_nav_next_revealer, Gtk.Revealer)
        self.assertIsNotNone(self.window.tab_nav_next_btn)
        self.assertIsInstance(self.window.tab_nav_next_btn, Gtk.Button)

    def test_button_css_classes(self):
        """Verify navigation buttons have circular, flat, and tab-nav-btn CSS classes."""
        for btn in (self.window.tab_nav_prev_btn, self.window.tab_nav_next_btn):
            classes = btn.get_css_classes()
            self.assertIn("circular", classes)
            self.assertIn("flat", classes)
            self.assertIn("tab-nav-btn", classes)

    def test_single_tab_hover_does_not_reveal(self):
        """With only 1 tab open, hovering over tab bar should not reveal the buttons."""
        self.assertEqual(self.window.tab_view.get_n_pages(), 1)
        self.window._on_tab_bar_enter()
        self.assertFalse(self.window.tab_nav_prev_revealer.get_reveal_child())
        self.assertFalse(self.window.tab_nav_next_revealer.get_reveal_child())
        self.assertFalse(self.window.tab_nav_prev_revealer.get_can_target())
        self.assertFalse(self.window.tab_nav_next_revealer.get_can_target())

    def test_multiple_tabs_hover_reveals_and_leave_hides(self):
        """With 2+ tabs open, hovering reveals buttons; leaving hides them."""
        self.window.create_new_tab(title="Tab 2")
        self.assertEqual(self.window.tab_view.get_n_pages(), 2)

        # Hover enters tab bar
        self.window._on_tab_bar_enter()
        self.assertTrue(self.window.tab_nav_prev_revealer.get_reveal_child())
        self.assertTrue(self.window.tab_nav_next_revealer.get_reveal_child())
        self.assertTrue(self.window.tab_nav_prev_revealer.get_can_target())
        self.assertTrue(self.window.tab_nav_next_revealer.get_can_target())

        # Hover leaves tab bar
        self.window._on_tab_bar_leave()
        self.assertFalse(self.window.tab_nav_prev_revealer.get_reveal_child())
        self.assertFalse(self.window.tab_nav_next_revealer.get_reveal_child())
        self.assertFalse(self.window.tab_nav_prev_revealer.get_can_target())
        self.assertFalse(self.window.tab_nav_next_revealer.get_can_target())

    def test_button_sensitivity_on_tab_positions(self):
        """First tab: prev disabled, next enabled. Last tab: next disabled, prev enabled."""
        p2 = self.window.create_new_tab(title="Tab 2")
        p3 = self.window.create_new_tab(title="Tab 3")
        self.assertEqual(self.window.tab_view.get_n_pages(), 3)

        # Switch to first tab (index 0)
        p1 = self.window.tab_view.get_nth_page(0)
        self.window.tab_view.set_selected_page(p1)
        self.window._update_tab_nav_buttons()
        self.assertFalse(self.window.tab_nav_prev_btn.get_sensitive())
        self.assertTrue(self.window.tab_nav_next_btn.get_sensitive())

        # Switch to middle tab (index 1)
        self.window.tab_view.set_selected_page(p2)
        self.window._update_tab_nav_buttons()
        self.assertTrue(self.window.tab_nav_prev_btn.get_sensitive())
        self.assertTrue(self.window.tab_nav_next_btn.get_sensitive())

        # Switch to last tab (index 2)
        self.window.tab_view.set_selected_page(p3)
        self.window._update_tab_nav_buttons()
        self.assertTrue(self.window.tab_nav_prev_btn.get_sensitive())
        self.assertFalse(self.window.tab_nav_next_btn.get_sensitive())

    def test_navigate_next_and_previous_tab(self):
        """Clicking next and previous methods cycles correctly between tabs."""
        p2 = self.window.create_new_tab(title="Tab 2")
        p3 = self.window.create_new_tab(title="Tab 3")
        p1 = self.window.tab_view.get_nth_page(0)

        self.window.tab_view.set_selected_page(p1)
        self.assertEqual(self.window.tab_view.get_selected_page(), p1)

        # Navigate next
        self.window.navigate_next_tab()
        self.assertEqual(self.window.tab_view.get_selected_page(), p2)

        self.window.navigate_next_tab()
        self.assertEqual(self.window.tab_view.get_selected_page(), p3)

        # Navigate previous
        self.window.navigate_previous_tab()
        self.assertEqual(self.window.tab_view.get_selected_page(), p2)

        self.window.navigate_previous_tab()
        self.assertEqual(self.window.tab_view.get_selected_page(), p1)


if __name__ == '__main__':
    unittest.main()
