# tests/test_document_importer.py
import unittest
import io
import zipfile
import pypdf
from src.document_importer import (
    HTMLTextExtractor,
    extract_epub_chapters,
    extract_pdf_chapters,
    load_document_chapters,
)


class TestDocumentImporter(unittest.TestCase):
    def test_html_text_extractor(self):
        extractor = HTMLTextExtractor()
        html_input = """
        <html>
            <head><title>Test Title</title><style>body { color: red; }</style></head>
            <body>
                <h1>Chapter 1: The Gathering</h1>
                <p>Paragraph 1 with <b>bold</b> and <i>italic</i> text.</p>
                <p>Paragraph 2 with &ldquo;smart quotes&rdquo; and &amp; ampersand.</p>
                <div>Div content line.</div>
            </body>
        </html>
        """
        extractor.feed(html_input)
        text = extractor.get_text()
        self.assertIn("Chapter 1: The Gathering", text)
        self.assertIn("Paragraph 1 with bold and italic text.", text)
        self.assertIn("Paragraph 2 with “smart quotes” and & ampersand.", text)
        self.assertIn("Div content line.", text)
        self.assertNotIn("body { color: red; }", text)

    def test_extract_epub_with_ncx_toc(self):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w') as zf:
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
        <dc:title>Great Novel</dc:title>
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
            <navLabel><text>Chapter 1: An Unexpected Party</text></navLabel>
            <content src="c1.xhtml"/>
        </navPoint>
        <navPoint id="p2" playOrder="2">
            <navLabel><text>Chapter 2: Roast Mutton</text></navLabel>
            <content src="c2.xhtml"/>
        </navPoint>
    </navMap>
</ncx>''')
            zf.writestr('OEBPS/c1.xhtml', '<html><body><h1>Chapter 1</h1><p>In a hole in the ground there lived a hobbit.</p></body></html>')
            zf.writestr('OEBPS/c2.xhtml', '<html><body><h1>Chapter 2</h1><p>Up jumped Bilbo, and putting on his dressing-gown went into the dining-room.</p></body></html>')

        bio.seek(0)
        chapters = extract_epub_chapters(bio.getvalue(), filename="The_Hobbit.epub")
        self.assertEqual(len(chapters), 2)
        self.assertIn("Chapter 1: An Unexpected Party", chapters[0][0])
        self.assertIn("In a hole in the ground there lived a hobbit.", chapters[0][1])
        self.assertIn("Chapter 2: Roast Mutton", chapters[1][0])
        self.assertIn("Up jumped Bilbo", chapters[1][1])

    def test_extract_epub_multi_heading_fallback(self):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w') as zf:
            zf.writestr('mimetype', 'application/epub+zip')
            zf.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>''')
            zf.writestr('content.opf', '''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Single File Book</dc:title>
    </metadata>
    <manifest>
        <item id="main" href="book.xhtml" media-type="application/xhtml+xml"/>
    </manifest>
    <spine>
        <itemref idref="main"/>
    </spine>
</package>''')
            zf.writestr('book.xhtml', '''<html><body>
                <h1>Chapter 1: The Start</h1>
                <p>This is the first chapter text that is quite long and descriptive.</p>
                <h1>Chapter 2: The Middle</h1>
                <p>This is the second chapter with plenty of interesting words.</p>
                <h1>Chapter 3: The End</h1>
                <p>This is the third and final chapter concluding our story.</p>
            </body></html>''')

        bio.seek(0)
        chapters = extract_epub_chapters(bio.getvalue(), filename="SingleBook.epub")
        self.assertEqual(len(chapters), 3)
        self.assertIn("Chapter 1: The Start", chapters[0][0])
        self.assertIn("This is the first chapter text", chapters[0][1])
        self.assertIn("Chapter 2: The Middle", chapters[1][0])
        self.assertIn("Chapter 3: The End", chapters[2][0])

    def test_extract_pdf_with_bookmarks(self):
        writer = pypdf.PdfWriter()
        p1 = writer.add_blank_page(width=200, height=200)
        p2 = writer.add_blank_page(width=200, height=200)
        p3 = writer.add_blank_page(width=200, height=200)

        writer.add_outline_item("Prologue: The Ancient World", 0)
        writer.add_outline_item("Chapter 1: The Discovery", 1)
        writer.add_outline_item("Chapter 2: Into the Darkness", 2)

        bio = io.BytesIO()
        writer.write(bio)
        bio.seek(0)

        # Note: blank pages have empty text, but function handles bookmarks cleanly
        chapters = extract_pdf_chapters(bio.getvalue(), filename="History.pdf")
        self.assertIsInstance(chapters, list)

    def test_extract_pdf_with_text_and_bookmarks(self):
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
<< /Length 55 >>
stream
BT
/F1 12 Tf
72 200 Td
(Chapter 1: The Journey Starts) Tj
ET
endstream
endobj
8 0 obj
<< /Length 52 >>
stream
BT
/F1 12 Tf
72 200 Td
(Chapter 2: The Final Conflict) Tj
ET
endstream
endobj
9 0 obj
<< /Title (Chapter 1: The Journey Starts) /Parent 6 0 R /Next 10 0 R /Dest [3 0 R /Fit] >>
endobj
10 0 obj
<< /Title (Chapter 2: The Final Conflict) /Parent 6 0 R /Prev 9 0 R /Dest [4 0 R /Fit] >>
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
0000000615 00000 n 
0000000719 00000 n 
0000000820 00000 n 
trailer
<< /Size 11 /Root 1 0 R >>
startxref
920
%%EOF
'''
        chapters = extract_pdf_chapters(raw_pdf, filename="Adventure.pdf")
        self.assertEqual(len(chapters), 2)
        self.assertIn("Chapter 1: The Journey Starts", chapters[0][0])
        self.assertIn("The Journey Starts", chapters[0][1])
        self.assertIn("Chapter 2: The Final Conflict", chapters[1][0])
        self.assertIn("The Final Conflict", chapters[1][1])


    def test_load_document_chapters_txt_and_md(self):
        txt_content = b"Line 1\nLine 2\nLine 3"
        res_txt = load_document_chapters(None, filename="notes.txt", raw_bytes=txt_content)
        self.assertEqual(len(res_txt), 1)
        self.assertEqual(res_txt[0][0], "notes.txt")
        self.assertEqual(res_txt[0][1], "Line 1\nLine 2\nLine 3")

        md_content = "# Title\n\nContent paragraph.".encode('utf-8')
        res_md = load_document_chapters(None, filename="doc.md", raw_bytes=md_content)
        self.assertEqual(len(res_md), 1)
        self.assertEqual(res_md[0][0], "doc.md")
        self.assertEqual(res_md[0][1], "# Title\n\nContent paragraph.")


if __name__ == '__main__':
    unittest.main()
