import unittest
import os
import xml.etree.ElementTree as ET
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from src.window import ReadAloudWindow


class TestButtonRecolour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_buttons_have_highlight_accent_css_class(self):
        """Verify open_button, read_button, pause_button, and stop_button have highlight-accent-btn class."""
        window = ReadAloudWindow()
        # Process any pending idle callbacks
        ctx = GLib.MainContext.default()
        while ctx.iteration(False):
            pass

        self.assertTrue(window.open_button.has_css_class("highlight-accent-btn") or
                        window.open_button.get_style_context().has_class("highlight-accent-btn"))
        self.assertTrue(window.read_button.has_css_class("highlight-accent-btn") or
                        window.read_button.get_style_context().has_class("highlight-accent-btn"))
        self.assertTrue(window.pause_button.has_css_class("highlight-accent-btn") or
                        window.pause_button.get_style_context().has_class("highlight-accent-btn"))
        self.assertTrue(window.stop_button.has_css_class("highlight-accent-btn") or
                        window.stop_button.get_style_context().has_class("highlight-accent-btn"))

    def test_css_styling_uses_highlight_color(self):
        """Verify CSS contains #f6d32d rules for open, read, pause, and stop buttons."""
        window_py_path = os.path.join(os.path.dirname(__file__), "..", "src", "window.py")
        with open(window_py_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("#f6d32d", code)
        self.assertIn(".highlight-accent-btn", code)
        self.assertIn("#open_button", code)
        self.assertIn("#read_button", code)
        self.assertIn("#pause_button", code)
        self.assertIn("#stop_button", code)

    def test_folder_open_svg_fill_matches_highlight(self):
        """Verify the Open Text file icon SVG exists and uses #f6d32d."""
        svg_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "icons",
            "hicolor",
            "scalable",
            "actions",
            "im.zackarious.ReadAloud.folder-open.svg"
        )
        self.assertTrue(os.path.isfile(svg_path), f"SVG missing at {svg_path}")

        tree = ET.parse(svg_path)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith("svg"))

        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("#f6d32d", content)

    def test_gresource_bundle_contains_folder_open_svg(self):
        """Verify GResource manifest includes action icons."""
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "src", "readaloud.gresource.xml")
        self.assertTrue(os.path.isfile(manifest_path))

        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("icons/im.zackarious.ReadAloud.folder-open.svg", content)
        self.assertIn("icons/im.zackarious.ReadAloud.eye-symbolic.svg", content)
        self.assertIn("icons/im.zackarious.ReadAloud.import-symbolic.svg", content)

    def test_playback_state_toggles_preserve_styling(self):
        """Verify switching between playback states preserves the highlight-accent-btn styling."""
        window = ReadAloudWindow()
        ctx = GLib.MainContext.default()
        while ctx.iteration(False):
            pass

        # Check in idle state
        self.assertTrue(window.read_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.pause_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.stop_button.has_css_class("highlight-accent-btn"))

        # Transition to playing state
        window.is_playing = True
        window._update_playback_toolbar_visibility()
        while ctx.iteration(False):
            pass
        self.assertTrue(window.read_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.pause_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.stop_button.has_css_class("highlight-accent-btn"))

        # Transition back to stopped state
        window.is_playing = False
        window._update_playback_toolbar_visibility()
        while ctx.iteration(False):
            pass
        self.assertTrue(window.read_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.pause_button.has_css_class("highlight-accent-btn"))
        self.assertTrue(window.stop_button.has_css_class("highlight-accent-btn"))


if __name__ == "__main__":
    unittest.main()
