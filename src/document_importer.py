# src/document_importer.py
"""Document importer supporting EPUB, PDF, TXT, and MD files.

Extracts text and chapters into individual tab documents for ReadAloud.
EPUB extraction uses Python's standard library (zipfile, ElementTree, html.parser).
PDF extraction uses pypdf for text and outline bookmark extraction.
"""

import os
import io
import re
import html
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


class HTMLTextExtractor(HTMLParser):
    """Robust HTML-to-text converter preserving paragraph and line structure."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._tag_stack = []

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'blockquote', 'hr', 'section', 'article'):
            self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if self._tag_stack and tag in self._tag_stack:
            while self._tag_stack and self._tag_stack[-1] != tag:
                self._tag_stack.pop()
            if self._tag_stack:
                self._tag_stack.pop()
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'blockquote', 'hr', 'section', 'article'):
            self.text_parts.append('\n')

    def handle_data(self, data):
        # Ignore non-visible content
        if self._tag_stack and self._tag_stack[-1] in ('script', 'style', 'head', 'title'):
            return
        self.text_parts.append(data)

    def get_text(self):
        raw = html.unescape(''.join(self.text_parts))
        lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in raw.split('\n')]
        text = '\n'.join(lines)
        return re.sub(r'\n{3,}', '\n\n', text).strip()


def _extract_title_from_html(html_str, fallback=""):
    """Finds <title>, <h1>, or <h2> text within HTML string."""
    for tag in ('title', 'h1', 'h2'):
        m = re.search(rf'(?is)<{tag}[^>]*>(.*?)</{tag}>', html_str)
        if m:
            clean = re.sub(r'<[^>]+>', '', m.group(1))
            clean = html.unescape(clean).strip()
            # Remove any line breaks
            clean = re.sub(r'\s+', ' ', clean)
            if clean:
                return clean
    return fallback


def extract_epub_chapters(source, filename=None):
    """Extracts chapters from an EPUB file.

    Args:
        source: bytes, io.BytesIO, or filesystem path string.
        filename: Optional filename to use as the base book name.

    Returns:
        List of tuples: [(chapter_title, chapter_text), ...]
    """
    if isinstance(source, (bytes, bytearray)):
        stream = io.BytesIO(source)
    elif isinstance(source, io.IOBase):
        stream = source
    elif isinstance(source, str) and os.path.isfile(source):
        with open(source, 'rb') as f:
            stream = io.BytesIO(f.read())
    else:
        raise ValueError("Invalid source for EPUB extraction")

    base_book_name = ""
    if filename:
        base_book_name = os.path.splitext(os.path.basename(filename))[0]

    if not zipfile.is_zipfile(stream):
        raise ValueError("The provided file is not a valid EPUB zip archive.")

    stream.seek(0)
    with zipfile.ZipFile(stream, 'r') as zf:
        namelist = zf.namelist()

        # 1. Locate rootfile from META-INF/container.xml
        container_path = "META-INF/container.xml"
        if container_path not in namelist:
            raise ValueError("Invalid EPUB: Missing META-INF/container.xml")

        container_xml = zf.read(container_path)
        container_root = ET.fromstring(container_xml)
        opf_path = None
        for elem in container_root.iter():
            if elem.tag.endswith('rootfile'):
                opf_path = elem.attrib.get('full-path')
                if opf_path:
                    break

        if not opf_path or opf_path not in namelist:
            # Fallback: search for any .opf file
            opf_candidates = [n for n in namelist if n.lower().endswith('.opf')]
            if opf_candidates:
                opf_path = opf_candidates[0]
            else:
                raise ValueError("Invalid EPUB: Could not locate OPF package file.")

        opf_dir = os.path.dirname(opf_path)
        opf_xml = zf.read(opf_path)
        opf_root = ET.fromstring(opf_xml)

        # 2. Extract book metadata title
        book_title = base_book_name
        for elem in opf_root.iter():
            if elem.tag.endswith('title') and elem.text and elem.text.strip():
                book_title = elem.text.strip()
                break
        if not book_title:
            book_title = base_book_name or "Book"

        # 3. Parse manifest
        manifest = {}  # id -> href
        nav_href = None
        ncx_href = None
        for elem in opf_root.iter():
            if elem.tag.endswith('item'):
                item_id = elem.attrib.get('id')
                item_href = elem.attrib.get('href')
                media_type = elem.attrib.get('media-type', '')
                properties = elem.attrib.get('properties', '')
                if item_id and item_href:
                    manifest[item_id] = item_href
                if 'nav' in properties.split() or (media_type == 'application/xhtml+xml' and 'nav' in item_id.lower()):
                    nav_href = item_href
                if media_type == 'application/x-dtbncx+xml' or (item_href and item_href.lower().endswith('.ncx')):
                    ncx_href = item_href

        # 4. Parse spine
        spine_item_ids = []
        for elem in opf_root.iter():
            if elem.tag.endswith('itemref'):
                idref = elem.attrib.get('idref')
                if idref and idref in manifest:
                    spine_item_ids.append(idref)

        # 5. Extract Table of Contents (NCX and/or NAV)
        toc_map = {}  # normalized relative href (without anchor) -> list of (anchor, title)

        # Try NCX first
        if ncx_href:
            full_ncx_path = os.path.normpath(os.path.join(opf_dir, ncx_href)).replace('\\', '/')
            if full_ncx_path in namelist:
                try:
                    ncx_xml = zf.read(full_ncx_path)
                    ncx_root = ET.fromstring(ncx_xml)
                    for navpoint in ncx_root.iter():
                        if navpoint.tag.endswith('navPoint'):
                            text_elem = None
                            for c in navpoint.iter():
                                if c.tag.endswith('text') and c.text:
                                    text_elem = c.text.strip()
                                    break
                            content_elem = None
                            for c in navpoint.iter():
                                if c.tag.endswith('content'):
                                    content_elem = c.attrib.get('src')
                                    break
                            if text_elem and content_elem:
                                parts = content_elem.split('#', 1)
                                href_base = parts[0]
                                anchor = parts[1] if len(parts) > 1 else ""
                                norm_href = os.path.normpath(os.path.join(os.path.dirname(ncx_href), href_base)).replace('\\', '/')
                                toc_map.setdefault(norm_href, []).append((anchor, text_elem))
                except Exception:
                    pass

        # Try NAV if toc_map is empty
        if not toc_map and nav_href:
            full_nav_path = os.path.normpath(os.path.join(opf_dir, nav_href)).replace('\\', '/')
            if full_nav_path in namelist:
                try:
                    nav_xml = zf.read(full_nav_path)
                    nav_root = ET.fromstring(nav_xml)
                    for a_elem in nav_root.iter():
                        if a_elem.tag.endswith('a') and a_elem.attrib.get('href'):
                            title = "".join(a_elem.itertext()).strip()
                            href_val = a_elem.attrib['href']
                            if title and href_val:
                                parts = href_val.split('#', 1)
                                href_base = parts[0]
                                anchor = parts[1] if len(parts) > 1 else ""
                                norm_href = os.path.normpath(os.path.join(os.path.dirname(nav_href), href_base)).replace('\\', '/')
                                toc_map.setdefault(norm_href, []).append((anchor, title))
                except Exception:
                    pass

        # 6. Read and extract chapters from spine
        chapters = []
        raw_sections = []

        for idx, item_id in enumerate(spine_item_ids, 1):
            rel_href = manifest.get(item_id)
            if not rel_href:
                continue

            full_file_path = os.path.normpath(os.path.join(opf_dir, rel_href)).replace('\\', '/')
            if full_file_path not in namelist:
                continue

            try:
                raw_bytes = zf.read(full_file_path)
            except Exception:
                continue

            try:
                html_content = raw_bytes.decode('utf-8')
            except UnicodeError:
                try:
                    html_content = raw_bytes.decode('latin-1')
                except Exception:
                    continue

            # Determine title for this spine document
            norm_rel_href = os.path.normpath(rel_href).replace('\\', '/')
            matched_titles = toc_map.get(norm_rel_href) or toc_map.get(rel_href) or []

            doc_title = ""
            if matched_titles and matched_titles[0][1]:
                doc_title = matched_titles[0][1]
            else:
                doc_title = _extract_title_from_html(html_content, fallback="")

            # Check if this document contains multiple chapter headings inside it
            heading_splits = re.split(r'(?i)(<h[12][^>]*>.*?</h[12]>)', html_content)
            if len(heading_splits) >= 5 and any(re.search(r'(?i)\b(?:chapter|part|section|book)\b', h) for h in heading_splits[1::2]):
                # Process preamble if any
                preamble_html = heading_splits[0]
                extractor = HTMLTextExtractor()
                extractor.feed(preamble_html)
                preamble_text = extractor.get_text()
                if len(preamble_text) >= 100:
                    raw_sections.append((f"{book_title} - Introduction", preamble_text))

                for h_idx in range(1, len(heading_splits), 2):
                    heading_html = heading_splits[h_idx]
                    body_html = heading_splits[h_idx + 1] if (h_idx + 1 < len(heading_splits)) else ""
                    h_title = re.sub(r'<[^>]+>', '', heading_html)
                    h_title = html.unescape(h_title).strip()
                    h_title = re.sub(r'\s+', ' ', h_title)

                    extractor = HTMLTextExtractor()
                    extractor.feed(body_html)
                    section_text = extractor.get_text()
                    if section_text:
                        raw_sections.append((h_title, section_text))
                continue

            # Single chapter document
            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            text = extractor.get_text()

            if not doc_title:
                first_line = text.split('\n')[0].strip() if text else ""
                if first_line and len(first_line) <= 60 and re.match(r'^[A-Z0-9\s:.-]+$', first_line, re.IGNORECASE):
                    doc_title = first_line
                else:
                    doc_title = f"Chapter {len(raw_sections) + 1}"

            raw_sections.append((doc_title, text))

        # Filter out trivial stub sections (e.g. covers, empty copyright pages with < 50 chars)
        has_multiple_substantive = sum(1 for _, t in raw_sections if len(t) >= 100) >= 1
        for title, text in raw_sections:
            if not text.strip():
                continue
            is_stub = len(text.strip()) < 50 and bool(re.search(r'(?i)\b(cover|title page|copyright|colophon)\b', title))
            if is_stub and has_multiple_substantive:
                continue

            clean_title = title.strip()
            if book_title and book_title.lower() not in clean_title.lower():
                final_title = f"{book_title} - {clean_title}"
            else:
                final_title = clean_title

            chapters.append((final_title, text))

        if not chapters and raw_sections:
            for title, text in raw_sections:
                if text.strip():
                    chapters.append((f"{book_title} - {title}" if book_title and book_title not in title else title, text))

    return chapters


def extract_pdf_chapters(source, filename=None):
    """Extracts chapters from a PDF file.

    Args:
        source: bytes, io.BytesIO, or filesystem path string.
        filename: Optional filename to use as the base book name.

    Returns:
        List of tuples: [(chapter_title, chapter_text), ...]
    """
    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf is required to extract PDF files. Please install pypdf.")

    if isinstance(source, (bytes, bytearray)):
        stream = io.BytesIO(source)
    elif isinstance(source, io.IOBase):
        stream = source
    elif isinstance(source, str) and os.path.isfile(source):
        with open(source, 'rb') as f:
            stream = io.BytesIO(f.read())
    else:
        raise ValueError("Invalid source for PDF extraction")

    base_book_name = ""
    if filename:
        base_book_name = os.path.splitext(os.path.basename(filename))[0]

    reader = pypdf.PdfReader(stream)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("The PDF file is encrypted and password protected.")

    total_pages = len(reader.pages)
    if total_pages == 0:
        return []

    book_title = base_book_name
    meta = reader.metadata
    if meta and hasattr(meta, 'title') and meta.title and meta.title.strip():
        book_title = meta.title.strip()
    if not book_title:
        book_title = base_book_name or "Document"

    # 1. Try outline / bookmarks
    bookmarks = []

    def traverse_outline(items):
        for item in items:
            if isinstance(item, list):
                traverse_outline(item)
            else:
                try:
                    page_num = reader.get_destination_page_number(item)
                    if page_num is not None and 0 <= page_num < total_pages:
                        bm_title = getattr(item, 'title', None)
                        if not bm_title and isinstance(item, dict):
                            bm_title = item.get('/Title')
                        if bm_title:
                            bm_title = str(bm_title).strip()
                            if bm_title:
                                bookmarks.append((page_num, bm_title))
                except Exception:
                    pass

    try:
        if reader.outline:
            traverse_outline(reader.outline)
    except Exception:
        bookmarks = []

    # If bookmarks exist, group pages into chapters
    if bookmarks:
        bookmarks.sort(key=lambda x: x[0])

        deduped = []
        seen_pages = set()
        for p, t in bookmarks:
            if p not in seen_pages:
                seen_pages.add(p)
                deduped.append((p, t))
        bookmarks = deduped

        chapters = []
        first_p = bookmarks[0][0]
        if first_p > 0:
            intro_text = "\n\n".join(
                (reader.pages[p].extract_text() or "").strip() for p in range(0, first_p)
            ).strip()
            if len(intro_text) >= 50:
                chapters.append((f"{book_title} - Introduction", intro_text))

        for i, (p_start, bm_title) in enumerate(bookmarks):
            p_end = bookmarks[i + 1][0] if (i + 1 < len(bookmarks)) else total_pages
            ch_text = "\n\n".join(
                (reader.pages[p].extract_text() or "").strip() for p in range(p_start, p_end)
            ).strip()
            if ch_text:
                full_title = f"{book_title} - {bm_title}" if book_title.lower() not in bm_title.lower() else bm_title
                chapters.append((full_title, ch_text))

        if chapters:
            return chapters

    # 2. Fallback: Scan pages for chapter heading regexes
    page_texts = [(reader.pages[p].extract_text() or "").strip() for p in range(total_pages)]

    heading_pattern = re.compile(
        r'^\s*(?:chapter|ch\.|part|section|book|act|scene)\s+(?:\d+|[ivxlcdm]+|[a-z]+)\b.*$|'
        r'^\s*(?:prologue|epilogue|preface|introduction|conclusion|afterword|foreword)\b.*$',
        re.IGNORECASE
    )

    detected_headings = []
    for p_idx, text in enumerate(page_texts):
        if not text:
            continue
        lines = [l.strip() for l in text.split('\n') if l.strip()][:3]
        for line in lines:
            if heading_pattern.match(line) and len(line) <= 80:
                detected_headings.append((p_idx, line))
                break

    if len(detected_headings) >= 2:
        chapters = []
        first_p = detected_headings[0][0]
        if first_p > 0:
            intro_text = "\n\n".join(page_texts[p] for p in range(0, first_p) if page_texts[p]).strip()
            if len(intro_text) >= 50:
                chapters.append((f"{book_title} - Introduction", intro_text))

        for i, (p_start, h_title) in enumerate(detected_headings):
            p_end = detected_headings[i + 1][0] if (i + 1 < len(detected_headings)) else total_pages
            ch_text = "\n\n".join(page_texts[p] for p in range(p_start, p_end) if page_texts[p]).strip()
            if ch_text:
                full_title = f"{book_title} - {h_title}" if book_title.lower() not in h_title.lower() else h_title
                chapters.append((full_title, ch_text))

        if chapters:
            return chapters

    # 3. Final Fallback: Return complete text as a single document
    full_text = "\n\n".join(t for t in page_texts if t).strip()
    if full_text:
        return [(book_title, full_text)]
    return []


def load_document_chapters(source, filename=None, raw_bytes=None):
    """Loads a document and extracts its chapters.

    Supports .epub, .pdf, .txt, .md.

    Args:
        source: GFile, path string, or None if raw_bytes is provided.
        filename: Optional filename.
        raw_bytes: Optional binary content bytes.

    Returns:
        List of tuples: [(chapter_title, chapter_text), ...]
    """
    if filename is None:
        if hasattr(source, 'get_basename'):
            filename = source.get_basename() or "Document"
        elif isinstance(source, str):
            filename = os.path.basename(source)
        else:
            filename = "Document"

    _, ext = os.path.splitext(filename.lower())

    # Get data bytes
    data = raw_bytes
    if data is None:
        if hasattr(source, 'load_contents'):
            success, contents, _ = source.load_contents(None)
            if success:
                data = contents
        elif isinstance(source, str) and os.path.isfile(source):
            with open(source, 'rb') as f:
                data = f.read()

    if data is None:
        raise ValueError(f"Could not load data for {filename}")

    if ext == '.epub':
        return extract_epub_chapters(data, filename=filename)
    elif ext == '.pdf':
        return extract_pdf_chapters(data, filename=filename)
    elif ext in ('.txt', '.md'):
        try:
            text = data.decode('utf-8')
        except UnicodeError:
            text = data.decode('latin-1')
        title = filename or "Document"
        return [(title, text)]
    else:
        raise ValueError(f"Unsupported file format: {ext}")
