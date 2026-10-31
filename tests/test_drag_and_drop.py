import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

import subprocess

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


class TestDragAndDrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.window = ReadAloudWindow()

    def tearDown(self):
        if hasattr(self.window, 'stop_playback') and self.window.is_playing:
            self.window.stop_playback()

    def test_file_extension_validation_allowed(self):
        """Only .txt and .md files are considered valid."""
        txt_file = Gio.File.new_for_path("/tmp/test.txt")
        md_file = Gio.File.new_for_path("/tmp/notes.MD")
        mixed_file = Gio.File.new_for_path("/tmp/doc.Txt")

        for f in [txt_file, md_file, mixed_file]:
            ext = os.path.splitext(f.get_basename().lower())[1]
            self.assertIn(ext, ('.txt', '.md'))

    def test_file_extension_validation_rejected(self):
        """Non-TXT/MD files are rejected."""
        pdf_file = Gio.File.new_for_path("/tmp/test.pdf")
        png_file = Gio.File.new_for_path("/tmp/image.png")
        py_file = Gio.File.new_for_path("/tmp/script.py")

        for f in [pdf_file, png_file, py_file]:
            ext = os.path.splitext(f.get_basename().lower())[1]
            self.assertNotIn(ext, ('.txt', '.md'))

    def test_incompatible_file_alert_triggered(self):
        """Dropping an unsupported file (e.g. DOCX) triggers _alert_incompatible_files without creating extra tabs."""
        initial_pages = self.window.tab_view.get_n_pages()
        with patch.object(self.window, '_alert_incompatible_files') as mock_alert:
            docx_file = Gio.File.new_for_path("/tmp/sample.docx")
            mock_file_list = MagicMock()
            mock_file_list.get_files.return_value = [docx_file]

            ret = self.window._on_files_dropped(None, mock_file_list, 0, 0)
            self.assertTrue(ret)
            mock_alert.assert_called_once()
            self.assertEqual(self.window.tab_view.get_n_pages(), initial_pages)

    def test_drop_into_empty_untitled_tab(self):
        """Dropping into an empty untitled tab populates it with the first file and adds new tabs for others."""
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False) as f2:
            f1.write("Content of first file")
            f1.flush()
            f2.write("Content of second file")
            f2.flush()
            path1, path2 = f1.name, f2.name

        try:
            # Window starts with 1 empty untitled tab
            self.assertEqual(self.window.tab_view.get_n_pages(), 1)
            page0 = self.window.tab_view.get_nth_page(0)

            file1 = Gio.File.new_for_path(path1)
            file2 = Gio.File.new_for_path(path2)
            mock_file_list = [file1, file2]

            with patch.object(Adw.AlertDialog, 'present'):
                self.window._on_files_dropped(None, mock_file_list, 0, 0)
                if hasattr(self.window, '_last_import_dialog') and self.window._last_import_dialog:
                    self.window._last_import_dialog.emit('response', 'import')

            # Two files dropped -> 2 total tabs
            self.assertEqual(self.window.tab_view.get_n_pages(), 2)
            self.assertEqual(page0.get_title(), os.path.basename(path1))
            self.assertEqual(self.window._get_text_for_page(page0), "Content of first file")

            page1 = self.window.tab_view.get_nth_page(1)
            self.assertEqual(page1.get_title(), os.path.basename(path2))
            self.assertEqual(self.window._get_text_for_page(page1), "Content of second file")
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_drop_into_tab_with_text_prompts_user(self):
        """Dropping files into a tab that already contains text invokes _prompt_dropped_files_import_choice."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Existing notes here.")

        with patch.object(self.window, '_prompt_dropped_files_import_choice') as mock_prompt:
            file1 = Gio.File.new_for_path("/tmp/dummy.txt")
            with patch.object(file1, 'load_contents', return_value=(True, b"Dummy content", "")):
                self.window._on_files_dropped(None, [file1], 0, 0)
                mock_prompt.assert_called_once()

    def test_choice_import_into_existing_tab(self):
        """Option 'existing' appends text to the current tab buffer."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Line 1")
        file1 = Gio.File.new_for_path("/tmp/imported.txt")

        self.window._on_import_choice_response("existing", [(file1, "Line 2")])
        updated_text = self.window._get_text_for_page(page0)
        self.assertEqual(updated_text, "Line 1\n\nLine 2")

    def test_choice_new_tabs_per_file(self):
        """Option 'new_tabs' creates a new tab for each file without altering existing tab."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Original text")
        file1 = Gio.File.new_for_path("/tmp/doc1.txt")
        file2 = Gio.File.new_for_path("/tmp/doc2.md")

        self.window._on_import_choice_response("new_tabs", [(file1, "Text 1"), (file2, "Text 2")])
        self.assertEqual(self.window.tab_view.get_n_pages(), 3)
        self.assertEqual(self.window._get_text_for_page(page0), "Original text")
        self.assertEqual(self.window._get_text_for_page(self.window.tab_view.get_nth_page(1)), "Text 1")
        self.assertEqual(self.window._get_text_for_page(self.window.tab_view.get_nth_page(2)), "Text 2")

    def test_choice_all_into_one_new_tab(self):
        """Option 'all_in_one' merges files into a single new tab."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Original text")
        file1 = Gio.File.new_for_path("/tmp/doc1.txt")
        file2 = Gio.File.new_for_path("/tmp/doc2.md")

        self.window._on_import_choice_response("all_in_one", [(file1, "Part 1"), (file2, "Part 2")])
        self.assertEqual(self.window.tab_view.get_n_pages(), 2)
        new_page = self.window.tab_view.get_nth_page(1)
        self.assertEqual(self.window._get_text_for_page(new_page), "Part 1\n\nPart 2")

    def test_choice_cancel(self):
        """Option 'cancel' makes no changes."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Original text")
        file1 = Gio.File.new_for_path("/tmp/doc1.txt")

        self.window._on_import_choice_response("cancel", [(file1, "Part 1")])
        self.assertEqual(self.window.tab_view.get_n_pages(), 1)
        self.assertEqual(self.window._get_text_for_page(page0), "Original text")

    def test_placeholder_visibility_lifecycle(self):
        """Placeholder is visible on empty tab, hides when typing, reappears when cleared, updates on tab switch."""
        page0 = self.window.tab_view.get_nth_page(0)
        self.assertTrue(self.window.drop_placeholder.get_visible())

        # 2. User starts typing -> hidden
        tv = self.window.main_text_view
        buf = tv.get_buffer()
        buf.set_text("User starts typing...")
        self.assertFalse(self.window.drop_placeholder.get_visible())

        # 3. User clears text -> visible again
        buf.set_text("")
        self.assertTrue(self.window.drop_placeholder.get_visible())

        # 4. Switch between empty and populated tabs
        page_with_text = self.window.create_new_tab(title="Doc", text="Some content")
        self.assertFalse(self.window.drop_placeholder.get_visible())

        self.window.tab_view.set_selected_page(page0)
        self.window._update_drop_placeholder_visibility()
        self.assertTrue(self.window.drop_placeholder.get_visible())

        self.window.tab_view.set_selected_page(page_with_text)
        self.window._update_drop_placeholder_visibility()
        self.assertFalse(self.window.drop_placeholder.get_visible())

    def test_dialog_response_signal_triggers_action(self):
        """Emitting response on the created dialog executes _on_import_choice_response properly."""
        page0 = self.window.tab_view.get_nth_page(0)
        self.window.main_text_view.get_buffer().set_text("Initial")
        file1 = Gio.File.new_for_path("/tmp/extra.txt")

        with patch.object(Adw.AlertDialog, 'present'):
            dialog = self.window._prompt_dropped_files_import_choice([(file1, "Appended text")])
            dialog.emit('response', 'existing')
            self.assertEqual(self.window._get_text_for_page(page0), "Initial\n\nAppended text")

    def test_import_with_tag_stripping_checkboxes(self):
        """Tag stripping options extract accurately from checkboxes and apply to text."""
        box, check_map = self.window._create_tag_stripping_checkbox_box()
        self.assertIsNotNone(box)
        self.assertIn("round", check_map)
        self.assertIn("square", check_map)
        self.assertIn("pipe", check_map)
        self.assertIn("hash", check_map)
        self.assertIn("star", check_map)

        # Initially all False
        opts = self.window._get_selected_stripping_from_checkboxes(check_map)
        self.assertFalse(any(opts.values()))

        # Check round, pipe, and star
        check_map["round"].set_active(True)
        check_map["pipe"].set_active(True)
        check_map["star"].set_active(True)
        opts = self.window._get_selected_stripping_from_checkboxes(check_map)
        self.assertTrue(opts["strip_round"])
        self.assertFalse(opts["strip_square"])
        self.assertTrue(opts["strip_pipe"])
        self.assertFalse(opts["strip_hash"])
        self.assertTrue(opts["strip_stars"])

        f1 = Gio.File.new_for_path("/tmp/sample.txt")
        loaded = [(f1, "Sample (note) [citation] |meta| and **bold** #hashtag text.")]
        cleaned = self.window._apply_stripping_to_loaded_files(loaded, opts)
        self.assertEqual(cleaned[0][1], "Sample [citation] and bold #hashtag text.")

    def test_empty_tab_import_prompt_with_tag_stripping(self):
        """Dropping into empty tab with tag stripping removes selected tags."""
        f1 = Gio.File.new_for_path("/tmp/f1.txt")
        raw_text = "Headline |draft| (details) [ref]"

        page0 = self.window.tab_view.get_nth_page(0)
        with patch.object(Adw.AlertDialog, 'present'):
            dialog = self.window._prompt_empty_tab_import([(f1, raw_text)], page0)
            extra_box = dialog.get_extra_child()
            self.assertIsNotNone(extra_box)

            # Find checkboxes in extra_box
            child = extra_box.get_first_child()
            # Activate pipe and bracket removal by finding check buttons
            while child:
                if isinstance(child, Gtk.CheckButton):
                    child.set_active(True)
                child = child.get_next_sibling()

            dialog.emit('response', 'import')
            self.assertEqual(self.window._get_text_for_page(page0), "Headline")

    def test_choice_import_with_tag_stripping(self):
        """Dropping into tab with text strips chosen tags when appending or creating tabs."""
        page0 = self.window.tab_view.get_nth_page(0)
        tv = self.window.main_text_view
        tv.get_buffer().set_text("Base")

        f1 = Gio.File.new_for_path("/tmp/imported.txt")
        text_with_tags = "# Section 1 (comment) |info|"

        with patch.object(Adw.AlertDialog, 'present'):
            dialog = self.window._prompt_dropped_files_import_choice([(f1, text_with_tags)])
            extra_box = dialog.get_extra_child()
            self.assertIsNotNone(extra_box)

            # Activate pipe checkbox
            child = extra_box.get_first_child()
            while child:
                if isinstance(child, Gtk.CheckButton) and "pipe" in child.get_label().lower():
                    child.set_active(True)
                child = child.get_next_sibling()

            dialog.emit('response', 'existing')
            # Only pipe was checked, so round and hash remain
            self.assertEqual(self.window._get_text_for_page(page0), "Base\n\n# Section 1 (comment)")

    def test_import_md_file_with_table_and_tag_stripping(self):
        """Importing an MD file with a markdown table strips the table cleanly."""
        page0 = self.window.tab_view.get_nth_page(0)
        md_table_text = (
            "# Rinoa Heartilly\n\n"
            "| Rinoa Heartilly |  |\n"
            "| --- | --- |\n"
            "| Final Fantasy character |  |\n"
            "| ![image](images/250px-RinoaDissidiaNT.png)  Rinoa as drawn by Tetsuya Nomura |  |\n"
            "| First\xa0game | Final Fantasy VIII (1999) |\n"
            "| Created\xa0by | Kazushige Nojima |\n"
            "| Designed\xa0by | Tetsuya Nomura |\n"
            "| Voiced\xa0by | EN: Skyler DavenportJA: Kana Hanazawa |\n"
            "| In-universe information |  |\n"
            "| Weapon | Blaster Edge |\n"
            "| Home | Galbadia |\n"
        )
        f = Gio.File.new_for_path("/tmp/rinoa.md")
        with patch.object(Adw.AlertDialog, 'present'):
            dialog = self.window._prompt_empty_tab_import([(f, md_table_text)], page0)
            extra_box = dialog.get_extra_child()
            child = extra_box.get_first_child()
            while child:
                if isinstance(child, Gtk.CheckButton):
                    child.set_active(True)
                child = child.get_next_sibling()

            dialog.emit('response', 'import')
            self.assertEqual(self.window._get_text_for_page(page0), "Rinoa Heartilly")

    def test_select_all_button_auto_ticks_and_toggles_checkboxes(self):
        """'Select All' button ticks all checkboxes, toggles to 'Deselect All', and vice versa."""
        box, check_map = self.window._create_tag_stripping_checkbox_box()
        btn = check_map["select_all"]
        chk_round = check_map["round"]
        chk_square = check_map["square"]
        chk_pipe = check_map["pipe"]
        chk_hash = check_map["hash"]
        chk_star = check_map["star"]

        # Initially, all are unchecked and button label is "Select All"
        self.assertEqual(btn.get_label(), "Select All")
        self.assertFalse(chk_round.get_active())
        self.assertFalse(chk_square.get_active())
        self.assertFalse(chk_pipe.get_active())
        self.assertFalse(chk_hash.get_active())
        self.assertFalse(chk_star.get_active())

        # Click "Select All" -> all should be checked and label becomes "Deselect All"
        btn.emit("clicked")
        self.assertEqual(btn.get_label(), "Deselect All")
        self.assertTrue(chk_round.get_active())
        self.assertTrue(chk_square.get_active())
        self.assertTrue(chk_pipe.get_active())
        self.assertTrue(chk_hash.get_active())
        self.assertTrue(chk_star.get_active())

        # Manually uncheck one checkbox -> button should switch back to "Select All"
        chk_pipe.set_active(False)
        self.assertEqual(btn.get_label(), "Select All")

        # Click "Select All" again -> all should be checked again
        btn.emit("clicked")
        self.assertEqual(btn.get_label(), "Deselect All")
        self.assertTrue(chk_pipe.get_active())

        # Click "Deselect All" -> all should become unchecked and label reverts to "Select All"
        btn.emit("clicked")
        self.assertEqual(btn.get_label(), "Select All")
        self.assertFalse(chk_round.get_active())
        self.assertFalse(chk_square.get_active())
        self.assertFalse(chk_pipe.get_active())
        self.assertFalse(chk_hash.get_active())
        self.assertFalse(chk_star.get_active())

    def test_drop_epub_into_empty_tab_creates_chapter_tabs(self):
        """Dropping a multi-chapter EPUB file into an empty tab creates tabs for each chapter."""
        import zipfile
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_epub:
            epub_path = tmp_epub.name

        try:
            with zipfile.ZipFile(epub_path, 'w') as zf:
                zf.writestr('mimetype', 'application/epub+zip')
                zf.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>''')
                zf.writestr('OEBPS/content.opf', '''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Sample Novel</dc:title>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>
        <item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="c1"/>
        <itemref idref="c2"/>
    </spine>
</package>''')
                zf.writestr('OEBPS/toc.ncx', '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <navMap>
        <navPoint id="p1" playOrder="1">
            <navLabel><text>Chapter 1: The Beginning</text></navLabel>
            <content src="c1.xhtml"/>
        </navPoint>
        <navPoint id="p2" playOrder="2">
            <navLabel><text>Chapter 2: The Adventure</text></navLabel>
            <content src="c2.xhtml"/>
        </navPoint>
    </navMap>
</ncx>''')
                zf.writestr('OEBPS/c1.xhtml', '<html><body><h1>Chapter 1</h1><p>First chapter prose text.</p></body></html>')
                zf.writestr('OEBPS/c2.xhtml', '<html><body><h1>Chapter 2</h1><p>Second chapter prose text.</p></body></html>')

            # Ensure initial state: 1 empty tab
            while self.window.tab_view.get_n_pages() > 1:
                self.window.tab_view.close_page(self.window.tab_view.get_nth_page(1))
            self.assertEqual(self.window.tab_view.get_n_pages(), 1)
            page0 = self.window.tab_view.get_nth_page(0)
            page0.set_title("Untitled Document")

            gfile = Gio.File.new_for_path(epub_path)
            with patch.object(Adw.AlertDialog, 'present'):
                ret = self.window._on_files_dropped(None, [gfile], 0, 0)
                self.assertTrue(ret)
                if hasattr(self.window, '_last_import_dialog') and self.window._last_import_dialog:
                    self.window._last_import_dialog.emit('response', 'import')

            # Should have 2 tabs now (Chapter 1 and Chapter 2)
            self.assertEqual(self.window.tab_view.get_n_pages(), 2)
            p0 = self.window.tab_view.get_nth_page(0)
            p1 = self.window.tab_view.get_nth_page(1)
            self.assertIn("Chapter 1: The Beginning", p0.get_title())
            self.assertIn("Chapter 2: The Adventure", p1.get_title())
            tv0 = self.window._get_text_view_for_page(p0)
            tv1 = self.window._get_text_view_for_page(p1)
            self.assertIn("First chapter prose text.", tv0.get_buffer().get_text(tv0.get_buffer().get_start_iter(), tv0.get_buffer().get_end_iter(), False))
            self.assertIn("Second chapter prose text.", tv1.get_buffer().get_text(tv1.get_buffer().get_start_iter(), tv1.get_buffer().get_end_iter(), False))
        finally:
            if os.path.exists(epub_path):
                os.unlink(epub_path)

    def test_drop_pdf_into_empty_tab_creates_chapter_tabs(self):
        """Dropping a multi-chapter PDF file into an empty tab creates tabs for each chapter."""
        raw_pdf = b'''%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /Outlines 6 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 8 0 R >>
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
6 0 obj
<< /Type /Outlines /First 9 0 R /Last 10 0 R /Count 2 >>
endobj
7 0 obj
<< /Length 50 >>
stream
BT
/F1 12 Tf
72 200 Td
(PDF Chapter 1 Content) Tj
ET
endstream
endobj
8 0 obj
<< /Length 50 >>
stream
BT
/F1 12 Tf
72 200 Td
(PDF Chapter 2 Content) Tj
ET
endstream
endobj
9 0 obj
<< /Title (Chapter 1: Genesis) /Parent 6 0 R /Next 10 0 R /Dest [3 0 R /Fit] >>
endobj
10 0 obj
<< /Title (Chapter 2: Exodus) /Parent 6 0 R /Prev 9 0 R /Dest [4 0 R /Fit] >>
endobj
xref
0 11
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000133 00000 n 
0000000254 00000 n 
0000000375 00000 n 
0000000438 00000 n 
0000000508 00000 n 
0000000610 00000 n 
0000000712 00000 n 
0000000805 00000 n 
trailer
<< /Size 11 /Root 1 0 R >>
startxref
897
%%EOF
'''
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(raw_pdf)
            tmp_pdf.flush()
            pdf_path = tmp_pdf.name

        try:
            while self.window.tab_view.get_n_pages() > 1:
                self.window.tab_view.close_page(self.window.tab_view.get_nth_page(1))
            page0 = self.window.tab_view.get_nth_page(0)
            page0.set_title("Untitled Document")

            gfile = Gio.File.new_for_path(pdf_path)
            with patch.object(Adw.AlertDialog, 'present'):
                ret = self.window._on_files_dropped(None, [gfile], 0, 0)
                self.assertTrue(ret)
                if hasattr(self.window, '_last_import_dialog') and self.window._last_import_dialog:
                    self.window._last_import_dialog.emit('response', 'import')

            self.assertEqual(self.window.tab_view.get_n_pages(), 2)
            p0 = self.window.tab_view.get_nth_page(0)
            p1 = self.window.tab_view.get_nth_page(1)
            self.assertIn("Chapter 1: Genesis", p0.get_title())
            self.assertIn("Chapter 2: Exodus", p1.get_title())
            tv0 = self.window._get_text_view_for_page(p0)
            tv1 = self.window._get_text_view_for_page(p1)
            self.assertIn("PDF Chapter 1 Content", tv0.get_buffer().get_text(tv0.get_buffer().get_start_iter(), tv0.get_buffer().get_end_iter(), False))
            self.assertIn("PDF Chapter 2 Content", tv1.get_buffer().get_text(tv1.get_buffer().get_start_iter(), tv1.get_buffer().get_end_iter(), False))
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)


if __name__ == '__main__':
    unittest.main()

