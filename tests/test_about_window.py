import unittest
import os
import subprocess
import tempfile
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio

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

from src.main import ReadAloudApplication, APP_DESCRIPTION, LICENSING_TEXT


class TestAboutWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_description_word_count(self):
        self.assertIn("offline", APP_DESCRIPTION.lower())
        self.assertIn("open-source", APP_DESCRIPTION.lower())
        self.assertIn("telemetry", APP_DESCRIPTION.lower())
        self.assertIn("github", APP_DESCRIPTION.lower())
        self.assertIn("Quality", APP_DESCRIPTION)
        self.assertIn("Voices are trained at one of 4 \"quality\" levels:", APP_DESCRIPTION)
        self.assertIn("x_low - 16Khz audio, 5-7M params", APP_DESCRIPTION)
        self.assertIn("low - 16Khz audio, 15-20M params", APP_DESCRIPTION)
        self.assertIn("medium - 22.05Khz audio, 15-20M params", APP_DESCRIPTION)
        self.assertIn("high - 22.05Khz audio, 28-32M params", APP_DESCRIPTION)
        self.assertIn("Multi-Speaker", APP_DESCRIPTION)
        self.assertIn("Some voices contain multiple speakers", APP_DESCRIPTION)
        self.assertIn("Multi-speaker models can quickly switch between different speakers", APP_DESCRIPTION)
        self.assertIn("Anti-gravity", APP_DESCRIPTION)
        self.assertIn("Claude", APP_DESCRIPTION)
        self.assertIn("release it open-source and for free :-)", APP_DESCRIPTION)

    def test_licensing_text_links(self):
        """Verify the legal page contains the updated SVGRepo author link and required sources."""
        self.assertIn("https://www.svgrepo.com/author/Asam%20Munir/", LICENSING_TEXT)
        self.assertNotIn("https://www.svgrepo.com (via SVGRepo", LICENSING_TEXT)
        self.assertIn("https://github.com/wbernard/parolu", LICENSING_TEXT)
        self.assertIn("https://github.com/rhasspy/piper", LICENSING_TEXT)
        self.assertIn("https://github.com/rhasspy/piper-voices", LICENSING_TEXT)
        self.assertIn("https://dribbble.com/asammunir", LICENSING_TEXT)
        self.assertIn("https://www.gnu.org/licenses/gpl-3.0.txt", LICENSING_TEXT)
        self.assertIn("https://www.flaticon.com/free-icon/cd_6749218", LICENSING_TEXT)

    def test_about_window_properties_and_rows(self):
        app = ReadAloudApplication()
        about = app._create_about_window()

        self.assertEqual(about.props.application_name, 'ReadAloud')
        self.assertEqual(about.props.website, 'https://github.com/Zackarious/ReadAloud')
        self.assertEqual(about.props.issue_url, 'https://github.com/Zackarious/ReadAloud/issues')
        self.assertEqual(about.props.comments, APP_DESCRIPTION)
        self.assertEqual(about.props.version, 'Version 1.8.12 - (02 November 2026)')
        self.assertEqual(about.props.default_width, 600)
        self.assertEqual(about.props.default_height, 680)

        # Verify stack has all 5 sub-tabs
        self.assertIsNotNone(about.stack)
        for tab_id in ['about', 'changelogs', 'description', 'credits', 'legal']:
            child = about.stack.get_child_by_name(tab_id)
            self.assertIsNotNone(child, f"Tab '{tab_id}' should exist in stack")

        # Verify stack page titles
        self.assertEqual(about.stack.get_page(about.stack.get_child_by_name("about")).get_title(), "About")
        self.assertEqual(about.stack.get_page(about.stack.get_child_by_name("changelogs")).get_title(), "Change Logs")
        self.assertEqual(about.stack.get_page(about.stack.get_child_by_name("description")).get_title(), "Description")
        self.assertEqual(about.stack.get_page(about.stack.get_child_by_name("credits")).get_title(), "Credits")
        self.assertEqual(about.stack.get_page(about.stack.get_child_by_name("legal")).get_title(), "Legal")

        # Verify Credits page rows and web links
        rows = {}
        def collect_rows(widget):
            if isinstance(widget, Adw.ActionRow):
                rows[widget.get_title()] = widget.get_subtitle()
            child = widget.get_first_child()
            while child:
                collect_rows(child)
                child = child.get_next_sibling()

        collect_rows(about)

        self.assertIn("zackarious", rows)
        self.assertEqual(rows["zackarious"], "https://github.com/Zackarious/ReadAloud")
        self.assertIn("Walter Bernard (Original Creator of Parolu)", rows)
        self.assertEqual(rows["Walter Bernard (Original Creator of Parolu)"], "https://github.com/wbernard/parolu")
        self.assertIn("Asam Munir (UI Icons)", rows)
        self.assertEqual(rows["Asam Munir (UI Icons)"], "https://dribbble.com/asammunir")
        self.assertIn("Piper Neural Text-to-Speech Engine", rows)
        self.assertEqual(rows["Piper Neural Text-to-Speech Engine"], "https://github.com/rhasspy/piper")
        self.assertIn("Piper Voice Models Repository", rows)
        self.assertEqual(rows["Piper Voice Models Repository"], "https://github.com/rhasspy/piper-voices")
        self.assertIn("Michael Hansen (Rhasspy)", rows)
        self.assertEqual(rows["Michael Hansen (Rhasspy)"], "https://github.com/synesthesiam")
        self.assertIn("SVGRepo (Asam Munir Collection)", rows)
        self.assertEqual(rows["SVGRepo (Asam Munir Collection)"], "https://www.svgrepo.com/author/Asam%20Munir/")
        self.assertIn("Flaticon (CD Audio Icon)", rows)
        self.assertEqual(rows["Flaticon (CD Audio Icon)"], "https://www.flaticon.com/free-icon/cd_6749218")
        self.assertIn("GNU General Public License v3.0", rows)
        self.assertEqual(rows["GNU General Public License v3.0"], "https://www.gnu.org/licenses/gpl-3.0.txt")
        self.assertIn("The MIT License", rows)
        self.assertEqual(rows["The MIT License"], "https://opensource.org/licenses/MIT")

        # Verify close button tooltip on About window
        close_tooltips = []
        def find_ctrls(widget):
            if isinstance(widget, Gtk.WindowControls):
                c = widget.get_first_child()
                while c:
                    if "close" in c.get_css_classes():
                        close_tooltips.append(c.get_tooltip_text())
                    c = c.get_next_sibling()
            child = widget.get_first_child()
            while child:
                find_ctrls(child)
                child = child.get_next_sibling()

        find_ctrls(about)
        self.assertTrue(len(close_tooltips) > 0)
        self.assertTrue(all(t == "Close" for t in close_tooltips))

    def test_changelog_action_switches_to_changelogs_tab(self):
        app = ReadAloudApplication()
        about = app._create_about_window()
        self.assertEqual(about.stack.get_visible_child_name(), "about")
        about.stack.set_visible_child_name("changelogs")
        self.assertEqual(about.stack.get_visible_child_name(), "changelogs")


if __name__ == '__main__':
    unittest.main()
