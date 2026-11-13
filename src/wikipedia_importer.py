# src/wikipedia_importer.py
"""Wikipedia article scraper and parser module for ReadAloud.

Fetches Wikipedia articles by topic name or URL, strips extraneous web metadata
(references, navigation templates, edit sections), extracts content into structured text,
and discovers related internal article topics for multi-tab reading.
"""

import os
import re
import time
import random
import urllib.parse
import urllib.request
import urllib.error
import json
import html
from html.parser import HTMLParser
from typing import List, Tuple, Optional, Callable, Dict, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    BeautifulSoup = None

DEFAULT_USER_AGENT = (
    "ReadAloud/1.8.19 (https://github.com/wbernard/parolu; contact@readaloud.app)"
)

STOP_SECTIONS = {
    "see also",
    "notes",
    "references",
    "bibliography",
    "ancient sources",
    "modern sources",
    "further reading",
    "external links",
    "sources",
    "citations",
}


class WikipediaArticle:
    """Represents a scraped Wikipedia article."""

    def __init__(self, title: str, text: str, url: str, related_topics: Optional[List[str]] = None):
        self.title = title
        self.text = text
        self.url = url
        self.related_topics = related_topics or []

    def __repr__(self):
        return f"<WikipediaArticle title='{self.title}' url='{self.url}' text_len={len(self.text)}>"


def parse_table_to_markdown(table) -> str:
    """Helper function to convert an HTML table into a Markdown table."""
    rows = table.find_all('tr')
    if not rows:
        return ""

    # Calculate the maximum number of columns to prevent broken markdown tables
    max_cols = 0
    for row in rows:
        cols = len(row.find_all(['th', 'td']))
        if cols > max_cols:
            max_cols = cols

    if max_cols == 0:
        return ""

    md_table = []
    header_processed = False

    for row in rows:
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue

        cell_texts = [cell.text.strip().replace('\n', ' ') for cell in cells]

        # Pad the row with empty cells if it's shorter than max_cols
        while len(cell_texts) < max_cols:
            cell_texts.append("")

        md_row = "| " + " | ".join(cell_texts) + " |"
        md_table.append(md_row)

        if not header_processed:
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            md_table.append(separator)
            header_processed = True

    return "\n".join(md_table)


def normalize_wikipedia_topic_or_url(input_str: str) -> Tuple[str, str]:
    """Normalizes a Wikipedia topic or URL into (topic_name, full_url).

    Examples:
        'Artificial intelligence' -> ('Artificial_intelligence', 'https://en.wikipedia.org/wiki/Artificial_intelligence')
        'https://en.wikipedia.org/wiki/Albert_Einstein#Early_life' -> ('Albert_Einstein', 'https://en.wikipedia.org/wiki/Albert_Einstein')
    """
    raw = input_str.strip()
    if not raw:
        raise ValueError("Wikipedia topic or URL cannot be empty.")

    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urllib.parse.urlparse(raw)
        path = parsed.path
        if "/wiki/" in path:
            topic_part = path.split("/wiki/")[-1].split("#")[0]
            unquoted_topic = urllib.parse.unquote(topic_part).replace(" ", "_")
            scheme = parsed.scheme or "https"
            netloc = parsed.netloc or "en.wikipedia.org"
            full_url = f"{scheme}://{netloc}/wiki/{urllib.parse.quote(unquoted_topic)}"
            return unquoted_topic, full_url
        else:
            raise ValueError(f"URL does not appear to be a Wikipedia article URL: {raw}")

    # Standard topic name
    clean_topic = raw.replace(" ", "_")
    full_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(clean_topic)}"
    return clean_topic, full_url


class _WikipediaHTMLParser(HTMLParser):
    def __init__(self, formatted_topic: str = ""):
        super().__init__()
        self.formatted_topic = formatted_topic
        self.title = ""
        self.text_chunks = []
        self.related_topics = []
        self._tag_stack = []
        self._skip_depth = 0
        self._in_h1 = False
        self._current_heading = []
        self._in_heading = False
        self._heading_level = 0
        self._stopped = False
        self._current_p = []
        self._in_p = False

    def handle_starttag(self, tag, attrs):
        if self._stopped:
            return
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '').split()

        # Skip unwanted metadata, references, navbars, and sidebars
        if tag in ('script', 'style', 'head') or any(
            c in classes for c in ['reference', 'mw-editsection', 'magnify', 'sidebar', 'hatnote', 'navbox', 'ambox', 'noprint', 'mw-empty-elt']
        ):
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            self._skip_depth += 1
            return

        self._tag_stack.append((tag, classes))

        if tag == 'h1' and attrs_dict.get('id') == 'firstHeading':
            self._in_h1 = True
        elif tag in ('h2', 'h3', 'h4'):
            self._in_heading = True
            self._heading_level = int(tag[1])
            self._current_heading = []
        elif tag == 'p':
            self._in_p = True
            self._current_p = []
        elif tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            if '/wiki/' in href:
                raw_topic = href.split('/wiki/')[-1].split('#')[0]
                if raw_topic and ':' not in raw_topic:
                    clean_topic = urllib.parse.unquote(raw_topic).replace(' ', '_')
                    if (
                        clean_topic != self.formatted_topic
                        and clean_topic not in self.related_topics
                        and not clean_topic.startswith('Main_Page')
                    ):
                        self.related_topics.append(clean_topic)

    def handle_endtag(self, tag):
        if self._stopped:
            return
        if self._skip_depth > 0:
            self._skip_depth -= 1
            return

        if self._tag_stack and self._tag_stack[-1][0] == tag:
            self._tag_stack.pop()

        if tag == 'h1' and self._in_h1:
            self._in_h1 = False
        elif tag in ('h2', 'h3', 'h4') and self._in_heading:
            self._in_heading = False
            h_text = html.unescape(''.join(self._current_heading)).strip()
            if tag == 'h2' and h_text.lower() in STOP_SECTIONS:
                self._stopped = True
                return
            if h_text and h_text not in ["Contents", "Navigation menu"]:
                prefix = "#" * self._heading_level
                self.text_chunks.append(f"\n\n{prefix} {h_text}\n\n")
        elif tag == 'p' and self._in_p:
            self._in_p = False
            p_text = html.unescape(''.join(self._current_p)).strip()
            if len(p_text) > 10:
                self.text_chunks.append(f"{p_text}\n\n")

    def handle_data(self, data):
        if self._stopped or self._skip_depth > 0:
            return
        if self._in_h1:
            self.title += data
        elif self._in_heading:
            self._current_heading.append(data)
        elif self._in_p:
            self._current_p.append(data)
        elif self._tag_stack and self._tag_stack[-1][0] in ('td', 'th', 'li', 'figcaption'):
            self.text_chunks.append(data)


def _scrape_wikipedia_with_html_parser(html_content: str, source_url: str = "", formatted_topic: str = "") -> WikipediaArticle:
    parser = _WikipediaHTMLParser(formatted_topic=formatted_topic)
    parser.feed(html_content)
    title = parser.title.strip() if parser.title.strip() else formatted_topic.replace('_', ' ')
    body = "".join(parser.text_chunks).strip()
    full_text = f"# {title}\n\n{body}" if body else f"# {title}"
    return WikipediaArticle(
        title=title,
        text=full_text,
        url=source_url,
        related_topics=parser.related_topics
    )


def scrape_wikipedia_article_from_html(html_content: str, source_url: str = "", formatted_topic: str = "") -> WikipediaArticle:
    """Parses Wikipedia HTML content and extracts the clean article text and related topics."""
    if not BS4_AVAILABLE:
        return _scrape_wikipedia_with_html_parser(html_content, source_url, formatted_topic)

    soup = BeautifulSoup(html_content, 'html.parser')

    # Decompose reference superscripts, edit sections, magnify links, and invisible elements
    for sup in soup.find_all('sup', class_='reference'):
        sup.decompose()

    for edit_span in soup.find_all('span', class_='mw-editsection'):
        edit_span.decompose()

    for mag in soup.find_all('div', class_='magnify'):
        mag.decompose()

    for style in soup.find_all(['style', 'script']):
        style.decompose()

    # Extract Title
    title_el = soup.find('h1', id='firstHeading')
    if title_el:
        title_text = title_el.text.strip()
    else:
        title_text = formatted_topic.replace("_", " ") if formatted_topic else "Wikipedia Article"

    # Locate main content container
    content_area = soup.select_one('#mw-content-text .mw-parser-output')
    if not content_area:
        content_area = soup.find('div', id='mw-content-text') or soup

    elements = content_area.find_all(['h2', 'h3', 'h4', 'p', 'table', 'ul', 'ol', 'figure', 'div'])

    related_topics = []
    text_chunks = [f"# {title_text}\n\n"]

    for el in elements:
        # Skip UI chrome, sidebars, hatnotes, navigation boxes, and maintenance boxes
        if el.find_parent(class_=['sidebar', 'hatnote', 'navbox', 'ambox', 'noprint', 'mw-empty-elt']):
            continue

        # Extract internal related topics from paragraphs and tables
        if el.name in ['p', 'table']:
            for a_tag in el.find_all('a', href=True):
                href = a_tag['href']
                if '/wiki/' in href:
                    raw_topic = href.split('/wiki/')[-1].split('#')[0]
                    if raw_topic and ':' not in raw_topic:
                        clean_topic = urllib.parse.unquote(raw_topic).replace(" ", "_")
                        if (
                            clean_topic != formatted_topic
                            and clean_topic not in related_topics
                            and not clean_topic.startswith("Main_Page")
                        ):
                            related_topics.append(clean_topic)

        if el.name == 'h2':
            header_text = el.text.strip()
            # Stop when hitting bibliography/references/external links
            if header_text.lower() in STOP_SECTIONS:
                break
            if header_text and header_text not in ["Contents", "Navigation menu"]:
                text_chunks.append(f"## {header_text}\n\n")

        elif el.name in ['h3', 'h4']:
            header_text = el.text.strip()
            if header_text:
                prefix = "###" if el.name == 'h3' else "####"
                text_chunks.append(f"{prefix} {header_text}\n\n")

        elif el.name == 'p':
            p_text = el.text.strip()
            if len(p_text) > 10:
                text_chunks.append(f"{p_text}\n\n")

        elif el.name == 'table':
            classes = el.get('class', [])
            if 'wikitable' in classes or 'infobox' in classes:
                markdown_table = parse_table_to_markdown(el)
                if markdown_table:
                    text_chunks.append(f"{markdown_table}\n\n")

        elif el.name in ['ul', 'ol']:
            # Capture bullet list items if they contain text
            items = []
            for li in el.find_all('li', recursive=False):
                li_text = li.text.strip()
                if li_text:
                    items.append(f"* {li_text}")
            if items:
                text_chunks.append("\n".join(items) + "\n\n")

        elif el.name in ['figure', 'div']:
            if el.name == 'div' and 'thumb' not in el.get('class', []):
                continue

            is_nested = False
            for parent in el.parents:
                if parent == content_area:
                    break
                if parent.name == 'figure' or (parent.name == 'div' and 'thumb' in parent.get('class', [])):
                    is_nested = True
                    break

            if is_nested:
                continue

            caption_el = el.find(['figcaption', 'div'], class_=['thumbcaption', 'caption'])
            caption_text = caption_el.text.strip() if caption_el else el.text.strip()
            if caption_text:
                text_chunks.append(f"{caption_text}\n\n")

    full_article_text = "".join(text_chunks).strip()
    return WikipediaArticle(
        title=title_text,
        text=full_article_text,
        url=source_url,
        related_topics=related_topics
    )


def fetch_wikipedia_article(
    topic_or_url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 15
) -> WikipediaArticle:
    """Fetches a single Wikipedia page over HTTP and parses its content."""
    formatted_topic, full_url = normalize_wikipedia_topic_or_url(topic_or_url)
    headers = {'User-Agent': user_agent}
    html_text = None
    last_err = None

    if REQUESTS_AVAILABLE and requests is not None:
        try:
            response = requests.get(full_url, headers=headers, timeout=timeout)
            if response.status_code == 404:
                clean_display = formatted_topic.replace("_", " ")
                raise FileNotFoundError(f"Could not find a Wikipedia page for '{clean_display}'.")
            response.raise_for_status()
            html_text = response.text
        except FileNotFoundError:
            raise
        except Exception as e:
            last_err = e

    if html_text is None:
        try:
            req = urllib.request.Request(full_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                charset = resp.headers.get_content_charset() or 'utf-8'
                html_text = raw_bytes.decode(charset, errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                clean_display = formatted_topic.replace("_", " ")
                raise FileNotFoundError(f"Could not find a Wikipedia page for '{clean_display}'.") from e
            raise ConnectionError(f"Wikipedia returned HTTP error: {e}") from e
        except Exception as e:
            if last_err:
                raise ConnectionError(f"Network error while connecting to Wikipedia: {last_err}") from last_err
            raise ConnectionError(f"Network error while connecting to Wikipedia: {e}") from e

    return scrape_wikipedia_article_from_html(
        html_text,
        source_url=full_url,
        formatted_topic=formatted_topic
    )


def fetch_wikipedia_articles(
    topic_or_url: str,
    fetch_related: bool = False,
    max_related: int = 3,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None
) -> List[WikipediaArticle]:
    """Fetches a Wikipedia article and optionally its related articles.

    Args:
        topic_or_url: Main article topic name or URL.
        fetch_related: Whether to automatically fetch internal related articles.
        max_related: Maximum number of related articles to fetch (default: 3).
        progress_callback: Optional callable `(status_msg, current_index, total_count)`.
        is_cancelled: Optional callable returning True if the operation was cancelled.

    Returns:
        List of WikipediaArticle objects.
    """
    if is_cancelled and is_cancelled():
        return []

    if progress_callback:
        progress_callback(f"Fetching '{topic_or_url}'…", 1, 1)

    main_article = fetch_wikipedia_article(topic_or_url)
    articles = [main_article]

    if not fetch_related or not main_article.related_topics or max_related <= 0:
        return articles

    target_related = main_article.related_topics[:max_related]
    total_articles = 1 + len(target_related)

    for idx, rel_topic in enumerate(target_related, start=2):
        if is_cancelled and is_cancelled():
            break

        # Polite delay to avoid rate limiting
        sleep_sec = random.uniform(0.6, 1.2)
        time.sleep(sleep_sec)

        if is_cancelled and is_cancelled():
            break

        if progress_callback:
            clean_rel = rel_topic.replace("_", " ")
            progress_callback(f"Fetching related article ({idx}/{total_articles}): '{clean_rel}'…", idx, total_articles)

        try:
            rel_art = fetch_wikipedia_article(rel_topic)
            articles.append(rel_art)
        except Exception as e:
            # Continue fetching remaining related articles if one fails
            print(f"Notice: Failed to fetch related Wikipedia article '{rel_topic}': {e}")

    return articles


class WikipediaSuggestion:
    """Represents a search suggestion returned by the Wikipedia Search API."""

    def __init__(self, title: str, description: str = "", thumbnail_url: Optional[str] = None):
        self.title = title
        self.description = description
        self.thumbnail_url = thumbnail_url

    def __repr__(self):
        return f"<WikipediaSuggestion title={self.title!r} desc={self.description!r}>"


_THUMBNAIL_CACHE: Dict[str, bytes] = {}
_MAX_CACHE_SIZE = 100


def fetch_thumbnail_bytes(url: str, timeout: float = 3.0) -> Optional[bytes]:
    """Fetches thumbnail image bytes with in-memory caching."""
    if not url:
        return None
    if url in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[url]

    clean_url = "https:" + url if url.startswith("//") else url
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    data = None
    if REQUESTS_AVAILABLE and requests is not None:
        try:
            resp = requests.get(clean_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.content
        except Exception:
            pass

    if data is None:
        try:
            req = urllib.request.Request(clean_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
        except Exception:
            pass

    if data:
        if len(_THUMBNAIL_CACHE) >= _MAX_CACHE_SIZE:
            _THUMBNAIL_CACHE.pop(next(iter(_THUMBNAIL_CACHE)))
        _THUMBNAIL_CACHE[url] = data

    return data


def fetch_wikipedia_suggestions(
    query: str,
    lang_code: str = "en",
    limit: int = 5,
    timeout: float = 4.0
) -> List[WikipediaSuggestion]:
    """Fetches title search suggestions from the Wikipedia REST API."""
    clean_q = query.strip()
    if not clean_q or len(clean_q) < 2:
        return []
    if clean_q.startswith("http://") or clean_q.startswith("https://"):
        return []

    # Clean language code
    lang = lang_code.split("_")[0].split("-")[0].lower() if lang_code else "en"
    if not lang or len(lang) > 5:
        lang = "en"

    encoded_q = urllib.parse.quote(clean_q)
    url = f"https://{lang}.wikipedia.org/w/rest.php/v1/search/title?q={encoded_q}&limit={limit}"

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json",
    }

    raw_data = None
    if REQUESTS_AVAILABLE and requests is not None:
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                raw_data = resp.json()
        except Exception:
            pass

    if raw_data is None:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

    if not raw_data or not isinstance(raw_data, dict):
        return []

    suggestions = []
    for page in raw_data.get("pages", []):
        if not isinstance(page, dict):
            continue
        title = page.get("title", "").strip()
        if not title:
            continue
        description = page.get("description", "").strip()
        thumb = page.get("thumbnail")
        thumb_url = None
        if isinstance(thumb, dict) and thumb.get("url"):
            raw_thumb_url = thumb.get("url", "")
            if raw_thumb_url.startswith("//"):
                thumb_url = "https:" + raw_thumb_url
            elif raw_thumb_url.startswith("http://") or raw_thumb_url.startswith("https://"):
                thumb_url = raw_thumb_url
        suggestions.append(WikipediaSuggestion(title=title, description=description, thumbnail_url=thumb_url))

    return suggestions


class WikipediaTrendingTopic:
    """Represents a trending topic from Wikipedia's Top 25 Report."""

    def __init__(
        self,
        rank: int,
        title: str,
        url: str = "",
        views: str = "",
        image_url: Optional[str] = None,
        notes: str = ""
    ):
        self.rank = rank
        self.title = title
        self.url = url
        self.views = views
        self.image_url = image_url
        self.notes = notes

    def __repr__(self):
        return f"<WikipediaTrendingTopic rank={self.rank} title={self.title!r} views={self.views!r}>"


WIKIPEDIA_TOP_25_URL = "https://en.wikipedia.org/wiki/Wikipedia:Top_25_Report"
_TOP_25_CACHE: Dict[str, Any] = {}


def scrape_wikipedia_top_25_report(html_content: str) -> Tuple[str, List[WikipediaTrendingTopic]]:
    """Scrapes Wikipedia:Top_25_Report HTML and extracts report title and top 25 topics."""
    report_title = "Wikipedia Top 25 Trending Topics"
    items: List[WikipediaTrendingTopic] = []

    if BS4_AVAILABLE and BeautifulSoup is not None:
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", class_="wikitable")
        if table:
            prev_h = table.find_previous(["h2", "h1"])
            if prev_h and prev_h.text.strip():
                clean_h = prev_h.text.strip()
                clean_h = re.sub(r'\[edit[^\]]*\]', '', clean_h).strip()
                if clean_h:
                    report_title = clean_h

            rows = table.find_all("tr")
            for r in rows:
                cells = r.find_all(["td", "th"])
                if len(cells) < 6:
                    continue
                rank_str = cells[0].text.strip()
                if not rank_str.isdigit():
                    continue
                rank = int(rank_str)

                # Column 1: Article title & URL
                art_cell = cells[1]
                title = art_cell.text.strip()
                art_a = art_cell.find("a")
                article_url = ""
                if art_a and art_a.get("href"):
                    href = art_a["href"]
                    if href.startswith("/wiki/"):
                        article_url = "https://en.wikipedia.org" + href
                    elif href.startswith("http://") or href.startswith("https://"):
                        article_url = href

                # Column 3: Views count
                views = cells[3].text.strip()

                # Column 4: Image thumbnail
                img_cell = cells[4]
                img_tag = img_cell.find("img")
                img_url = None
                if img_tag and img_tag.get("src"):
                    raw_src = img_tag["src"]
                    if raw_src.startswith("//"):
                        img_url = "https:" + raw_src
                    elif raw_src.startswith("http://") or raw_src.startswith("https://"):
                        img_url = raw_src

                # Column 5: Notes/about commentary
                notes_cell = cells[5]
                notes = notes_cell.text.strip().replace("\n", " ")
                notes = re.sub(r"\s+", " ", notes).strip()

                items.append(WikipediaTrendingTopic(
                    rank=rank,
                    title=title,
                    url=article_url,
                    views=views,
                    image_url=img_url,
                    notes=notes
                ))
    else:
        class _Top25FallbackParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_wikitable = False
                self.table_depth = 0
                self.in_row = False
                self.cells = []
                self.current_cell = []
                self.current_a = None
                self.current_img = None
                self.rows_data = []

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                classes = attrs_dict.get('class', '').split()
                if tag == 'table' and 'wikitable' in classes:
                    self.in_wikitable = True
                    self.table_depth = 1
                    return
                if self.in_wikitable:
                    if tag == 'table':
                        self.table_depth += 1
                    elif tag == 'tr':
                        self.in_row = True
                        self.cells = []
                    elif tag in ('td', 'th') and self.in_row:
                        self.current_cell = []
                        self.current_a = None
                        self.current_img = None
                    elif tag == 'a' and 'href' in attrs_dict and not self.current_a:
                        self.current_a = attrs_dict['href']
                    elif tag == 'img' and 'src' in attrs_dict and not self.current_img:
                        self.current_img = attrs_dict['src']

            def handle_endtag(self, tag):
                if self.in_wikitable:
                    if tag == 'table':
                        self.table_depth -= 1
                        if self.table_depth == 0:
                            self.in_wikitable = False
                    elif tag == 'tr' and self.in_row:
                        self.in_row = False
                        if len(self.cells) >= 6:
                            self.rows_data.append(self.cells)
                    elif tag in ('td', 'th') and self.in_row:
                        text = ''.join(self.current_cell).strip()
                        self.cells.append({'text': text, 'a': self.current_a, 'img': self.current_img})

            def handle_data(self, data):
                if self.in_wikitable and self.in_row:
                    self.current_cell.append(data)

        parser = _Top25FallbackParser()
        parser.feed(html_content)
        for r in parser.rows_data:
            if not r[0]['text'].isdigit():
                continue
            rank = int(r[0]['text'])
            title = r[1]['text']
            href = r[1]['a'] or ""
            if href.startswith("/wiki/"):
                href = "https://en.wikipedia.org" + href
            views = r[3]['text']
            img_src = r[4]['img']
            if img_src and img_src.startswith("//"):
                img_src = "https:" + img_src
            notes = re.sub(r"\s+", " ", r[5]['text']).strip()
            items.append(WikipediaTrendingTopic(
                rank=rank,
                title=title,
                url=href,
                views=views,
                image_url=img_src,
                notes=notes
            ))

    return report_title, items


def fetch_wikipedia_top_25(
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 15,
    force_refresh: bool = False
) -> Tuple[str, List[WikipediaTrendingTopic]]:
    """Fetches and parses the Wikipedia:Top_25_Report page."""
    global _TOP_25_CACHE
    now = time.time()
    if not force_refresh and "data" in _TOP_25_CACHE and (now - _TOP_25_CACHE.get("timestamp", 0) < 3600):
        return _TOP_25_CACHE["title"], _TOP_25_CACHE["data"]

    headers = {"User-Agent": user_agent}
    html_text = None
    last_err = None

    if REQUESTS_AVAILABLE and requests is not None:
        try:
            resp = requests.get(WIKIPEDIA_TOP_25_URL, headers=headers, timeout=timeout)
            resp.raise_for_status()
            html_text = resp.text
        except Exception as e:
            last_err = e

    if html_text is None:
        try:
            req = urllib.request.Request(WIKIPEDIA_TOP_25_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                html_text = resp.read().decode(charset, errors="replace")
        except Exception as e:
            if last_err:
                raise ConnectionError(f"Failed to fetch Wikipedia Top 25 Report: {last_err}") from last_err
            raise ConnectionError(f"Failed to fetch Wikipedia Top 25 Report: {e}") from e

    title, items = scrape_wikipedia_top_25_report(html_text)
    if items:
        _TOP_25_CACHE["timestamp"] = now
        _TOP_25_CACHE["title"] = title
        _TOP_25_CACHE["data"] = items
    return title, items

