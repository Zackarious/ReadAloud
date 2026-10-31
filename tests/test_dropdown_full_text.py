import unittest
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib, GObject, Pango

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

from src.window import ReadAloudWindow


class DummyListItem(GObject.Object):
    def __init__(self):
        super().__init__()
        self._child = None
        self._item = None

    def set_child(self, child):
        self._child = child

    def get_child(self):
        return self._child

    def set_item(self, item):
        self._item = item

    def get_item(self):
        return self._item


class TestDropdownFullText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_dropdown_list_factory_has_no_ellipsize_or_excerpt(self):
        """Verify list factory creates labels with EllipsizeMode.NONE so popup choices have no excerpt."""
        window = ReadAloudWindow()
        dropdown = window.voice_chooser
        list_factory = dropdown.get_list_factory()
        self.assertIsNotNone(list_factory, "voice_chooser must have a list_factory set")

        item = DummyListItem()
        list_factory.emit("setup", item)
        label = item.get_child()
        self.assertIsInstance(label, Gtk.Label)
        self.assertEqual(
            label.get_ellipsize(),
            Pango.EllipsizeMode.NONE,
            "Popup list item label must have EllipsizeMode.NONE so choices are not excerpted with ellipses"
        )

        full_voice_name = "Jenny_dioco Voice - Medium quality - (Optimised speed to generate)"
        str_obj = Gtk.StringObject.new(full_voice_name)
        item.set_item(str_obj)

        list_factory.emit("bind", item)

        self.assertEqual(
            label.get_text(),
            full_voice_name,
            "Popup list choice must display the full text without any excerpt or truncation"
        )
        self.assertNotIn("...", label.get_text())

    def test_dropdown_button_factory_displays_full_text(self):
        """Verify button factory sets the full text on the closed button label with no artificial max_chars excerpt."""
        window = ReadAloudWindow()
        dropdown = window.voice_chooser
        button_factory = dropdown.get_factory()
        self.assertIsNotNone(button_factory, "voice_chooser must have a button factory set")

        item = DummyListItem()
        button_factory.emit("setup", item)
        label = item.get_child()
        self.assertIsInstance(label, Gtk.Label)

        longest_voice_name = "Northern_english_male Voice - Medium quality - (Optimised speed to generate)"
        str_obj = Gtk.StringObject.new(longest_voice_name)
        item.set_item(str_obj)

        button_factory.emit("bind", item)

        self.assertEqual(
            label.get_text(),
            longest_voice_name,
            "Button label text must display the full voice name without hardcoded excerpt truncation"
        )
        self.assertNotIn("...", label.get_text())
        self.assertEqual(label.get_tooltip_text(), longest_voice_name)


if __name__ == "__main__":
    unittest.main()
