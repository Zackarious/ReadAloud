# tests/test_wikipedia_importer.py
import unittest
import os
import gi
from unittest.mock import patch, MagicMock

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from bs4 import BeautifulSoup
from src.wikipedia_importer import (
    normalize_wikipedia_topic_or_url,
    parse_table_to_markdown,
    scrape_wikipedia_article_from_html,
    fetch_wikipedia_article,
    fetch_wikipedia_articles,
    WikipediaArticle,
    fetch_wikipedia_suggestions,
    fetch_thumbnail_bytes,
    WikipediaSuggestion,
)
from src.window import ReadAloudWindow, clean_all_tags

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestWikipediaImporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()
        cls.app = Adw.Application(application_id="im.zackarious.ReadAloud.TestWiki")
        cls.app.register(None)

    def test_normalize_topic_and_url(self):
        # Plain topic string
        topic, url = normalize_wikipedia_topic_or_url("Artificial intelligence")
        self.assertEqual(topic, "Artificial_intelligence")
        self.assertEqual(url, "https://en.wikipedia.org/wiki/Artificial_intelligence")

        # Plain topic with spaces and special chars
        topic, url = normalize_wikipedia_topic_or_url("Ada Lovelace")
        self.assertEqual(topic, "Ada_Lovelace")
        self.assertEqual(url, "https://en.wikipedia.org/wiki/Ada_Lovelace")

        # Full URL
        topic, url = normalize_wikipedia_topic_or_url("https://en.wikipedia.org/wiki/Alan_Turing")
        self.assertEqual(topic, "Alan_Turing")
        self.assertEqual(url, "https://en.wikipedia.org/wiki/Alan_Turing")

        # URL with section fragment
        topic, url = normalize_wikipedia_topic_or_url("https://en.wikipedia.org/wiki/Alan_Turing#Early_life")
        self.assertEqual(topic, "Alan_Turing")
        self.assertEqual(url, "https://en.wikipedia.org/wiki/Alan_Turing")

        # URL with encoded characters
        topic, url = normalize_wikipedia_topic_or_url("https://en.wikipedia.org/wiki/C%2B%2B")
        self.assertEqual(topic, "C++")
        self.assertEqual(url, "https://en.wikipedia.org/wiki/C%2B%2B")

        # Invalid or empty
        with self.assertRaises(ValueError):
            normalize_wikipedia_topic_or_url("   ")

        with self.assertRaises(ValueError):
            normalize_wikipedia_topic_or_url("https://example.com/not-a-wiki-page")

    def test_parse_table_to_markdown(self):
        html_table = """
        <table class="wikitable">
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Cell A</td><td>Cell B</td></tr>
            <tr><td>Cell C</td><td>Cell D</td></tr>
        </table>
        """
        soup = BeautifulSoup(html_table, 'html.parser')
        table_el = soup.find('table')
        md = parse_table_to_markdown(table_el)

        self.assertIn("| Header 1 | Header 2 |", md)
        self.assertIn("| --- | --- |", md)
        self.assertIn("| Cell A | Cell B |", md)
        self.assertIn("| Cell C | Cell D |", md)

    def test_scrape_wikipedia_article_from_html(self):
        sample_html = """
        <html>
        <body>
            <h1 id="firstHeading">Ada Lovelace</h1>
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <div class="sidebar">Sidebar navigation to be removed</div>
                    <div class="hatnote">Hatnote info to be ignored</div>
                    <p>Augusta Ada King, Countess of Lovelace was an English mathematician<sup class="reference"><a href="#cite_note-1">[1]</a></sup>.<span class="mw-editsection">[edit]</span></p>
                    <p>She is known for her work on the <a href="/wiki/Analytical_Engine">Analytical Engine</a> and worked with <a href="/wiki/Charles_Babbage">Charles Babbage</a>.</p>
                    <table class="infobox">
                        <tr><th>Born</th><td>10 December 1815</td></tr>
                    </table>
                    <h2>Early life</h2>
                    <p>Lovelace was born in London to poet Lord Byron and Anne Isabella Milbanke.</p>
                    <h2>References</h2>
                    <p>This reference section should be skipped entirely.</p>
                    <h2>External links</h2>
                    <p>This external link section should also be skipped.</p>
                </div>
            </div>
        </body>
        </html>
        """
        article = scrape_wikipedia_article_from_html(sample_html, source_url="https://en.wikipedia.org/wiki/Ada_Lovelace", formatted_topic="Ada_Lovelace")

        self.assertEqual(article.title, "Ada Lovelace")
        self.assertIn("Augusta Ada King", article.text)
        self.assertIn("Analytical Engine", article.text)
        self.assertIn("Early life", article.text)

        # Removed metadata
        self.assertNotIn("[1]", article.text)
        self.assertNotIn("[edit]", article.text)
        self.assertNotIn("Sidebar navigation", article.text)
        self.assertNotIn("Hatnote info", article.text)
        self.assertNotIn("This reference section should be skipped", article.text)
        self.assertNotIn("This external link section should also be skipped", article.text)

        # Related topics discovered
        self.assertIn("Analytical_Engine", article.related_topics)
        self.assertIn("Charles_Babbage", article.related_topics)

    def test_clean_all_tags_on_wikipedia_article(self):
        sample_html = """
        <html>
        <body>
            <h1 id="firstHeading">Quantum Computing</h1>
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <p>Quantum computing uses qubits (quantum bits) to perform complex calculations.</p>
                    <p>It is based on **superposition** and [entanglement].</p>
                    <table class="wikitable">
                        <tr><th>Property</th><th>Description</th></tr>
                        <tr><td>Qubit</td><td>Basic unit of quantum information</td></tr>
                    </table>
                    <h2>Key principles</h2>
                    <p>Researchers worldwide (including universities and tech companies) are developing processors.</p>
                </div>
            </div>
        </body>
        </html>
        """
        article = scrape_wikipedia_article_from_html(sample_html)
        # Raw article has markdown headers and table
        self.assertIn("# Quantum Computing", article.text)
        self.assertIn("| Property | Description |", article.text)

        # Strip all tags as done upon importing into tab
        cleaned = clean_all_tags(article.text)

        # Confirm all tags are stripped
        self.assertNotIn("#", cleaned)
        self.assertNotIn("|", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("[entanglement]", cleaned)
        self.assertNotIn("(quantum bits)", cleaned)
        self.assertNotIn("(including universities and tech companies)", cleaned)
        self.assertIn("Quantum computing uses qubits to perform complex calculations.", cleaned)
        self.assertIn("superposition", cleaned)

    def test_window_import_wikipedia_action_registered(self):
        win = ReadAloudWindow(application=self.app)
        self.assertTrue(win.has_action("import-wikipedia"))

    def test_window_on_import_wikipedia_action_presents_dialog(self):
        win = ReadAloudWindow(application=self.app)
        dialog = win.on_import_wikipedia_action()
        self.assertIsNotNone(dialog)
        self.assertIsInstance(dialog, Adw.AlertDialog)
        self.assertEqual(dialog.get_heading(), "Import from Wikipedia")
        self.assertTrue(dialog.has_response("import"))
        self.assertTrue(dialog.has_response("cancel"))

        content_box = dialog.get_extra_child()
        self.assertIsNotNone(content_box)
        self.assertIsInstance(content_box, Gtk.Box)

        # Verify logo picture and donate link button exist within extra_child hierarchy
        children = []
        def collect_children(widget):
            child = widget.get_first_child()
            while child:
                children.append(child)
                collect_children(child)
                child = child.get_next_sibling()
        collect_children(content_box)

        has_picture = any(isinstance(c, Gtk.Picture) for c in children)
        self.assertTrue(has_picture, "Dialog should include Wikipedia logo Picture")

        donate_links = [c for c in children if isinstance(c, Gtk.LinkButton) and c.get_uri() == "https://donate.wikimedia.org/"]
        self.assertTrue(len(donate_links) > 0, "Dialog should include LinkButton to https://donate.wikimedia.org/")

    def test_populate_wikipedia_tabs_into_empty_untitled_tab(self):
        win = ReadAloudWindow(application=self.app)
        # Verify initial empty untitled tab
        self.assertEqual(win.tab_view.get_n_pages(), 1)
        cur_page = win.tab_view.get_selected_page()
        self.assertIn("Untitled", cur_page.get_title())

        articles = [
            WikipediaArticle(
                title="Ada Lovelace",
                text="Augusta Ada King, Countess of Lovelace was an English mathematician (mathematician) with **notable** contributions.",
                url="https://en.wikipedia.org/wiki/Ada_Lovelace"
            ),
            WikipediaArticle(
                title="Charles Babbage",
                text="Charles Babbage was an English polymath [mathematician] known as a pioneer of computing.",
                url="https://en.wikipedia.org/wiki/Charles_Babbage"
            ),
        ]

        win._populate_wikipedia_tabs(articles)

        # Should have updated the initial empty tab for the first article, and created a second tab for Babbage
        self.assertEqual(win.tab_view.get_n_pages(), 2)

        page1 = win.tab_view.get_nth_page(0)
        self.assertEqual(page1.get_title(), "Ada Lovelace")
        tv1 = win._get_text_view_for_page(page1)
        b1 = tv1.get_buffer()
        text1 = b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True)
        self.assertIn("Augusta Ada King", text1)
        self.assertNotIn("(mathematician)", text1)
        self.assertNotIn("**", text1)

        page2 = win.tab_view.get_nth_page(1)
        self.assertEqual(page2.get_title(), "Charles Babbage")
        tv2 = win._get_text_view_for_page(page2)
        b2 = tv2.get_buffer()
        text2 = b2.get_text(b2.get_start_iter(), b2.get_end_iter(), True)
        self.assertIn("Charles Babbage", text2)
        self.assertNotIn("[mathematician]", text2)

    def test_populate_wikipedia_tabs_with_existing_content(self):
        win = ReadAloudWindow(application=self.app)
        # Put text in the current tab
        cur_page = win.tab_view.get_selected_page()
        cur_page.set_title("My Existing Note")
        tv = win._get_text_view_for_page(cur_page)
        tv.get_buffer().set_text("Do not overwrite this important text.")

        articles = [
            WikipediaArticle(
                title="Alan Turing",
                text="Alan Turing was an English mathematician and computer scientist.",
                url="https://en.wikipedia.org/wiki/Alan_Turing"
            )
        ]

        win._populate_wikipedia_tabs(articles)

        # The existing tab must be preserved, and a new tab must be appended
        self.assertEqual(win.tab_view.get_n_pages(), 2)
        page0 = win.tab_view.get_nth_page(0)
        self.assertEqual(page0.get_title(), "My Existing Note")

        page1 = win.tab_view.get_nth_page(1)
        self.assertEqual(page1.get_title(), "Alan Turing")
        tv1 = win._get_text_view_for_page(page1)
        b1 = tv1.get_buffer()
        self.assertIn("Alan Turing", b1.get_text(b1.get_start_iter(), b1.get_end_iter(), True))

    @patch('src.wikipedia_importer.requests.get')
    def test_fetch_wikipedia_article_with_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
        <body>
            <h1 id="firstHeading">Python (programming language)</h1>
            <div id="mw-content-text">
                <div class="mw-parser-output">
                    <p>Python is a high-level programming language.</p>
                </div>
            </div>
        </body>
        </html>
        """
        mock_get.return_value = mock_resp

        article = fetch_wikipedia_article("Python (programming language)")
        self.assertEqual(article.title, "Python (programming language)")
        self.assertIn("high-level programming language", article.text)

    def test_scrape_wikipedia_with_html_parser_fallback(self):
        """Verify the standard-library HTMLParser fallback produces clean article text and related links."""
        from src.wikipedia_importer import _scrape_wikipedia_with_html_parser
        sample_html = """
        <html>
        <body>
            <h1 id="firstHeading">Grace Hopper</h1>
            <div id="mw-content-text">
                <div class="sidebar">Sidebar navigation to be removed</div>
                <p>Grace Brewster Murray Hopper was an American computer scientist.<sup class="reference"><a href="#cite_1">[1]</a></sup></p>
                <p>She was a pioneer of computer programming and worked on <a href="/wiki/COBOL">COBOL</a> and <a href="/wiki/UNIVAC_I">UNIVAC I</a>.</p>
                <h2>Career</h2>
                <p>Hopper joined the Naval Reserve during World War II.</p>
                <h2>References</h2>
                <p>Skip this citation bibliography.</p>
            </div>
        </body>
        </html>
        """
        article = _scrape_wikipedia_with_html_parser(sample_html, source_url="https://en.wikipedia.org/wiki/Grace_Hopper", formatted_topic="Grace_Hopper")
        self.assertEqual(article.title, "Grace Hopper")
        self.assertIn("Grace Brewster Murray Hopper", article.text)
        self.assertIn("Career", article.text)
        self.assertNotIn("Skip this citation", article.text)
        self.assertIn("COBOL", article.related_topics)
        self.assertIn("UNIVAC_I", article.related_topics)

    @patch('src.window.fetch_wikipedia_articles')
    def test_start_wikipedia_import_completes_and_populates_tabs(self, mock_fetch):
        mock_fetch.return_value = [
            WikipediaArticle(title="Donald Trump", text="Donald John Trump is an American politician.", url="https://en.wikipedia.org/wiki/Donald_Trump")
        ]
        win = ReadAloudWindow(application=self.app)
        populated = []
        win._populate_wikipedia_tabs = lambda arts: populated.extend(arts)

        thread = win._start_wikipedia_import("Donald_Trump", fetch_related=False, max_related=0)
        thread.join(timeout=5.0)

        # Process pending GLib idle callbacks
        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        self.assertEqual(len(populated), 1)
        self.assertEqual(populated[0].title, "Donald Trump")

    @patch('src.window.fetch_wikipedia_articles')
    def test_start_wikipedia_import_shows_error_on_failure(self, mock_fetch):
        mock_fetch.side_effect = ConnectionError("Wikipedia connection timed out.")
        win = ReadAloudWindow(application=self.app)
        errors = []
        win._show_error = lambda err: errors.append(err)

        thread = win._start_wikipedia_import("Donald_Trump", fetch_related=False, max_related=0)
        thread.join(timeout=5.0)

        ctx = GLib.MainContext.default()
        while ctx.pending():
            ctx.iteration(False)

        self.assertEqual(len(errors), 1)
        self.assertIn("Wikipedia connection timed out", errors[0])

    def test_wiki_header_button_configuration(self):
        win = ReadAloudWindow(application=self.app)
        self.assertTrue(hasattr(win, 'wiki_button'))
        self.assertIsNotNone(win.wiki_button)
        self.assertEqual(win.wiki_button.get_action_name(), "win.import-wikipedia")
        self.assertEqual(win.wiki_button.get_tooltip_text(), "Import from Wikipedia")
        child = win.wiki_button.get_child()
        self.assertIsInstance(child, Gtk.Image)

    def test_open_file_dialog_does_not_shadow_gettext(self):
        win = ReadAloudWindow(application=self.app)
        with patch.object(Gtk.FileDialog, "open") as mock_open:
            # Calling with action callback arguments (action, param) should not fail with TypeError
            win.open_file_dialog(None, None)
            self.assertTrue(mock_open.called)

    def test_save_text_dialog_does_not_fail(self):
        win = ReadAloudWindow(application=self.app)
        with patch.object(Gtk.FileDialog, "save") as mock_save:
            win.save_text_dialog(None, None)
            self.assertTrue(mock_save.called)

    def test_fetch_wikipedia_suggestions_short_or_url_returns_empty(self):
        self.assertEqual(fetch_wikipedia_suggestions(""), [])
        self.assertEqual(fetch_wikipedia_suggestions("a"), [])
        self.assertEqual(fetch_wikipedia_suggestions("https://en.wikipedia.org/wiki/England"), [])
        self.assertEqual(fetch_wikipedia_suggestions("http://en.wikipedia.org/wiki/England"), [])

    @patch('src.wikipedia_importer.urllib.request.urlopen')
    def test_fetch_wikipedia_suggestions_parses_json(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"""{
            "pages": [
                {
                    "title": "England",
                    "description": "Country within the United Kingdom",
                    "thumbnail": {
                        "url": "//thumb.wikimedia.org/flag.png",
                        "width": 60,
                        "height": 36
                    }
                },
                {
                    "title": "England cricket team",
                    "description": "Men's national cricket team",
                    "thumbnail": null
                }
            ]
        }"""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Disable requests if available during test to test urllib fallback
        with patch('src.wikipedia_importer.REQUESTS_AVAILABLE', False):
            suggs = fetch_wikipedia_suggestions("England", lang_code="en_US")
            self.assertEqual(len(suggs), 2)
            self.assertEqual(suggs[0].title, "England")
            self.assertEqual(suggs[0].description, "Country within the United Kingdom")
            self.assertEqual(suggs[0].thumbnail_url, "https://thumb.wikimedia.org/flag.png")
            self.assertEqual(suggs[1].title, "England cricket team")
            self.assertIsNone(suggs[1].thumbnail_url)

    def test_fetch_thumbnail_bytes_caching(self):
        with patch('src.wikipedia_importer.requests') as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"fake-image-bytes"
            mock_req.get.return_value = mock_resp
            with patch('src.wikipedia_importer.REQUESTS_AVAILABLE', True):
                data1 = fetch_thumbnail_bytes("https://example.com/test_thumb.png")
                self.assertEqual(data1, b"fake-image-bytes")
                # Second call should use cache and not call requests.get again
                mock_req.get.reset_mock()
                data2 = fetch_thumbnail_bytes("https://example.com/test_thumb.png")
                self.assertEqual(data2, b"fake-image-bytes")
                mock_req.get.assert_not_called()

    def test_dialog_suggestions_dropdown_interaction(self):
        win = ReadAloudWindow(application=self.app)
        dialog = win.on_import_wikipedia_action()
        self.assertTrue(hasattr(dialog, '_entry'))
        self.assertTrue(hasattr(dialog, '_sugg_revealer'))
        self.assertTrue(hasattr(dialog, '_sugg_listbox'))

        # Initially revealer is hidden
        self.assertFalse(dialog._sugg_revealer.get_reveal_child())

        # Simulate populating suggestions
        dialog._entry.set_text("England")
        sample_suggs = [
            WikipediaSuggestion("England", "Country within the United Kingdom"),
            WikipediaSuggestion("2011 England riots", "6-11 August riots")
        ]
        dialog._apply_suggestions("England", sample_suggs)

        # Revealer should be revealed with 2 rows
        self.assertTrue(dialog._sugg_revealer.get_reveal_child())
        row0 = dialog._sugg_listbox.get_row_at_index(0)
        self.assertIsNotNone(row0)
        self.assertEqual(getattr(row0, '_wiki_title', None), "England")

        # Activating row0 should set entry text and hide revealer
        row0.emit("activate")
        self.assertEqual(dialog._entry.get_text(), "England")
        self.assertFalse(dialog._sugg_revealer.get_reveal_child())


if __name__ == '__main__':
    unittest.main()


