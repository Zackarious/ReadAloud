# main.py
#
# Copyright 2025 Walter Bernard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import re
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, GObject, Gdk, GLib

import gettext
_ = gettext.gettext

from .paths import get_resource_bundle_path

def ensure_resources_loaded():
    """Ensure readaloud.gresource is loaded and registered with Gio."""
    bundle_path = get_resource_bundle_path()
    if bundle_path and bundle_path.is_file():
        try:
            res = Gio.Resource.load(str(bundle_path))
            res._register()
        except Exception:
            # Already registered or invalid
            pass

ensure_resources_loaded()

from .window import ReadAloudWindow
from .bubble import ListenerBubbleWindow

CHANGELOG_XML = r"""
<p><em>Version 1.8.13 - (04 November 2026)</em></p>
<p>Version 1.8.13 resolves a critical audio playback resumption issue where switching tabs or opening a new tab with the plus button paused audio but returning to the tab restarted playback from the beginning of the buffer; adds per-tab playback and paused state tracking, anchors pause marks and cursor positions at the paused word in the text buffer, preserves visual word highlighting across tab switches, synchronizes dynamic playback controls per tab, supports seamless resumption from both Resume and Read buttons as well as keyboard shortcuts, and expands the automated regression test suite to 270 tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Abrupt Tab Playback Reset on Tab Switch:</em> Removed the unconditional stop_playback() invocation in _on_selected_page_changed() when switching active tabs. <em>Reason:</em> Abruptly stopping playback cleared the audio player pipeline, destroyed the pause anchor mark, and reset reading position to offset 0, preventing users from resuming audio where they left off when returning to the tab.</li>
  <li><em>Default Cursor Fallback to Offset 0 in read_text():</em> Removed the unconditioned fallback that placed the cursor iterator at character offset 0 when no text was selected and pause_resume_mark was present. <em>Reason:</em> Ignored existing anchored paused positions, forcing playback synthesis to restart from the beginning of the buffer even when a tab had been cleanly paused.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Per-Tab Playback State Management (_active_tab_page, _is_playing, _is_paused, _paused_offset, _highlight_index):</em> Added per-page playback metadata and active tab reference tracking in window.py. <em>Reason:</em> Enables each document tab to maintain its own independent audio playback, paused state, exact character offset, and active word highlight index across tab switches and new tab creations.</li>
  <li><em>Non-Destructive Tab Audio Pausing on Switch (_on_selected_page_changed):</em> Added automatic pausing (reader.pause_audio()) and state persistence when switching away from an active tab (such as clicking the + button to create a new tab or selecting a different tab). <em>Reason:</em> Pauses the audio stream without destroying the underlying pipeline or clearing the visual word highlight, allowing instant and sample-accurate resumption upon returning.</li>
  <li><em>Text-Anchored Pause Mark &amp; Cursor Placement on Inactive Tab:</em> Added automated creation and positioning of pause_resume_mark (Gtk.TextMark) along with place_cursor() at the exact paused character offset in the outgoing tab's text buffer. <em>Reason:</em> Anchors the paused reading location to the text buffer even across tab switches and ensures the cursor stays synchronized with the paused word.</li>
  <li><em>Automated Tab Playback Regression Tests (test_tab_switch_pauses_playback, test_new_tab_pauses_playback_and_resume_on_return, test_new_tab_pauses_playback_and_resume_with_new_voice_settings):</em> Added regression tests in tests/test_tab_system.py and tests/test_cached_playback.py covering tab creation during playback, paused state and highlight retention, and resumption on return. <em>Reason:</em> Prevents regressions where switching tabs or creating new documents could reset playback or discard paused positions.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Play &amp; Resume Interaction in read_text():</em> Updated read_text() to detect if the current tab is in a paused state (self.is_playing and self.is_paused) and seamlessly call toggle_pause() to resume audio, and updated cursor iteration to honor pause_resume_mark if present. <em>Reason:</em> Guarantees that clicking the Play button ("Read Text"), clicking Resume, or pressing Ctrl+P resumes playback directly from where the user left off without restarting from the beginning.</li>
  <li><em>Highlight Timer Synchronization on Tab Resume (toggle_pause):</em> Updated toggle_pause() to restart the word highlight polling timer (_highlight_timeout_id) if inactive and sync cur_page._is_paused = False when resuming audio. <em>Reason:</em> Ensures visual word highlighting resumes scrolling and tracking the spoken audio seamlessly when playback is resumed after returning to a paused tab.</li>
  <li><em>Tab Close Resource Deallocation (_on_close_page):</em> Updated finish_close() to invoke reader.stop_audio() and clear _active_tab_page when closing a tab with an active or paused reader. <em>Reason:</em> Prevents orphaned background GStreamer pipelines or temporary audio files from lingering after a tab is closed.</li>
  <li><em>Wikimedia-Compliant User-Agent Header:</em> Updated user-agent identification string to ReadAloud/1.8.13 (https://github.com/wbernard/parolu; contact@readaloud.app) in wikipedia_importer.py. <em>Reason:</em> Maintains strict compliance with Wikimedia Foundation User-Agent policies for the new version release.</li>
  <li><em>Application Version Increment (1.8.13):</em> Updated application version to 1.8.13 across meson.build, src/main.py, src/error_logger.py, src/wikipedia_importer.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, build_windows/build_arm64_portable.py, build_linux/build_deb.sh, build_linux/build_appimage.sh, build_linux/debian/control, build_macos/build_macos.sh, tests/test_about_window.py, and CI workflows. <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Word Highlight Retention on Outgoing Tab:</em> Preserved the active word highlight (current_word_highlight tag and HighlightTextView._highlight_range) on the tab being switched away from, instead of clearing it. <em>Reason:</em> Gives the user immediate visual confirmation of where they left off reading when returning to the document tab.</li>
  <li><em>Dynamic Playback Control Synchronization per Tab:</em> Updated _on_selected_page_changed() to synchronize toolbar button icons and tooltips dynamically when switching between tabs (showing Resume icon and enabling the pause button when selecting a paused tab, and showing idle Play button with disabled pause button when selecting an unplayed tab). <em>Reason:</em> Provides clear visual affordances so users immediately recognize whether the active tab has paused playback ready to resume or is ready for fresh reading.</li>
</ul>

<p><em>Version 1.8.12 - (02 November 2026)</em></p>
<p>Version 1.8.12 streamlines the window header bar controls by removing the redundant burger-like unwrap button following the Save to Text File icon, preserves document unwrapping via standard shortcuts and the primary application menu, introduces automated header bar layout test verification, recompiles application resources, and updates the version across all platforms and package builders.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Redundant Left-Side Header Bar Burger / Unwrap Button:</em> Removed the unwrap_button (format-justify-fill-symbolic) widget located immediately after the Save to Text File icon in window.ui along with its @Gtk.Template.Child binding in window.py. <em>Reason:</em> The four-line justification symbol visually resembled a duplicate burger menu on the left side of the header bar directly adjacent to document action buttons, causing visual clutter and user confusion with the main application burger menu on the right. Text unwrapping and paragraph reflow remain fully accessible through the primary menu ("Unwrap / Reflow Text") and via keyboard shortcuts (Ctrl+Shift+W, Ctrl+J).</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Header Bar Button Configuration Test (test_headerbar_buttons):</em> Added a dedicated regression test in tests/test_word_wrap.py verifying that the header bar's start child container strictly contains Open File (open_button), Wikipedia Import (wiki_button), and Save Text (save_text_button), and asserting that the redundant unwrap button is not present on the header bar. <em>Reason:</em> Guarantees that future updates maintain a clean, uncluttered header bar layout and prevents accidental reintroduction of redundant toolbar buttons.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Wikimedia-Compliant User-Agent Header:</em> Updated user-agent identification string to ReadAloud/1.8.12 (https://github.com/wbernard/parolu; contact@readaloud.app) in wikipedia_importer.py. <em>Reason:</em> Maintains strict compliance with Wikimedia Foundation User-Agent policies for the new version release.</li>
  <li><em>Compiled GResource Bundle:</em> Recompiled src/readaloud.gresource with glib-compile-resources from src/readaloud.gresource.xml. <em>Reason:</em> Packages the updated window.ui header bar definition into the application's runtime binary resource bundle.</li>
  <li><em>Application Version Increment (1.8.12):</em> Updated application version to 1.8.12 across meson.build, src/main.py, src/error_logger.py, src/wikipedia_importer.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, build_linux/build_deb.sh, build_linux/debian/control, tests/test_about_window.py, and CI workflows. <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Uncluttered Header Bar Navigation:</em> Streamlined the top header bar layout by eliminating the duplicate burger-style icon between the Save to Text File icon and the centered window title. <em>Reason:</em> Restores a balanced, clean user interface with standard GNOME HIG alignment, eliminating visual distraction while keeping core reading, saving, and navigation tools cleanly distinct.</li>
</ul>

<p><em>Version 1.8.11 - (01 November 2026)</em></p>
<p>Version 1.8.11 resolves critical audio playback silence and missing element errors on Windows by introducing dynamic GStreamer audio sink discovery, adds a zero-dependency native Windows fallback player (WinSoundAudioPlayer) and Unix CLI fallback player (SubprocessAudioPlayer), establishes a resilient multi-tier audio player fallback chain in Reader, fixes the unhandled AttributeError crash when pressing Return in the Wikipedia importer dialog, updates PyInstaller packaging to harvest PortAudio binaries and sounddevice data, includes GStreamer audio sink plugins in Windows CI builds, and expands the automated regression test suite to 267 tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Hardcoded GStreamer "autoaudiosink" Pipeline Construction:</em> Removed hardcoded autoaudiosink element in reader.py and audio_backend.py. <em>Reason:</em> Systems lacking gst-plugins-good (such as Windows environments without good plugins installed) fail with gst_parse_error: no element "autoaudiosink", causing playback pipeline creation to fail completely with silence.</li>
  <li><em>Bypassed Audio Backend Architecture in Reader:</em> Removed direct, unabstracted GStreamer calls in Reader._play_audio_file_async() that bypassed audio_backend.py. <em>Reason:</em> Bypassing the audio backend prevented Reader from using alternative audio players (sounddevice, winsound, CLI tools) when GStreamer was absent or broken.</li>
  <li><em>Nonexistent AlertDialog.response() Invocation:</em> Removed dialog.response("import") in window.py on the Wikipedia import entry activate handler. <em>Reason:</em> Adw.AlertDialog is a Gtk.Widget in Libadwaita and does not possess a .response() method (unlike legacy Gtk.Dialog or Adw.MessageDialog), which caused pressing Return or Keypad Enter in the search input to throw AttributeError: 'AlertDialog' object has no attribute 'response' and crash the main thread.</li>
  <li><em>Unguarded Multi-Module Pre-Initialization in Windows Entrypoint:</em> Removed the monolithic try...except block importing all C-extensions in a single block in win_entrypoint.py. <em>Reason:</em> If any single module (e.g. sounddevice due to missing _sounddevice_data) failed to import, the entire block aborted, preventing subsequent extensions (lameenc) from pre-initializing before MinGW64 GLib runtime DLLs loaded.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Dynamic GStreamer Audio Sink Detection (get_best_gst_audio_sink &amp; get_gst_audio_sink_candidates):</em> Added dynamic GStreamer audio sink discovery in audio_backend.py querying registered element factories in order of platform preference (autoaudiosink, wasapisink, directsoundsink, pulsesink, pipewiresink, alsasink, osxaudiosink). <em>Reason:</em> Automatically detects and utilizes whichever audio sink plugin is installed on the user's host platform instead of assuming autoaudiosink is always present.</li>
  <li><em>Sequential GStreamer Sink Fallback Recovery:</em> Added multi-sink trial iteration in GStreamerAudioPlayer.play(). <em>Reason:</em> If the primary sink fails during pipeline launch or state transition, the player attempts remaining available sinks sequentially before failing.</li>
  <li><em>Native Windows Standard-Library Audio Player (WinSoundAudioPlayer):</em> Added WinSoundAudioPlayer in audio_backend.py implementing BaseAudioPlayer using Python's built-in winsound module. <em>Reason:</em> Provides a zero-dependency, guaranteed audio output mechanism on Microsoft Windows that requires no external GStreamer plugins or PortAudio binaries, ensuring speech is always audible.</li>
  <li><em>CLI Subprocess Audio Player (SubprocessAudioPlayer):</em> Added SubprocessAudioPlayer in audio_backend.py using system tools (aplay, paplay, pw-play, ffplay). <em>Reason:</em> Delivers an additional playback fallback on Linux/Unix systems where GStreamer or sounddevice may not be available.</li>
  <li><em>Multi-Tier Audio Player Fallback Chain (get_audio_player_chain):</em> Added an ordered fallback player chain in audio_backend.py and integrated it into Reader._play_audio_file_async(). <em>Reason:</em> Seamlessly falls back to secondary and tertiary audio players if the primary player fails to launch, eliminating silent synthesis failures.</li>
  <li><em>PortAudio and GStreamer Dependencies in Windows CI:</em> Added mingw-w64-ucrt-x86_64-portaudio, mingw-w64-ucrt-x86_64-gstreamer, mingw-w64-ucrt-x86_64-gst-plugins-base, mingw-w64-ucrt-x86_64-gst-plugins-good, and mingw-w64-ucrt-x86_64-gst-plugins-bad to build-windows.yml. <em>Reason:</em> Ensures Windows release builds include essential audio sink plugins (autoaudiosink, directsoundsink, wasapisink) and PortAudio libraries.</li>
  <li><em>PyInstaller Hook Collection for PortAudio &amp; Sounddevice:</em> Added collect_all('sounddevice') and collect_all('_sounddevice_data'), portaudio DLL search, and plugin binary collections in ReadAloud.spec. <em>Reason:</em> Resolves ModuleNotFoundError: No module named '_sounddevice_data' in frozen Windows bundles.</li>
  <li><em>Automated Regression Test Suite Expansion (267 Tests):</em> Added tests/test_audio_playback_fallback.py and entry activation unit tests, increasing test coverage from 258 to 267 automated unit tests. <em>Reason:</em> Guarantees verification of sink discovery, fallback chains, and dialog activation.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Reader Audio Architecture Synchronization:</em> Updated Reader methods (pause_audio, resume_audio, get_playback_position, seek, stop_audio) to delegate directly to self._player while keeping _current_pipeline synchronized for legacy and test callers. <em>Reason:</em> Guarantees that word highlight synchronization, seek navigation, and pause/resume work uniformly regardless of which audio backend is active.</li>
  <li><em>Wikipedia Importer Return Key Activation:</em> Updated the article search entry's activate signal handler in window.py to validate input, emit dialog.emit("response", "import"), and invoke dialog.force_close(). <em>Reason:</em> Allows users to press Return or Keypad Enter in the search box to import the article immediately without triggering AttributeError.</li>
  <li><em>Isolated Windows Pre-Init Extension Loading:</em> Updated win_entrypoint.py to import C-extensions in an iterative loop with per-module exception trapping and configured _sounddevice_data PortAudio DLL directory search. <em>Reason:</em> Prevents transient import issues in one extension from cascading and blocking other required libraries.</li>
  <li><em>Wikimedia-Compliant User-Agent Header:</em> Updated user-agent identification string to ReadAloud/1.8.11 (https://github.com/wbernard/parolu; contact@readaloud.app) in wikipedia_importer.py. <em>Reason:</em> Maintains strict compliance with Wikimedia Foundation User-Agent policies for the new version.</li>
  <li><em>Application Version Increment (1.8.11):</em> Updated application version to 1.8.11 across meson.build, src/main.py, src/error_logger.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, build_linux/build_deb.sh, build_linux/debian/control, and CI workflows. <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Responsive Wikipedia Search Entry Form Submission:</em> Fixed the Wikipedia article import modal visual responsiveness upon pressing Return or Keypad Enter in the topic entry box, ensuring the dialog immediately dismisses and seamlessly transitions to the loading progress spinner without unhandled exception popups or freezing. <em>Reason:</em> Delivers a smooth, frictionless keyboard interaction for article lookups matching native Libadwaita dialog behaviors.</li>
  <li><em>Persistent Real-Time Word Highlighting Across Audio Backends:</em> Maintained visual yellow word-level text highlighting during speech playback across all fallback audio engines (SoundDeviceAudioPlayer, WinSoundAudioPlayer, SubprocessAudioPlayer, GStreamerAudioPlayer). <em>Reason:</em> Ensures visual reading assistance remains active and responsive even when running on minimal fallback audio backends.</li>
</ul>

<p><em>Version 1.8.10 - (30 October 2026)</em></p>
<p>Version 1.8.10 introduces automatic paragraph gap separation with an empty line gap between paragraphs upon pressing Return or Keypad Enter, integrates paragraph gap normalization for all document imports and clipboard pastes, incorporates a direct Wikipedia article importer into the Tools menu and header bar, adds an interactive live autocomplete suggestions dropdown matching Wikipedia's website design with article thumbnails and descriptions, enables multi-tab sequential import for related Wikipedia topics with automatic all-tag stripping, embeds the Wikipedia globe logo and a Wikimedia Foundation donation callout card, fixes the broken Open File dialog by eliminating gettext function shadowing, establishes a Wikimedia policy-compliant HTTP client with a resilient standard-library fallback, resolves Flatpak packaging build and site-packages cleanup issues, eliminates premature cancellation when closing modal progress dialogs, modernizes error reporting with native Adw.AlertDialog modals, and expands the automated regression test suite to 244 tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Single-Newline Paragraph Collapse on Return Key:</em> Removed default Gtk.TextView single-newline Return key insertion behavior that placed new lines directly adjacent without vertical spacing. <em>Reason:</em> Tightly packed lines without an empty line gap between paragraphs make it harder for users to distinguish distinct paragraphs visually while text is being spoken and highlighted during speech playback.</li>
  <li><em>Unformatted Single-Newline Text Imports and Pastes:</em> Removed unspaced single-newline document loading and raw clipboard pasting that inserted dense, unformatted paragraphs into the reader. <em>Reason:</em> Raw single-newline text resulted in cramped, hard-to-follow text during speech synthesis; enforcing consistent double-newline gaps between paragraphs makes text substantially easier to follow during audio playback.</li>
  <li><em>Gettext Function Parameter Shadowing in File Dialogs:</em> Removed parameter names "_" in open_file_dialog and save_text_dialog that shadowed Python's _() translation function with None. <em>Reason:</em> When Gio simple actions triggered open_file_dialog(self, action, _), Gio passed None for the parameter, binding "_" to None. Subsequent calls to _("Supported Documents...") crashed with TypeError: 'NoneType' object is not callable, rendering the Open File button completely inoperative.</li>
  <li><em>Direct Browser User-Agent Impersonation in Wikipedia Requests:</em> Removed the spoofed Mozilla/5.0 browser user-agent header from wikipedia_importer.py. <em>Reason:</em> Impersonating a standard browser without client contact metadata violated Wikimedia Foundation's User-Agent Policy, causing Wikipedia's edge firewalls to flag requests as automated bot abuse and block downloads with HTTP 403 Forbidden.</li>
  <li><em>Premature Operation Cancellation on Programmatic Dialog Close:</em> Removed the unrestricted response handler assignment in _start_wikipedia_import that marked operations as cancelled whenever progress_dialog.force_close() was called. <em>Reason:</em> In Libadwaita, force_close() triggers the dialog's close response ("cancel"), which previously caused the completion callback to interpret programmatic closure as a user cancel action, immediately returning and discarding scraped articles before tabs could be populated.</li>
  <li><em>Wildcard Python Library Cleanup Directives in Flatpak Manifest:</em> Removed the "cleanup": ["*"] directives from python3-meson-python and python3-scikit-build in pip-dependencies.json. <em>Reason:</em> The wildcard cleanup directive deleted the entire /app/lib/python3.13/site-packages directory after building build backends, purging installed runtime dependencies and causing ReadAloud to crash on launch with ModuleNotFoundError.</li>
  <li><em>PEP 517 Source Distribution Build Dependency in Flatpak:</em> Removed .tar.gz source tarball archives for beautifulsoup4 and soupsieve in pip-dependencies.json. <em>Reason:</em> Building from source tarballs required the hatchling PEP 517 build backend, which is absent from the standard GNOME Flatpak runtime and caused pip build failures.</li>
  <li><em>Deprecated Gtk.MessageDialog Error Modals:</em> Removed deprecated Gtk.MessageDialog instances and legacy .show() method calls in _show_error(). <em>Reason:</em> Gtk.MessageDialog is deprecated in GTK 4.10+ and failed to render properly as a modal sheet within Libadwaita application windows.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Return Key Stroke Paragraph Gap Separation (HighlightTextView._on_key_pressed):</em> Added a dedicated keyboard controller to HighlightTextView intercepting Return and Keypad Enter to insert \n\n (a separate line with an empty line gap), deleting active selections and wrapping mutations in begin_user_action() / end_user_action() for clean single-step undo/redo, while retaining Shift + Return for single newlines. <em>Reason:</em> Automatically creates visually clear paragraph gaps as the user types without requiring manual double-tapping of the Return key.</li>
  <li><em>Automatic Paragraph Gap Normalization Utility (ensure_paragraph_gaps):</em> Added a text processing engine in src/window.py that converts single newlines into double newlines (\n\n), cleans whitespace on blank lines, normalizes CRLF/CR line endings, and limits excessive newlines to 2. <em>Reason:</em> Guarantees consistent and readable paragraph separation across all imported, pasted, and edited text.</li>
  <li><em>Clipboard Paste Paragraph Formatting (HighlightTextView._on_paste_clipboard):</em> Added clipboard paste interception for GTK's paste-clipboard signal (Ctrl + V, Shift + Insert, and context menu Paste) that asynchronously retrieves clipboard contents and formats text via ensure_paragraph_gaps(). <em>Reason:</em> Ensures all text copied and pasted from external applications immediately adopts readable paragraph gap spacing.</li>
  <li><em>Imported Document Paragraph Formatting:</em> Integrated ensure_paragraph_gaps() across tab creation (create_new_tab), File Open (open_file_complete), Drag &amp; Drop file loaders, EPUB/PDF chapter extractors, Wikipedia imports, and demo presets. <em>Reason:</em> Enforces consistent paragraph spacing for all imported documents regardless of format or source.</li>
  <li><em>Live Wikipedia Search Autocomplete Dropdown (fetch_wikipedia_suggestions):</em> Added real-time autocomplete suggestions to the search box in the Wikipedia import window backed by Wikipedia's official REST Search API (https://{lang}.wikipedia.org/w/rest.php/v1/search/title), returning matching articles with thumbnail previews, bold titles, and subtitle descriptions. <em>Reason:</em> Enables users to quickly search, discover, and pick exact Wikipedia article titles without leaving the application or memorizing precise spelling.</li>
  <li><em>In-Memory Thumbnail Caching (fetch_thumbnail_bytes):</em> Added thread-safe in-memory caching for Wikipedia article thumbnails. <em>Reason:</em> Avoids duplicate network requests and eliminates latency when browsing or re-querying common search suggestions.</li>
  <li><em>Wikipedia Quick-Access Header Bar Button (wiki_button):</em> Added a dedicated Wikipedia import button in the top-left corner of the main window headerbar directly after the Open File button, styled with the Wikipedia globe puzzle logo and standardized (48, 42) dimensions. <em>Reason:</em> Provides one-click access to the Wikipedia article importer without needing to navigate into the burger menu.</li>
  <li><em>Wikimedia Foundation Donation Callout Card:</em> Added a non-intrusive donation callout card inside the Wikipedia import dialog featuring a direct hyperlink button to https://donate.wikimedia.org/. <em>Reason:</em> Encourages users to support the Wikimedia Foundation and keep free knowledge accessible to everyone worldwide.</li>
  <li><em>Wikipedia Article Importer (wikipedia_importer.py):</em> Added a complete Wikipedia scraping and article extraction module capable of normalizing article topic names (e.g. "Artificial Intelligence", "Donald Trump") and full Wikipedia URLs into clean, structured markdown. <em>Reason:</em> Allows users to import Wikipedia articles directly into ReadAloud for offline listening without manually copying and pasting text from web browsers.</li>
  <li><em>Tools Menu Wikipedia Action (win.import-wikipedia):</em> Added "Import Wikipedia Article…" to the Tools submenu in src/window.ui, wired to on_import_wikipedia_action() in src/window.py. <em>Reason:</em> Provides easy and discoverable access to article imports directly alongside existing document and text cleanup tools.</li>
  <li><em>Multi-Tab Related Topic Extraction:</em> Added automatic discovery of internal related /wiki/... article links with a configurable spin button (1–10 articles) in the import dialog, creating a distinct tab for each related article. <em>Reason:</em> Enables research workflows where a main subject and its related references are imported into sequential tabs in one single operation.</li>
  <li><em>Dual-Engine Resilient HTTP Client:</em> Added standard-library urllib.request fallback logic to fetch_wikipedia_article() if requests is unavailable or encounters connection exceptions. <em>Reason:</em> Ensures reliable HTTP fetching across containerized runtimes and environments without third-party network libraries.</li>
  <li><em>Standard-Library HTMLParser Fallback:</em> Added _WikipediaHTMLParser to wikipedia_importer.py to parse and clean Wikipedia article structures without requiring BeautifulSoup. <em>Reason:</em> Guarantees that Wikipedia article parsing continues to operate smoothly even if bs4 is missing from the environment.</li>
  <li><em>Pre-built Pure-Python Universal Wheels for Flatpak:</em> Added pre-built universal .whl packages for beautifulsoup4 and soupsieve to pip-dependencies.json. <em>Reason:</em> Eliminates build-time compiler dependencies and ensures fast, clean Flatpak installations.</li>
  <li><em>Automated Test Suite Expansion (244 Tests):</em> Added 15 comprehensive automated unit tests covering paragraph gap normalization, Return key presses, Keypad Enter, Shift + Return, selection replacement, non-editable text views, clipboard paste formatting, and tab imports, expanding the test suite to 244 automated unit tests. <em>Reason:</em> Guarantees full regression prevention for paragraph gap rules, keyboard shortcuts, and document imports.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Document Buffer Population and Tab Creation:</em> Updated create_new_tab(), _import_dropped_files_into_empty_tab(), _on_import_choice_response(), _apply_and_play_demo(), _on_wikipedia_import_selected(), and open_file_complete() to format text with ensure_paragraph_gaps(). <em>Reason:</em> Standardizes paragraph spacing across every document loading, file dropping, demo loading, and scraping flow in the application.</li>
  <li><em>Undo/Redo Grouping on Paragraph Insertion:</em> Updated Return key insertion and clipboard paste handlers to wrap buffer mutations in begin_user_action() and end_user_action(). <em>Reason:</em> Allows users to undo or redo typed paragraph gaps and formatted pastes in a single Ctrl + Z / Ctrl + Y keystroke instead of multi-step undo operations.</li>
  <li><em>Open File Dialog and Save Dialog Callback Signatures:</em> Updated open_file_dialog and save_text_dialog method signatures to (self, action=None, param=None). <em>Reason:</em> Resolves the critical Open File button crash, allowing file selection and text saving dialogs to open without exception.</li>
  <li><em>Wikipedia Search Box Debouncing and Navigation:</em> Updated the search box with a 250ms debouncer, Down Arrow focus shifting into the suggestions listbox, Enter key selection, Escape key dismissal, and automatic dropdown suppression on full URLs. <em>Reason:</em> Provides a smooth, responsive, and accessible keyboard-first search experience without spamming network endpoints during keystrokes.</li>
  <li><em>Dropdown Scroll and View Adjustment:</em> Updated the suggestions container to use a responsive Gtk.ScrolledWindow with min-content-height: 140px and automatic scroll reset to the top. <em>Reason:</em> Keeps 2–3 suggestions in view while preventing the modal from expanding excessively or pushing dialog controls off-screen.</li>
  <li><em>Automatic All-Tag Stripping on Wikipedia Import:</em> Updated the tab population pipeline (_populate_wikipedia_tabs) so that every fetched article automatically undergoes clean_all_tags() before buffer insertion, removing brackets, pipes, wikitables, hashes, and asterisks. <em>Reason:</em> Formats raw Wikipedia text into smooth, natural, and pronunciation-ready prose for Piper TTS synthesis.</li>
  <li><em>Wikimedia-Compliant User-Agent Header:</em> Updated user-agent identification to "ReadAloud/1.8.10 (https://github.com/wbernard/parolu; contact@readaloud.app)" conforming strictly to the Wikimedia Foundation User-Agent Policy. <em>Reason:</em> Ensures uninterrupted network access and compliant programmatic communication with Wikipedia API and web endpoints.</li>
  <li><em>Worker Exception Scoping in Asynchronous Importer:</em> Updated error capturing in _start_wikipedia_import to bind err_msg = str(err) prior to dispatching GLib.idle_add(). <em>Reason:</em> Prevents Python 3 free variable NameError exceptions resulting from automatic variable cleanup at the end of except blocks.</li>
  <li><em>Application Version Increment (1.8.10):</em> Updated application version to 1.8.10 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, src/wikipedia_importer.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Reader Paragraph Spacing and Vertical Layout:</em> Updated the document text reader view so that all paragraphs are visually separated by an empty line gap (\n\n) when typing with Return, pasting, or importing documents. <em>Reason:</em> Provides generous, clear vertical separation between paragraphs, making it substantially easier for users to read along as words and sentences are highlighted during audio playback.</li>
  <li><em>Wikipedia Search Dropdown Card:</em> Added an expandable suggestions listbox underneath the search box styled with .card and .rich-list, showing article thumbnails, bold headings, and dimmed description captions matching the Wikipedia website layout. <em>Reason:</em> Visualizes search matches and allows immediate visual identification of articles before importing.</li>
  <li><em>Wikipedia Globe Quick-Access Button in Header Bar:</em> Added a dedicated Wikipedia icon button to the top-left header bar between the Open and Save buttons, featuring the clean Wikipedia globe puzzle logo, header-icon-btn CSS styling, and (48, 42) sizing. <em>Reason:</em> Makes Wikipedia imports immediately accessible from the main interface while keeping header controls visually balanced.</li>
  <li><em>Wikipedia Globe Logo in Dialogs:</em> Embedded the high-resolution, alpha-transparent Wikipedia globe logo (/im/zackarious/ReadAloud/images/wikipedia-logo.png) centered in the import dialog and in the asynchronous fetching progress dialog. <em>Reason:</em> Provides clear, professional branding identifying the source of imported content.</li>
  <li><em>Wikimedia Donation Encouragement Card:</em> Added a styled .card container in the import dialog displaying an encouragement message and a centered button linking to https://donate.wikimedia.org/. <em>Reason:</em> Promotes awareness of the non-profit foundation maintaining Wikipedia with an aesthetically integrated donation prompt.</li>
  <li><em>Asynchronous Download Spinner Dialog:</em> Added an active Gtk.Spinner modal alert displaying real-time fetching progress (e.g. "Fetching 'Donald_Trump'…") with a responsive Cancel button. <em>Reason:</em> Provides clear visual feedback during network operations without freezing the main user interface.</li>
  <li><em>Native Adw.AlertDialog Error Presentation:</em> Updated _show_error() to present native Adw.AlertDialog modals with Libadwaita styling and a standard OK response button. <em>Reason:</em> Replaces outdated unstyled message dialogs with polished, theme-integrated alert sheets.</li>
</ul>

<p><em>Version 1.8.9 - (16 October 2026)</em></p>
<p>Version 1.8.9 redesigns the "About ReadAloud" window into a condensed sub-tabbed dialog matching the GNOME Disks GTK4 style with a centered segmented pill switcher, introduces star (asterisk) tag stripping for markdown bold, italics, bullets, and horizontal dividers, adds a unified "Remove All" option directly under the Tools submenu, expands drag-and-drop import tag stripping to 5 options, and increases automated regression test coverage to 210 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Monolithic About Dialog and Multi-Level Drill-Down Subpages:</em> Removed the oversized Adw.AboutWindow implementation and its nested navigation views (whatsnew, details, legal) that required clicking back-and-forth into separate subpages to read changelogs, application description, and legal terms. <em>Reason:</em> The monolithic dialog was excessively tall (600x750px), cramped vertical scrolling within deep navigation pages, and hid important project information behind nested navigation rows.</li>
  <li><em>Sequential Single-Tool Tag Cleanup Constraint:</em> Removed the restriction requiring users to select each bracket, pipe, and hash removal tool one-by-one sequentially from the menu. <em>Reason:</em> Cleaning complex markdown documents containing combinations of brackets, tables, hashes, and asterisks forced users to open the burger menu up to 4 separate times.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Condensed Sub-Tabbed "About ReadAloud" Window (AboutReadAloudWindow):</em> Added a dedicated AboutReadAloudWindow featuring a centered segmented pill switcher (Gtk.StackSwitcher with .linked style) in the headerbar with 5 immediate sub-tabs: About, Change Logs, Description, Credits, and Legal, preserving 100% of all project information with zero data loss. <em>Reason:</em> Provides a compact (~600x680px), modern, and easily navigable interface that conforms to GNOME HIG dialog standards without burying information.</li>
  <li><em>Star (Asterisk) Tag Stripping Tool (clean_star_symbols):</em> Added clean_star_symbols() in src/window.py and registered win.remove-stars ("Remove * Stars (Asterisks)") in the Tools menu. <em>Reason:</em> Strips markdown bold, italic, bullet, footnote, and horizontal divider asterisks (*, **, ***) while normalizing whitespace and punctuation spacing, preventing speech synthesizers from pronouncing punctuation symbols or stumbling over formatting characters.</li>
  <li><em>Star (Asterisk) Import Dialog Checkbox:</em> Added "Remove * stars (asterisks)" as a 5th checkbox option in _create_tag_stripping_checkbox_box within src/window.py, fully synchronized with the dynamic "Select All" / "Deselect All" button. <em>Reason:</em> Enables users to strip asterisk formatting markers automatically upon dragging and dropping Markdown or text files into ReadAloud.</li>
  <li><em>"Remove All" Tools Action (win.remove-all-tags):</em> Added "Remove All" action item under the Tools submenu, backed by clean_all_tags() to strip round brackets, square brackets, pipes/tables, hashes, and stars in a single operation across either the current tab or all tabs. <em>Reason:</em> Delivers an instant, one-click all-in-one cleanup workflow for active documents and multi-tab sessions neatly organized under Tools.</li>
  <li><em>Keyboard Escape Dismissal for About Window:</em> Added a local Gtk.ShortcutController to AboutReadAloudWindow binding the Escape key to close the window. <em>Reason:</em> Conforms to standard desktop dialog dismissal conventions.</li>
  <li><em>Automated Regression Test Suite Expansion (210 Tests):</em> Added comprehensive automated unit tests covering sub-tab stack structure, tab titles, changelog action routing, clean_star_symbols, clean_all_tags, remove-stars action, remove-all-tags action, menu hierarchy verification, and 5-option import dialog state toggles in tests/test_about_window.py, tests/test_text_tools.py, and tests/test_drag_and_drop.py, expanding test coverage to 210 automated unit tests. <em>Reason:</em> Guarantees stability and prevents regressions across text cleanup operations, menu actions, and dialog workflows.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Tag Stripping Pipeline Execution (apply_text_tag_stripping):</em> Updated apply_text_tag_stripping() with the strip_stars parameter to chain markdown image, table/pipe, round bracket, square bracket, hash, and star cleaning in the optimal artifact-free order. <em>Reason:</em> Ensures all text cleaning operations execute cleanly without leaving detached exclamation marks, orphan punctuation, or irregular whitespace.</li>
  <li><em>Drag-and-Drop Placeholder Card Description:</em> Updated the empty tab placeholder card bullet in src/window.ui to state "• Strip brackets, pipes, hashes, or stars on import". <em>Reason:</em> Accurately informs users of all available text cleaning capabilities.</li>
  <li><em>Application Version Increment (1.8.9):</em> Updated application version to 1.8.9 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>GNOME Disks-Style Pill Header Switcher:</em> Updated the About window titlebar to feature a linked segmented toggle button switcher [ About | Change Logs | Description | Credits | Legal ] centered in the headerbar. <em>Reason:</em> Creates a condensed, visually balanced, and intuitive desktop dialog matching modern GNOME applications.</li>
  <li><em>Import Dialog 5-Option Layout:</em> Updated the document import dialog to present 5 neatly aligned tag-stripping checkboxes ("Remove ( ) round brackets and text", "Remove [ ] square brackets and text", "Remove | pipes and text", "Remove # hashes", "Remove * stars (asterisks)") under the "Select All" / "Deselect All" button. <em>Reason:</em> Delivers a harmonious, easily scannable layout that fits comfortably within modal alert boundaries.</li>
  <li><em>Burger Drop Down Menu "Remove All" Placement:</em> Added "Remove All" item directly to the primary burger menu dropdown with clean separator line and inside the Tools submenu. <em>Reason:</em> Enhances accessibility by providing high-visibility access to full document cleanup directly from the main application menu.</li>
</ul>

<p><em>Version 1.8.8 - (10 October 2026)</em></p>
<p>Version 1.8.8 introduces informative hover tooltip popups for the top-right Minimize, Maximize/Restore, and Close window controls, implements dynamic window state tracking that automatically updates the maximize button tooltip between "Maximize" and "Restore", adds titlebar close button tooltips across About and Change Logs dialogs, and expands automated regression test coverage, supported by 193 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Unlabeled Window Control Buttons:</em> Removed un-annotated headerbar window controls where hovering over the Minimize, Maximize, and Close buttons produced no tooltip popup. <em>Reason:</em> Window control buttons lacked descriptive hover tooltips, leaving users without visual confirmation or accessibility explanations of button functions.</li>
  <li><em>Static Maximize Control Labeling:</em> Removed static title bar control state handling that did not distinguish between restored and maximized states. <em>Reason:</em> A static maximize label did not reflect the active window geometry or indicate that clicking the button while maximized will restore the window to its previous dimensions.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Header Bar Window Controls Hover Tooltips:</em> Added dynamic tooltip popups to the Minimize (_("Minimize")), Maximize (_("Maximize") / _("Restore")), and Close (_("Close")) buttons in _update_window_controls_tooltips within ReadAloudWindow. <em>Reason:</em> Delivers clear, standard tooltip popups on hover that explain exactly what each window control button does across all desktop environments.</li>
  <li><em>Reactive Window Maximize / Restore State Detection:</em> Added connection to the window's notify::maximized GObject property signal and toggle_maximize_window handler to dynamically toggle the maximize button's tooltip between "Maximize" (when window is normal/restored) and "Restore" (when window is maximized). <em>Reason:</em> Provides accurate, real-time visual feedback indicating the action that will occur when clicking the button based on current window state.</li>
  <li><em>About Window Control Tooltip:</em> Added close button tooltip assignment in configure_about_contents for Adw.AboutWindow navigation and subpages. <em>Reason:</em> Maintains consistent, accessible tooltip behavior across all secondary dialogs and windows.</li>
  <li><em>Window Controls Test Coverage:</em> Added dedicated unit tests (test_window_controls_tooltips in tests/test_shortcuts.py and close button verification in tests/test_about_window.py), expanding the test suite to 193 automated tests. <em>Reason:</em> Validates tooltip initialization, dynamic text toggling between Maximize and Restore, and prevents regression in window control behavior.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Header Bar Initialization and Mapping Lifecycle:</em> Updated ReadAloudWindow.__init__ and connected the window map signal to ensure window control tooltips are populated immediately upon widget hierarchy realization and refreshed upon window mapping. <em>Reason:</em> Ensures tooltips are consistently applied regardless of window manager decoration overrides or display server re-mapping events.</li>
  <li><em>Application Version Increment (1.8.8):</em> Updated application version to 1.8.8 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Informative Window Control Popups on Hover:</em> Updated the top-right headerbar controls so that hovering over the Minimize, Maximize/Restore, or Close buttons displays a native popup tooltip ("Minimize", "Maximize", "Restore", "Close"). <em>Reason:</em> Enhances visual clarity, accessibility, and desktop integration by clearly explaining the function of each button.</li>
  <li><em>About Window Close Button Tooltip:</em> Updated the About window title bar controls so that hovering over the Close button displays "Close". <em>Reason:</em> Ensures visual consistency with main window controls.</li>
</ul>

<p><em>Version 1.8.7 - (07 October 2026)</em></p>
<p>Version 1.8.7 resolves the word highlighting glitch across soft-wrapped lines and line breaks, introduces a "Select All" toggle button for the file import tag-stripping dialog, enables full tab name hover tooltips without premature truncation, expands em-dash and double-hyphen word tokenization, and adds comprehensive automated unit test coverage, supported by 192 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Logical Paragraph Line Iteration in Word Highlighting:</em> Removed the logical paragraph line iteration in HighlightTextView.do_snapshot_layer that relied on newline delimiters (eol.forward_to_line_end() and cur.forward_line()). <em>Reason:</em> In GTK4 GtkTextView, soft-wrapped display lines within a paragraph do not contain newline (\n) characters; relying on logical line iterators caused line-end iterators to advance past the entire paragraph, producing inverted negative width calculations that truncated the highlight box to a tiny single-character sliver on the first line while leaving subsequent visual lines completely unhighlighted.</li>
  <li><em>Undifferentiated Em-Dash and Double-Hyphen Token Bundling:</em> Removed the indiscriminate \S+ word tokenization in extract_sentences_and_words that treated words joined by closed em-dashes (—) or double-hyphens (--) as single inseparable tokens. <em>Reason:</em> Closed em-dashes and double-hyphens connect distinct words without whitespace; grouping them into one token forced speech synthesizer word boundary timings to span across multiple spoken words and cross over visual line break boundaries.</li>
  <li><em>Premature 24-Character Tab Title Truncation:</em> Removed the artificial 24-character excerpt truncation (first_line[:24] + "…") in bubble._handle_retrieved_text and window.load_text_and_play. <em>Reason:</em> Hardcoding a 24-character slice permanently truncated the tab title string itself, preventing tooltips and hover popup boxes from ever displaying the complete tab title and cutting off phrases mid-word.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Display-Line Bounding Box Traversal (_get_highlight_rectangles):</em> Added visual display line grouping in HighlightTextView that tracks character bounds and clusters them by visual line using vertical overlap (abs(loc.y - line_y) &lt;= max_height * 0.5) to compute precise bounding boxes (min_x, y, max_x - min_x, height) for each individual line touched by a highlighted span. <em>Reason:</em> Guarantees that any active word or phrase wrapping across one or multiple soft-wrapped visual display lines receives accurate, complete bounding boxes for every line it spans.</li>
  <li><em>Em-Dash and Double-Hyphen Word Tokenizer:</em> Added regex sub-tokenization in extract_sentences_and_words that separates words connected by em-dashes (—) or double hyphens (--) into constituent words while keeping terminal punctuation attached and preserving exact character offsets matching original text slices. <em>Reason:</em> Synchronizes speech synthesizer word boundary events with individual spoken words so each word highlights independently and accurately during audio playback.</li>
  <li><em>"Select All" / "Deselect All" Import Dialog Toggle:</em> Added a dedicated "Select All" toggle button to the file import dialog box (_create_tag_stripping_checkbox_box). <em>Reason:</em> Allows users to quickly toggle all 4 tag-stripping options (round brackets, square brackets, pipes, and hashes) on or off with a single click, eliminating the need to check each box individually.</li>
  <li><em>Explicit Tab Tooltip Synchronization:</em> Added explicit page.set_tooltip(title) calls across create_new_tab, open_file, save_text_complete, _on_run_demo, and _prompt_empty_tab_import. <em>Reason:</em> Guarantees that hovering over any tab in AdwTabBar consistently displays a native tooltip popup containing the full tab title, even when the tab label on screen is constrained or ellipsized.</li>
  <li><em>Automated Regression Test Suite Expansion (192 Tests):</em> Added unit tests covering line wrap highlight rectangles, em-dash word splitting, "Select All" toggle logic, full tab title retention, and tab tooltip synchronization in tests/test_highlight_and_language_tick.py, tests/test_drag_and_drop.py, tests/test_tab_system.py, and tests/test_bubble.py. <em>Reason:</em> Ensures stability, prevents regressions in highlight rendering and tab navigation, and validates import dialog interactions.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Multiline Highlight Rendering in HighlightTextView.do_snapshot_layer:</em> Updated snapshot rendering to draw individual 10px rounded padded rectangles across every visual display line segment returned by _get_highlight_rectangles, while retaining an O(1) fast-path for single-line words (loc1.y == loc2.y and loc2.x &gt; loc1.x). <em>Reason:</em> Delivers smooth, full-coverage highlight shapes across all lines for wrapped words or multi-word segments while preserving optimal rendering performance during real-time speech playback.</li>
  <li><em>Dynamic Checkbox State Tracking for Import Dialog:</em> Updated _create_tag_stripping_checkbox_box to observe individual checkbutton toggles and dynamically update the button label between "Select All" (when any checkbox is unticked) and "Deselect All" (when all checkboxes are active). <em>Reason:</em> Provides clear visual feedback representing the current selection state at all times.</li>
  <li><em>Tab Header and Quick Read Title Preservation:</em> Updated load_text_and_play and bubble._handle_retrieved_text to preserve the full first line of imported or selected text (with a 500-character sanity ceiling). <em>Reason:</em> Retains meaningful document context and full tab titles rather than cryptic truncated fragments.</li>
  <li><em>Application Version Increment (1.8.7):</em> Maintained application version 1.8.7 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Adheres to semantic versioning standards for the bug fix release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Seamless Highlight Display Across Line Wraps:</em> Updated active word highlighting so that when a word or phrase wraps across lines, each line displays a complete rounded yellow rectangle with 2x padding behind the text rather than a truncated box on the first line and black text on subsequent lines. <em>Reason:</em> Eliminates the visual highlight glitch where words wrapping at line breaks appeared cut off, partially highlighted, or illegible on dark themes.</li>
  <li><em>Complete Tab Name Popup on Hover:</em> Updated the tab hover popup box in AdwTabBar so that it reveals the full, untruncated name of the tab instead of ending with an ellipsis (…). <em>Reason:</em> Enables users to instantly identify the full document or excerpt name by simply hovering over the tab, especially when tabs are narrow in multi-tab workflows.</li>
  <li><em>"Select All" Button in File Import Dialog:</em> Added an aligned "Select All" button at the top of the tag-stripping checkbox list in Adw.AlertDialog with compact margins (margin_top=2, margin_bottom=2, spacing=3). <em>Reason:</em> Provides an accessible, well-proportioned layout that seamlessly integrates into both single-action and multi-action import dialogs without vertical clipping or awkward crowding.</li>
</ul>

<p><em>Version 1.8.6 - (03 October 2026)</em></p>
<p>Version 1.8.6 introduces full drag-and-drop file import for TXT and MD documents with an empty-tab visual guidance interface, introduces multi-select tag stripping check boxes on import allowing users to strip round brackets, square brackets, pipes, and hashes, adds a dedicated "Remove | Pipes" text cleanup tool with full Markdown table and delimiter row elimination, resolves Markdown table and image orphan exclamation mark artifacts upon import, and consolidates the Tools menu inside the primary Burger Menu, supported by 187 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Standalone Run Demo Headerbar Button:</em> Removed the dedicated "Run Demo" dropdown button from the window headerbar. <em>Reason:</em> Reduces headerbar clutter, consolidates demo playback alongside other tools, and groups related voice tools logically under the Tools menu.</li>
  <li><em>Standalone Tools Headerbar Button (Top Left):</em> Removed the standalone "Tools" dropdown menu button from the top-left section of the window headerbar. <em>Reason:</em> Eliminates visual clutter in the top-left toolbar, keeps the headerbar focused on primary file actions (Open and Save), and avoids redundant menus by centralizing text cleanup utilities and voice demos inside the primary Burger Menu.</li>
  <li><em>Direct Unchecked Empty Tab Import:</em> Removed automatic immediate tab creation without prompt when dropping files into an empty document tab. <em>Reason:</em> Users dropping files into empty tabs had no opportunity to pre-process text or strip unwanted citations, brackets, metadata pipes, or heading hashes before populating the tab.</li>
  <li><em>Alternating Cell Consumption and Line-Break Bridging Regex:</em> Removed the raw single-pass regex (<code>\|[^|]*\|</code> with DOTALL) that consumed shared column delimiter pipes and bridged across line breaks. <em>Reason:</em> Multi-column tables share boundary pipes between cells, and matching across newlines caused alternating cells across lines to be preserved and stitched together while leaving behind delimiter hyphens (---) and dangling pipe characters.</li>
  <li><em>Decoupled Image Bracket Stripping &amp; Orphan Exclamation Delimiters:</em> Removed isolated bracket removal on Markdown image references that left leading exclamation marks (<code>!</code>) stranded on their own lines. <em>Reason:</em> Stripping only bracket pairs from <code>![image](url)</code> left behind disconnected <code>!</code> characters that speech synthesizers read aloud as "exclamation mark" and caused unsightly visual artifacts between paragraphs.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Drag-and-Drop TXT &amp; MD File Ingestion:</em> Added Gtk.DropTarget integration supporting drag-and-drop of TXT and MD text files directly into the application window. <em>Reason:</em> Allows users to quickly and naturally open documents by dropping files from their desktop or file manager.</li>
  <li><em>Empty Tab Drag-and-Drop Visual Guidance Card:</em> Added an explanatory card centered in the editor canvas of empty tabs with an icon, title, format guidelines, and typing dismissal notice. <em>Reason:</em> Teaches new users how to import documents via drag-and-drop while an empty tab is active.</li>
  <li><em>Reactive Typing Dismissal of Placeholder:</em> Implemented reactive buffer change detection that immediately hides the drag-and-drop guidance card when typing begins and restores it if the document is emptied. <em>Reason:</em> Maximizes clean, distraction-free writing space while keeping onboarding guidance available when needed.</li>
  <li><em>Incompatible File Format Validation &amp; Alert Dialog:</em> Added strict file extension validation rejecting non-TXT and non-MD files (e.g., .pdf, .png, .py) with a native Adw.AlertDialog alert ("ReadAloud is only compatible with TXT or MD Files."). <em>Reason:</em> Protects against loading unreadable binary data or unsupported file formats into the speech synthesizer.</li>
  <li><em>Multi-Option Drop Dialog for Populated Tabs:</em> When dropping files into a tab with existing text, prompts the user to choose between "Import into Existing Tab", "Create New Tabs per File", or "All into One New Tab" (with Cancel). <em>Reason:</em> Gives users explicit control over where dropped text is placed without accidentally overwriting existing work.</li>
  <li><em>Multi-Select Tag-Stripping Checkboxes on File Import:</em> Added interactive check boxes to the file import dialogs (for both empty tabs and tabs with existing content) allowing multi-selection to remove ( ) round brackets, [ ] square brackets, | pipes, or # hashes. <em>Reason:</em> Empowers users to pre-process imported documents by stripping unwanted parenthetical notes, citation tags, markdown tables/pipes, or headers before text is loaded into tabs.</li>
  <li><em>Remove | Pipes Text Cleanup Tool:</em> Added the "Remove | Pipes" cleanup tool (clean_pipe_brackets and win.remove-pipe-brackets) to the Tools menu, removing all text enclosed between pipe characters (and empty ||) while normalizing surrounding whitespace and punctuation. <em>Reason:</em> Allows users to remove metadata tags, wiki tables, and pipe-delimited fields so speech engines do not read unwanted pipe symbols or raw table syntax.</li>
  <li><em>Markdown Table Delimiter &amp; Block Detection:</em> Added dedicated markdown table detection (is_table_separator) that identifies table separator rows (<code>| --- | --- |</code> or <code>--- | ---</code>) and scans upwards and downwards to mark all connected table header rows and data rows for removal. <em>Reason:</em> Markdown tables (such as Wikipedia infoboxes and structured documentation tables) contain pipe-delimited data that must be completely removed so speech engines do not read fragmented tabular syntax or table text.</li>
  <li><em>Full-Row Pipe Table Elimination:</em> Added detection for lines beginning and ending with pipe characters (<code>| ... |</code>) to strip all single-column or multi-column table rows cleanly along with all text within them. <em>Reason:</em> Completely removes markdown table rows, infobox cards, and cell content without leaving stray characters or partial lines.</li>
  <li><em>Unified Markdown Image Stripping &amp; Orphan Exclamation Filter:</em> Added pattern matching across bracket cleaners and import tag stripping to remove complete markdown image tags as unified units (<code>![alt](url)</code>), along with a line filter removing stranded exclamation mark lines (<code>!</code>). <em>Reason:</em> Completely eliminates leftover exclamation mark artifacts from imported Markdown articles while preserving legitimate sentence-ending punctuation.</li>
  <li><em>Preset Voice Demos Submenu inside Tools:</em> Moved the preset voice demos (Demo 1 Jenny, Demo 2 Northern English Male, Demo 3 Joe) into a dedicated "Preset Voice Demos" subcategory inside the Tools menu. <em>Reason:</em> Creates a clean, centralized Tools hub containing both text cleanup tools and voice demonstration presets.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Centralized Burger Menu Tools Submenu:</em> Consolidated all text cleanup tools (Remove Brackets, Pipes, Hashes) and Preset Voice Demos under the Tools submenu within the primary Burger Menu (≡). <em>Reason:</em> Provides a consistent, unified menu structure that keeps the application headerbar minimal and uncluttered.</li>
  <li><em>Markdown Table &amp; Image Artifact Cleanup:</em> Updated clean_pipe_brackets(), clean_square_brackets(), clean_round_brackets(), and apply_text_tag_stripping() to eliminate markdown tables, image references, and orphan exclamation marks cleanly, leaving only surrounding text without residual artifacts like dashes (---), image exclamation marks (!), or glued words. <em>Reason:</em> Resolves visual and auditory artifacts where importing Markdown files left behind garbled table fragments or stray punctuation characters.</li>
  <li><em>Tag Stripping Pipeline Execution Order:</em> Updated apply_text_tag_stripping() to execute image and table stripping before bracket and hash stripping. <em>Reason:</em> Strips markdown tables, images, and embedded URLs cleanly at the beginning of the pipeline so individual cleaners do not leave behind detached exclamation marks or partial image descriptions.</li>
  <li><em>Import Dialog Button Response Action Fix:</em> Connected the Adw.AlertDialog import prompt directly to the "response" signal handler instead of dialog.choose(). <em>Reason:</em> Resolves an issue where dialog button clicks resulted in no action because dialog.choose() passes an asynchronous Gio.Task object rather than the response string.</li>
  <li><em>Text Cleanup Tool Tab Scope Dialog Support:</em> Updated _prompt_and_apply_bracket_tool() and _apply_bracket_tool_to_view() to fully support all cleanup tools (round brackets, square brackets, pipes, and hashes). <em>Reason:</em> Provides a uniform dialog asking users whether to apply cleanup to the current tab or across all tabs.</li>
  <li><em>Atomic Undo Support for Text Cleaning Tools:</em> Wrapped all bracket, pipe, and hash removal modifications in buffer.begin_user_action() and buffer.end_user_action(). <em>Reason:</em> Ensures all text cleanup operations can be instantly and safely reverted using Ctrl + Z undo.</li>
  <li><em>Expanded Automated Test Suite (187 Tests):</em> Added comprehensive test suites in tests/test_text_tools.py and tests/test_drag_and_drop.py covering drag-and-drop ingestion, format validation, import tag stripping checkboxes, pipe bracket removal, markdown tables, markdown image syntax stripping, and orphan exclamation line elimination, bringing total passing tests to 187. <em>Reason:</em> Verifies stability, edge cases, and regression prevention across all new features.</li>
  <li><em>Application Version Increment (1.8.6):</em> Maintained application version 1.8.6 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Adheres to semantic versioning standards for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Minimalist Streamlined Top-Left Headerbar:</em> Removed the "Tools" dropdown button from the top-left area of the headerbar, leaving only the Open and Save buttons alongside the window title and tabs. <em>Reason:</em> Greatly simplifies the top-left window layout, creating a balanced, modern, and uncluttered toolbar aesthetic.</li>
  <li><em>Clean Post-Import Tab Text Display without Table or Image Artifacts:</em> Updated imported tab rendering so that Markdown files with tables and images display only clean prose and headings, free from broken table borders, hyphens, dangling pipe characters, and floating exclamation marks. <em>Reason:</em> Delivers an aesthetically clean reading canvas in the text view without messy formatting artifacts.</li>
  <li><em>Centered Empty Tab Drag-and-Drop Guidance Card:</em> Designed a modern centered card with a folder icon, bold title, bullet points, and subtitled hint on empty tab workspaces. <em>Reason:</em> Provides an attractive, informative visual empty-state that explains the drag-and-drop feature at a glance.</li>
  <li><em>Compact Multi-Select Checkboxes in Import Dialogs:</em> Integrated 4 native Gtk.CheckButton checkboxes with clear labels into the Adw.AlertDialog extra child space. <em>Reason:</em> Delivers an intuitive, legible visual checklist for choosing tag stripping options upon file import.</li>
  <li><em>Updated Empty Tab Guidance Text:</em> Refined the placeholder text to explicitly describe stripping brackets, pipes, or hashes on import. <em>Reason:</em> Informs users of the newly added tag-stripping capability directly within the interface.</li>
</ul>

<p><em>Version 1.8.5 - (03 October 2026)</em></p>
<p>Version 1.8.5 introduces in-flight speech synthesis cancellation with a dedicated Cancel button on the loading HUD and Escape key shortcut, introduces a new "Tools" dropdown menu with brackets and hash symbol removal tools featuring tab-scope prompt dialogs and atomic undo support, and expands the Adjust Speed system to a 5-choice ladder by adding calibrated "Slow" and "Slower" settings across all 35 voice models, supported by 158 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Un-cancellable Background Speech Synthesis Loop:</em> Removed the uninterruptible synthesis loop in Reader where Piper speech synthesis ran to completion regardless of user actions. <em>Reason:</em> Long document synthesis could not be aborted if started accidentally or with incorrect voice settings, locking the user out and tying up system CPU resources.</li>
  <li><em>3-Choice Speed System Limitation:</em> Removed the restriction limiting speech rates to only Normal, Fast, and Super Fast. <em>Reason:</em> Many users found Normal too fast for dense or technical reading material, requiring slower, more relaxed playback tempos.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Speech Generation Cancellation &amp; Process Abort:</em> Added full user cancellation capability to active audio synthesis in src/reader.py and src/window.py. Synthesis threads check for cancellation at sentence boundaries and immediately break out, halt generation, clean up partial temporary .wav files, dismiss the loading HUD, and re-enable window sensitivity. <em>Reason:</em> Gives users immediate control to stop unwanted or accidental synthesis operations instantly.</li>
  <li><em>Loading Indicator HUD Cancel Button &amp; Escape Key:</em> Added a pill-shaped Cancel button (.loading-indicator-box .cancel-generation-button) to the loading HUD and bound the Escape key to abort generation. <em>Reason:</em> Delivers an intuitive, accessible visual and keyboard-driven mechanism to cancel audio generation at any moment.</li>
  <li><em>Tools Dropdown Menu in Header Bar:</em> Added a dedicated Tools dropdown menu (GtkMenuButton id="tools_button") directly to the right of the Run Demo menu on the header bar, mirrored in the primary hamburger menu under Text Tools. <em>Reason:</em> Organizes text transformation and pre-reading cleanup utilities into a dedicated, easily accessible menu.</li>
  <li><em>Remove ( ) Round Brackets Tool:</em> Added the "Remove ( ) Brackets" cleanup action, stripping round brackets and all enclosed text, including nested parentheses and multiline blocks, while normalizing surrounding whitespace and punctuation. <em>Reason:</em> Allows users to clean explanatory parenthetical remarks from articles and Wikipedia excerpts prior to speech synthesis.</li>
  <li><em>Remove [ ] Square Brackets Tool:</em> Added the "Remove [ ] Brackets" cleanup action, stripping square brackets and enclosed citations (e.g., [1], [b], [citation needed]), while normalizing adjacent whitespace and punctuation. <em>Reason:</em> Strips distracting reference citation numbers and footnotes from copied encyclopedia texts so they are not read aloud.</li>
  <li><em>Remove # Hashes Tool:</em> Added the "Remove # Hashes" cleanup action, stripping all # characters from text while collapsing multiple spaces and trimming line-leading indentation. <em>Reason:</em> Automatically converts Markdown headings (# Heading to Heading) and cleans hashtags and numeric hash markers so speech engines do not pronounce "hash" or "number sign".</li>
  <li><em>Text Tool Tab Scope Prompt Dialog:</em> Added a modal Adw.AlertDialog when triggering any text cleanup tool, asking the user whether to apply the transformation to the Current Tab or All Tabs (or Cancel). <em>Reason:</em> Provides flexibility to clean a single active document or perform batch cleanup across all open tabs simultaneously.</li>
  <li><em>Atomic Reversible Buffer Edits (Undo Support):</em> Wrapped all text tool transformations in begin_user_action() and end_user_action(). <em>Reason:</em> Enables users to instantly revert any bracket or hash removal using standard Ctrl + Z undo.</li>
  <li><em>"Slow" and "Slower" Speed Options:</em> Expanded the Adjust Speed dropdown from 3 choices to 5 discrete choices: Slower, Slow, Normal, Fast, and Super Fast. <em>Reason:</em> Provides calibrated, slower tempo choices below Normal for relaxed listening and comprehension of complex texts.</li>
  <li><em>35-Voice Model Slow &amp; Slower Speed Calibration:</em> Calibrated Slow as Normal minus 0.1 and Slower as Normal minus 0.2 across all 35 British and American English Piper voice models in VOICE_MODEL_SPEEDS. <em>Reason:</em> Retains model-specific cadence adjustments tailored to each voice's natural delivery.</li>
</ul>

<p><em>Speed Playback Settings Breakdown by Voice Model:</em></p>
<ul>
  <li><code>en_GB-alan-low</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.0 | Super Fast: 1.2</li>
  <li><code>en_GB-alan-medium</code> — Slower: 0.8 | Slow: 0.9 | Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_GB-alba-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-aru-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-cori-high</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-cori-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-jenny_dioco-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-northern_english_male-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-semaine-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-southern_english_female-low</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-vctk-medium</code> — Slower: 0.2 | Slow: 0.3 | Normal: 0.4 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-amy-low</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-amy-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-arctic-medium</code> — Slower: 0.4 | Slow: 0.5 | Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-bryce-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-danny-low</code> — Slower: 0.4 | Slow: 0.5 | Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-hfc_female-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-hfc_male-medium</code> — Slower: 0.7 | Slow: 0.8 | Normal: 0.9 | Fast: 1.2 | Super Fast: 1.5</li>
  <li><code>en_US-joe-medium</code> — Slower: 0.7 | Slow: 0.8 | Normal: 0.9 | Fast: 1.2 | Super Fast: 1.5</li>
  <li><code>en_US-john-medium</code> — Slower: 0.8 | Slow: 0.9 | Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_US-kathleen-low</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-kristin-medium</code> — Slower: 0.8 | Slow: 0.9 | Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_US-kusal-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-l2arctic-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-lessac-high</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-lessac-low</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-lessac-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-libritts-high</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-libritts_r-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ljspeech-high</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-ljspeech-medium</code> — Slower: 0.6 | Slow: 0.7 | Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-norman-medium</code> — Slower: 0.4 | Slow: 0.5 | Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-ryan-high</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ryan-low</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ryan-medium</code> — Slower: 0.5 | Slow: 0.6 | Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Speed Dropdown UI &amp; Default Selection:</em> Updated GtkDropDown in src/window.ui to list Slower, Slow, Normal, Fast, and Super Fast, with Normal selected by default (index 2). <em>Reason:</em> Aligns the UI options with the expanded 5-choice speed ladder while keeping Normal as the default baseline.</li>
  <li><em>Speed Keyboard Navigation (Ctrl + Up and Ctrl + Down):</em> Updated increase_speed() and decrease_speed() to cycle across all 5 discrete choices with bounds clamping. <em>Reason:</em> Provides seamless keyboard stepping from Slower through Super Fast.</li>
  <li><em>Batch Audio Export Cancellation Handling:</em> Updated _batch_export_tabs_audio() in src/window.py to monitor cancellation flags. <em>Reason:</em> Cancelling during multi-tab batch export stops subsequent tab processing immediately and closes the progress dialog.</li>
  <li><em>Expanded Test Suite (158 Tests):</em> Added tests/test_generation_cancellation.py and expanded tests/test_speed_dropdown.py and tests/test_text_tools.py to bring total automated unit tests to 158. <em>Reason:</em> Ensures robust test coverage for cancellation, 5-choice speed mappings, and text cleanup tools.</li>
  <li><em>Application Version Increment (1.8.5):</em> Updated application version from 1.8.4 to 1.8.5 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Reflects the new release adhering to semantic versioning.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Pill-Shaped Cancel Button on Translucent HUD:</em> Designed a sleek pill-shaped Cancel button on the dark translucent HUD with hover and active states matching Libadwaita styling. <em>Reason:</em> Provides a visually appealing, prominent abort control that integrates into the existing loading indicator.</li>
  <li><em>New Tools Dropdown on Header Bar:</em> Positioned the "Tools ▾" button immediately adjacent to "Run Demo ▾". <em>Reason:</em> Creates a balanced, organized headerbar layout with clear visual affordances for text manipulation.</li>
  <li><em>5-Row Speed Popover with Active Selection Tick:</em> The speed dropdown popover now presents all 5 options in vertical progression with an active checkmark (✓) dynamically reflecting the selected speed. <em>Reason:</em> Offers clear visual feedback of the selected speaking rate.</li>
</ul>

<p><em>Version 1.8.4 - (01 October 2026)</em></p>
<p>Version 1.8.4 simplifies speech rate adjustment by replacing the continuous float slider with a streamlined 3-choice dropdown (Normal, Fast, Super Fast), calibrated across all 35 voice models with active selection tick marks and automatic viewport centering when opening dropdown lists, supported by 136 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Continuous 0.1–2.0 Float Speed Slider and Popover:</em> Removed the GtkScale speed adjustment slider and popover menu button from the bottom toolbar in src/window.ui and src/window.py. <em>Reason:</em> The continuous decimal slider was imprecise and cumbersome to adjust, whereas voices require distinct, voice-model-tailored speaking tempos for optimal clarity.</li>
  <li><em>Speed Multiplier Label and Template Bindings:</em> Removed label_2 (speed multiplier text display) and adjustment_2 Gtk.Template.Child bindings from the window class in src/window.py. <em>Reason:</em> Obsolete template child bindings were retired in favor of the standardized GtkDropDown component with backward-compatible proxy methods.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Simplified 3-Choice Speed Dropdown:</em> Added a dedicated speed dropdown (GtkDropDown id="speed_chooser") on the bottom toolbar offering three discrete, accessible settings: Normal, Fast, and Super Fast. <em>Reason:</em> Simplifies user experience by providing clear, natural, and immediate tempo selections without decimal guesswork.</li>
  <li><em>35-Voice Model Speed Conversion Engine:</em> Implemented VOICE_MODEL_SPEEDS dictionary and get_speed_for_voice() in src/window.py mapping all 35 British and American English Piper voice models to calibrated speed floats for Normal, Fast, and Super Fast modes. <em>Reason:</em> Accounts for inherent cadence variations across different voice models to deliver consistent, natural pacing for every voice.</li>
  <li><em>Dropdown Selection Tickmark for Speed:</em> Added active selection checkmarks (✓) next to the chosen speed option in the speed popup list via _setup_dropdown_excerpt(). <em>Reason:</em> Delivers immediate visual confirmation of the currently active speed setting consistent with the language and voice choosers.</li>
  <li><em>Automatic Popover Centering on Active Ticked Choice:</em> Implemented automatic scrolling and vertical centering on notify::visible in _setup_dropdown_excerpt(), ensuring that when a dropdown opens, the active ticked item (such as Ryan Voice further down the list) is immediately centered and visible. <em>Reason:</em> Eliminates the need for manual scrolling to locate the currently selected option in long lists.</li>
  <li><em>Automated Speed Dropdown &amp; Viewport Centering Test Suite:</em> Added tests/test_speed_dropdown.py containing comprehensive tests for all 35 voice model speeds, helper resolution, dropdown UI items, get_value/set_value compatibility, popup checkmarks, keyboard cycling, and automatic popover scrolling, expanding the suite to 136 passing tests. <em>Reason:</em> Protects against regressions in speed mappings, UI dropdown operations, and keyboard navigation.</li>
</ul>

<p><em>Speed Playback Settings Breakdown by Voice Model:</em></p>
<ul>
  <li><code>en_GB-alan-low</code> — Normal: 0.8 | Fast: 1.0 | Super Fast: 1.2</li>
  <li><code>en_GB-alan-medium</code> — Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_GB-alba-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-aru-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-cori-high</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-cori-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-jenny_dioco-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-northern_english_male-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-semaine-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_GB-southern_english_female-low</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_GB-vctk-medium</code> — Normal: 0.4 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-amy-low</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-amy-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-arctic-medium</code> — Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-bryce-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-danny-low</code> — Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-hfc_female-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-hfc_male-medium</code> — Normal: 0.9 | Fast: 1.2 | Super Fast: 1.5</li>
  <li><code>en_US-joe-medium</code> — Normal: 0.9 | Fast: 1.2 | Super Fast: 1.5</li>
  <li><code>en_US-john-medium</code> — Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_US-kathleen-low</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-kristin-medium</code> — Normal: 1.0 | Fast: 1.2 | Super Fast: 1.4</li>
  <li><code>en_US-kusal-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-l2arctic-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-lessac-high</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-lessac-low</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-lessac-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-libritts-high</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-libritts_r-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ljspeech-high</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-ljspeech-medium</code> — Normal: 0.8 | Fast: 1.1 | Super Fast: 1.4</li>
  <li><code>en_US-norman-medium</code> — Normal: 0.6 | Fast: 0.9 | Super Fast: 1.2</li>
  <li><code>en_US-ryan-high</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ryan-low</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
  <li><code>en_US-ryan-medium</code> — Normal: 0.7 | Fast: 1.0 | Super Fast: 1.3</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Speed Keyboard Shortcuts (Ctrl + Up and Ctrl + Down):</em> Updated increase_speed() and decrease_speed() to cycle smoothly between Normal (0), Fast (1), and Super Fast (2) with bounds clamping while preserving fallback compatibility. <em>Reason:</em> Aligns keyboard shortcuts with the simplified 3-choice speed system without breaking existing accelerator keybindings.</li>
  <li><em>Playback Pipeline and Dynamic Voice Switching:</em> Updated playback initialization and toggle_pause() settings change detection to resolve current speed floats dynamically from the active speed mode and selected voice. <em>Reason:</em> Guarantees seamless audio generation and cached playback consistency when switching voices or speed modes.</li>
  <li><em>Documentation and Readme References:</em> Updated README.md and app metainfo descriptions to reflect the simplified 3-choice speed dropdown and discrete keyboard navigation. <em>Reason:</em> Maintains accurate, user-facing feature documentation.</li>
  <li><em>Application Version Increment (1.8.4):</em> Updated application version from 1.8.3 to 1.8.4 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Reflects the new release adhering to semantic versioning.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Cohesive Bottom Toolbar with Speed Dropdown Button:</em> Styled the new speed dropdown button with the speed symbolic gauge icon (im.zackarious.ReadAloud.speed-symbolic) and active mode text alongside the dropdown indicator ([icon] Normal ▾), perfectly harmonizing with the language and voice choosers. <em>Reason:</em> Establishes a clean, unified visual design language across all bottom toolbar controls.</li>
  <li><em>Instant Centered Viewport on Dropdown Open:</em> Dropdown popovers now automatically position the selected choice with its checkmark directly in the middle of the popup viewport upon opening. <em>Reason:</em> Enhances visual ergonomics and usability by eliminating tedious searching and scrolling.</li>
</ul>

<p><em>Version 1.8.3 - (29 September 2026)</em></p>
<p>Version 1.8.3 expands the dynamic editor font zoom ceiling from 300% to 1000%, delivering an ultra-accessible 10× text magnification range with responsive word wrapping, continuous keyboard and mouse wheel scaling, and full settings persistence, supported by 129 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>300% Maximum Font Zoom Ceiling:</em> Removed the hardcoded 300% maximum font size limitation (min(int(percentage), 300)) in src/window.py. <em>Reason:</em> Users with visual impairments, large high-DPI displays (such as 4K and 8K monitors), or room-scale distance reading environments were constrained by the 300% ceiling, which restricted large-format text magnification.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>1000% Ultra-Accessible Dynamic Font Scaling:</em> Added support for scaling editor text up to 1000% (10× baseline magnification) in set_text_zoom(), enabling seamless zoom traversal from 70% to 1000% in 10% increments via Ctrl +, Ctrl -, Ctrl 0, and Ctrl + Mouse Scroll Wheel. <em>Reason:</em> Provides unrestricted accessibility and legibility across all display form factors and viewing distances without text clipping or layout breakdown.</li>
  <li><em>Text Zoom Range &amp; Shortcut Automated Unit Test:</em> Added test_text_zoom_levels_and_shortcuts in tests/test_shortcuts.py, validating zoom scaling up to 1000%, lower bound clamping at 70%, out-of-range value handling, and Ctrl + / Ctrl - / Ctrl 0 keyboard shortcuts, expanding the test suite to 129 passing tests. <em>Reason:</em> Prevents future regressions in zoom limits, keyboard shortcuts, and CSS dynamic styling.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Documentation of Extended Zoom Range:</em> Updated README.md Dynamic Text Zoom specification from 70%–300% to 70%–1000%. <em>Reason:</em> Keeps user-facing feature documentation and shortcut references accurate and up to date.</li>
  <li><em>Application Version Increment (1.8.3):</em> Updated application version from 1.8.2 to 1.8.3 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Reflects the new release adhering to semantic versioning.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>High-Magnification Typography Rendering:</em> Editor text can now expand up to 1000% scale while maintaining crisp vector glyph rendering, balanced line heights, and responsive soft-wrapping. <em>Reason:</em> Allows comfortable reading of oversized text from across the room or on large television/presentation screens without horizontal overflow.</li>
</ul>

<p><em>Version 1.8.2 - (26 September 2026)</em></p>
<p>Version 1.8.2 introduces native title bar window controls with Minimize and Maximize/Restore buttons positioned immediately after the primary burger menu, native window manager integration with keyboard shortcuts and application actions, and a comprehensive AI engineering attribution and open-source licensing acknowledgment in the Application Description window, backed by 128 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>GNOME Title Bar Single-Close Default Limitation (:close):</em> Removed reliance on GNOME/Libadwaita's standard single-button title bar layout (:close) by explicitly defining and enforcing :minimize,maximize,close in both src/window.ui and src/window.py. <em>Reason:</em> In default GNOME desktop environments, title buttons are restricted solely to the close button, preventing users from directly minimizing or maximizing the application window via header bar controls without external system-level configuration tweaks.</li>
  <li><em>Omission of AI Tooling &amp; Open-Source Engineering Attribution:</em> Removed the undocumented gap regarding AI tool usage and engineering ownership in the application description. <em>Reason:</em> Transparent attribution ensures users and open-source contributors understand the architecture and review rigor behind AI-accelerated development while reaffirming full ownership of technical decisions and copyleft reciprocal obligations under the GNU General Public License v3.0.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Top-Right Minimize and Maximize Header Bar Controls:</em> Added dedicated Minimize (window-minimize-symbolic / —) and Maximize/Restore (window-maximize-symbolic / □) title buttons placed immediately after the primary menu (burger) button on the right side of AdwHeaderBar. <em>Reason:</em> Provides users across all desktop environments (GNOME, KDE Plasma, XFCE, Windows) with immediate, intuitive, and standard window management controls.</li>
  <li><em>Application Window Management Actions (win.minimize &amp; win.toggle-maximize):</em> Added minimize_window() calling self.minimize() and toggle_maximize_window() toggling between self.maximize() and self.unmaximize(), exposing them as win.minimize and win.toggle-maximize Gio actions on ReadAloudWindow. <em>Reason:</em> Enables robust programmatic control of window state accessible via actions, menus, and keyboard shortcuts.</li>
  <li><em>Primary Menu Window Control Items:</em> Added "Minimize Window" and "Maximize Window" action items into the primary burger menu dropdown (primary_menu). <em>Reason:</em> Allows accessibility and menu-driven window control for users who prefer navigation via application menus or keyboard menu navigation.</li>
  <li><em>F11 Maximize / Restore Keyboard Shortcut:</em> Added the F11 key binding in _on_window_key_pressed to toggle window maximization, fully documented in the Keyboard Shortcuts help overlay (src/gtk/help-overlay.ui). <em>Reason:</em> Conforms to standard desktop conventions for fullscreen/maximize toggling with a single dedicated key press.</li>
  <li><em>AI Acceleration &amp; Core Architecture Attribution in Application Description:</em> Added the dedicated engineering acknowledgment paragraph verbatim into APP_DESCRIPTION displayed in the Application Description page of the About window. <em>Reason:</em> Clearly states that while AI tools such as Anti-gravity and Claude were leveraged to accelerate software development, core architecture, rigorous code reviews, technical trade-offs, and GPL v3 open-source compliance remain entirely owned by the author.</li>
  <li><em>Window Controls &amp; Description Test Suite Expansion:</em> Added test cases in tests/test_shortcuts.py (test_header_bar_decoration_layout, test_minimize_and_maximize_actions, test_f11_shortcut_toggles_maximize) and tests/test_about_window.py (Anti-gravity, Claude, and open-source terms), expanding test suite coverage to 128 passing tests. <em>Reason:</em> Prevents regressions in window management behavior, headerbar decoration layouts, shortcuts, and metadata integrity.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Header Bar Decoration Enforcement on Window Initialization:</em> Updated ReadAloudWindow.__init__ to explicitly bind header_bar and call self.header_bar.set_decoration_layout(":minimize,maximize,close"). <em>Reason:</em> Ensures the window control layout is strictly maintained at runtime regardless of theme overrides or desktop settings daemon interference.</li>
  <li><em>About Dialog Description &amp; Test Verification:</em> Updated APP_DESCRIPTION in src/main.py and tests/test_about_window.py to seamlessly integrate the new third paragraph while preserving quality level and multi-speaker model documentation. <em>Reason:</em> Maintains cohesive visual formatting, readable typography, and complete test verification in the details subpage.</li>
  <li><em>Application Version Increment (1.8.2):</em> Updated application version from 1.8.1 to 1.8.2 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, build_windows/win_entrypoint.py, and CI workflows (.github/workflows/build-windows.yml). <em>Reason:</em> Conforms to semantic versioning for the new release.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Top-Right Title Bar Controls Layout:</em> The top-right corner of the window now cleanly renders the Burger Menu button followed in sequence by the Minimize button (—), Maximize/Restore button (□), and Close button (✕). <em>Reason:</em> Establishes a balanced, familiar window title bar interface consistent with modern multi-platform desktop user experiences.</li>
  <li><em>Application Description Window Typography Flow:</em> The Application Description subpage in the About ReadAloud window features the newly added engineering paragraph positioned with consistent paragraph spacing directly after the offline privacy guarantee. <em>Reason:</em> Enhances transparency and readability within the Libadwaita clamp container without cramping adjacent paragraphs or causing visual overflow.</li>
</ul>

<p><em>Version 1.8.1 - (25 September 2026)</em></p>
<p>Version 1.8.1 introduces vertical viewport center-alignment during speech playback, completely eliminates text jumping and micro-flickering across words on the same line, adds dynamic tail-padding for end-of-document centering, and introduces an automated standalone Microsoft Windows executable packaging and installer toolchain, supported by 125 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Bottom-Pinned Viewport Threshold Scrolling (use_align=False):</em> Removed the minimum-distance viewport threshold auto-scrolling (use_align=False, within_margin=0.1) in src/window.py. <em>Reason:</em> Only scrolling when text reached the bottom 10% of the viewport pinned the actively spoken text line directly against the bottom toolbar, cutting off upcoming lines and causing eye strain.</li>
  <li><em>Conflicting Immediate Adjustment Snaps (vadj.set_value):</em> Removed manual programmatic adjustment setting (vadj.set_value(clamped_val)) from _highlight_word. <em>Reason:</em> Manually setting the adjustment on every single highlighted word abruptly interrupted GTK's native smooth-scroll interpolation, fighting with the target baseline and causing rapid 5-pixel vertical saw-tooth vibration and flickering on every word during playback.</li>
  <li><em>Redundant Per-Word Scrolling on Identical Visual Lines:</em> Removed unconditional scrolling invocation on every word highlight event. <em>Reason:</em> Re-triggering scroll physics across words on the exact same visual line caused micro-jitter and continuous layout recalculation; keeping the viewport stationary while traversing words on a line provides a stable, flicker-free reading experience.</li>
  <li><em>Restricted 12px Editor Bottom Margin:</em> Removed the static 12px bottom text margin in editor tabs. <em>Reason:</em> Without sufficient padding at the end of the text buffer, the viewport ran out of scrollable room, trapping the final paragraphs at the bottom of the window and preventing them from reaching the center of the screen.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>True Vertical Center Auto-Scroller (yalign=0.5):</em> Added true vertical center scrolling using GTK's native scroll_to_iter alignment (within_margin=0.0, use_align=True, xalign=0.0, yalign=0.5), keeping the active highlighted word line dead-center in the window during playback. <em>Reason:</em> Guarantees that the active line is always centered 50% from top and bottom, giving readers balanced view of preceding context and upcoming lines ahead.</li>
  <li><em>Dynamic End-of-Document Bottom Margin Expansion:</em> Added dynamic bottom margin calculation (desired_bottom_margin = max(350, int(page_size * 0.5))) on the editor's text view. <em>Reason:</em> Ensures that regardless of window height, the document tail always has at least half a viewport of trailing space, enabling the very last sentence of any document to scroll to the exact vertical center of the screen without toolbar collision.</li>
  <li><em>Visual Line &amp; Paragraph Change Detection:</em> Added dual tracking of visual line coordinates (self._last_scrolled_line_y) and buffer line indices (self._last_scrolled_line_idx), with automated off-screen detection and force_scroll override for seeking. <em>Reason:</em> Guarantees that scrolling only engages when speech transitions across visual lines (hard newlines or soft wraps) or during navigation, keeping the viewport completely rock-solid and still while reading words on the same line.</li>
  <li><em>Standalone Microsoft Windows Executable &amp; Installer Toolchain:</em> Added Windows packaging suite with PyInstaller specification (build_windows/ReadAloud.spec), entry point wrapper (build_windows/win_entrypoint.py), Windows dependencies (requirements-windows.txt), Inno Setup compiler script (build_windows/installer.iss), and GitHub Actions CI workflow (.github/workflows/build-windows.yml) generating portable zip and setup installer executables. <em>Reason:</em> Enables native standalone execution and distribution of ReadAloud on 64-bit Microsoft Windows without requiring separate MSYS2 or Linux installations.</li>
  <li><em>Same-Line Playback Stability Automated Test:</em> Added test_highlight_word_no_jumping_on_same_line in tests/test_highlight_and_language_tick.py, expanding the automated unit test suite to 125 passing tests. <em>Reason:</em> Verifies programmatically that multiple word highlights on the same line do not trigger spurious scroll calls, preventing regressions in reading stability.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Smooth Viewport Interpolation in _highlight_word:</em> Updated auto-scrolling to rely exclusively on GTK4's native smooth-scrolling ease-out curves without external adjustment overrides. <em>Reason:</em> Delivers fluid, organic vertical transitions when advancing from one line to the next with zero direction reversals or jitter.</li>
  <li><em>Highlight State Invalidation on Seek &amp; Tab Switch:</em> Updated _clear_highlight() and tab selection callbacks to reset _last_scrolled_line_y = None and _last_scrolled_line_idx = None. <em>Reason:</em> Ensures that stopping, seeking, or switching documents immediately re-centers the new active word on the first speech tick.</li>
  <li><em>Application Version Increment (1.8.1):</em> Updated application version from 1.8 to 1.8.1 across meson.build, src/main.py, data/im.zackarious.ReadAloud.metainfo.xml.in, README.md, build_windows/installer.iss, and CI workflows. <em>Reason:</em> Reflects the new release adhering to semantic versioning.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Centered Active Reading Viewport:</em> The currently spoken line remains positioned at the vertical midpoint of the display, with ample breathing room above and below. <em>Reason:</em> Dramatically reduces eye fatigue and eliminates obstruction from the bottom action toolbar.</li>
  <li><em>Rock-Solid In-Line Word Traversal:</em> Highlighted words advance across the active line with zero vertical jumping, oscillation, or stutter. <em>Reason:</em> Creates a pleasant, calm reading environment where the text stays stationary under the reader's gaze.</li>
  <li><em>Smooth Eased Line Transitions:</em> When speech moves to a new line, the viewport smoothly glides downward in a single fluid motion. <em>Reason:</em> Replaces abrupt jumping with a polished, professional animation.</li>
  <li><em>Generous Bottom Clearance for Tail Sentences:</em> The bottom padding extends dynamically below the text, lifting the final lines off the window edge. <em>Reason:</em> Prevents the last sentence from getting cut in half or obscured behind playback controls.</li>
</ul>

<p><em>Version 1.8 - (17 September 2026)</em></p>
<p>Version 1.8 introduces a redesigned geometric plus-style cross layout for the Quick Listener desktop companion widget, permanently locking the central Play/Pause button at its exact on-screen position across both compact and expanded states, smooth organic outward and inward morphology animations, unified outer perimeter styling with inner border elimination, 100% transparent click-through corner cutouts via dynamic compositor input regions, persistent rewind and forward controls with GTK4 GSK render cache invalidation, and full Wayland/X11 compatibility, supported by 122 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Asymmetric Window Expansion and Positional Drift (B3 to C5):</em> Removed the dynamic top-left resizing mechanism that resized the window from 72×72px down-and-right to 216×216px, which previously shifted the central Play/Pause button across the user's desktop (e.g. from grid position B3 to C5). <em>Reason:</em> Shifting the button position disoriented users and moved the button away from the pointer during hover expansion; anchoring the center button at (108, 108) within a constant 216×216px transparent canvas ensures the Play/Pause button remains completely stationary on screen while controls emerge around it.</li>
  <li><em>Inner Border Lines Around Center Play/Pause Button:</em> Removed interior white borders and separate bounding box strokes around the central Play/Pause button. <em>Reason:</em> Interior dividing lines made the layout appear cluttered and fragmented; drawing a unified continuous outer perimeter contour gives the plus layout a sleek, seamless, cohesive aesthetic.</li>
  <li><em>Opaque and Pointer-Blocking Corner Bounding Box:</em> Removed opaque background fills and pointer-intercepting canvas areas in the four corner cutouts surrounding the plus shape. <em>Reason:</em> A solid rectangular bounding box blocked user interaction with desktop windows underneath; integrating Gdk.Surface.set_input_region guarantees mouse clicks and scroll events in transparent corners pass straight through to underlying applications.</li>
  <li><em>Stale Opacity Guards in Middle Row Snapshotting:</em> Removed local opacity guards (if op > 0.005:) and decoupled progress state in MiddleRowBox. <em>Reason:</em> In GTK4, container render node caching (GSK) caused the Rewind 15s and Fast Forward 15s buttons to intermittently vanish when local progress lagged behind the parent container; deriving progress directly from PlusBubbleBox and invalidating render nodes guarantees all controls persist reliably.</li>
  <li><em>Full Circular Expansion Profile:</em> Removed expanding into a solid 216×216px circular disc (border-radius: 50%) when hovering over the Play/Pause button. <em>Reason:</em> Replaced with an ergonomic plus-style cross layout where arms branch out directionally toward each corresponding button, minimizing desktop footprint while providing distinct directional targets.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Center-Locked Play/Pause Position Anchor:</em> Added a fixed-center coordinate architecture (108, 108) on a constant 216×216px transparent canvas, keeping the central Play/Pause button permanently anchored at its exact on-screen position (e.g. B3) in both compact circular mode and expanded plus mode. <em>Reason:</em> Completely eliminates positional drift upon expansion while remaining 100% compatible with Wayland compositors (which strictly prohibit client-side window repositioning).</li>
  <li><em>Dynamic Input Region Pass-Through via Gdk.Surface.set_input_region:</em> Added dynamic cairo.Region masking in _update_input_region that restricts pointer events to the 72×72px circular bounds in compact mode and the horizontal/vertical cross arms in expanded mode. <em>Reason:</em> Allows clicks and gestures in the four corner cutouts and outer canvas area to pass directly through to desktop windows underneath without intercepting user input.</li>
  <li><em>Directional Symmetrical Plus Expansion Layout:</em> Added directional outward expansion where secondary controls emerge symmetrically around the stationary Play/Pause button: Export CD (Top), Stop Playback (Bottom), Rewind 15s (Left), and Fast Forward 15s (Right). <em>Reason:</em> Provides an intuitive, natural spatial layout where the user can access navigation and export options without their cursor losing contact with the primary playback button.</li>
  <li><em>Smooth Outward (260ms) and Inward (200ms) Plus Morphology Animations:</em> Added tick-driven easing animations (ep = p²(3 - 2p)) in PlusBubbleBox that smoothly stretch the circle into the plus shape while translating sub-buttons outward from the center into their respective positions. <em>Reason:</em> Creates an organic, polished transition where controls bloom smoothly from behind the Play/Pause button rather than appearing abruptly.</li>
  <li><em>Unified Cairo Perimeter Path Construction:</em> Added dynamic vector path tracing in PlusBubbleBox.do_snapshot using four rounded semicircular arm caps and inner right-angle corners with a single continuous 2.5px white border stroke (#ffffff). <em>Reason:</em> Produces a clean, vector-sharp plus shape border with zero interior dividing lines across any scaling factor or display DPI.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>GSK Render Node Synchronization for Rewind and Fast Forward Icons:</em> Updated MiddleRowBox.do_snapshot to derive animation progress directly from its parent PlusBubbleBox, bypassed opacity/translation transforms when expanded, and explicitly invalidated redraw passes with self.middle_box.queue_draw(). <em>Reason:</em> Resolves an issue where GTK4's Scene Graph (GSK) reused stale cached render nodes with zero opacity, causing Rewind and Fast Forward buttons to intermittently disappear.</li>
  <li><em>Euclidean Hit-Testing and Motion Tracking for (108, 108) Center:</em> Updated _is_point_in_plus, _get_button_at_pos, and pointer motion tracking to calculate Euclidean distances from the new (108, 108) center and cross arms. <em>Reason:</em> Guarantees accurate button activation, hover highlights, and drag detection across the fixed 216×216px canvas in both compact circle mode and expanded plus mode.</li>
  <li><em>Quick Listener Collapse Finalizer:</em> Updated _finish_collapse to maintain the 216×216px transparent window size and re-apply the compact 72×72px input mask rather than resizing top-level window geometry. <em>Reason:</em> Prevents window manager origin jumping and maintains exact desktop placement when collapsing back to the compact circular bubble.</li>
  <li><em>Automated Test Suite Expansion (122 Tests Passing):</em> Updated tests/test_bubble.py to validate the (108, 108) center anchor, plus arm hit-testing, corner cutout pass-through, expanded button persistence, and CSS transparency. <em>Reason:</em> Ensures complete test coverage and prevents future regressions across all Quick Listener interaction flows.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Geometric Plus-Style Cross Silhouette:</em> The Quick Listener expands into a distinct plus-shaped cross with four rounded arms extending 72px from the center, replacing the previous solid circular disc. <em>Reason:</em> Creates an iconic, visually uncluttered silhouette that clearly defines the 5 interactive control regions.</li>
  <li><em>Seamless Unified Outer Border with Zero Inner Lines:</em> The plus shape features a single continuous 2.5px solid white border (#ffffff) around its outer perimeter, with all interior borders around the play/pause button removed. <em>Reason:</em> Establishes a minimalist, cohesive appearance without distracting interior dividing lines.</li>
  <li><em>100% Transparent Pass-Through Corner Cutouts:</em> The four corner quadrants between the plus arms are rendered completely transparent with zero dark overlay or bounding box shading. <em>Reason:</em> Blends naturally with any wallpaper or application window underneath without blocking visual content.</li>
  <li><em>Smooth Outward Emerge Transition for Sub-Buttons:</em> Sub-button icons slide outward from behind the center Play/Pause button into their final positions while fading in from opacity 0 to 1 during expansion. <em>Reason:</em> Delivers fluid visual choreography that makes the controls feel as though they are blooming directly from the primary button.</li>
  <li><em>Center-Anchored Visual Position Stability:</em> The Play/Pause button remains visually fixed at the exact same screen coordinates throughout hover expansion and collapse. <em>Reason:</em> Eliminates jarring visual jumping and ensures complete visual consistency for the user.</li>
</ul>

<p><em>Version 1.7 - (16 September 2026)</em></p>
<p>Version 1.7 introduces interactive playback controls directly onto the floating Quick Listener companion widget, including a dynamic 5-button cross (D-pad) layout revealing export audio (single or multi-tab), 15-second rewind, pause/resume, stop, and fast-forward controls when hovering over the active play or pause icon, a 1.5-second anti-flicker leave delay, paused seeking with word scrolling and automatic resume, instant pause/resume toggling, all styled in signature golden yellow matching the ReadAloud brand identity with 3D flip transitions, tactile bounce feedback, precision word highlight synchronization during seeks, contextual right-click menu options, and bi-directional playback synchronization, supported by 117 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Abrupt 150ms Leave Timeout on Quick Listener:</em> Removed the aggressive 150ms collapse timeout triggered when the mouse pointer leaves the expanded Quick Listener bubble. <em>Reason:</em> A 150ms timeout caused severe visual flickering and abrupt accidental collapse whenever the user's cursor brushed against the border or briefly moved between controls; replacing it with a 1.5-second debounce delay ensures a smooth, forgiving user experience.</li>
  <li><em>Horizontal 288×72px Capsule Hover Layout:</em> Removed the linear 4-button horizontal strip container (288×72px) for expanded Quick Listener controls. <em>Reason:</em> Replaced with a balanced 216×216px 5-button cross (D-pad) arrangement that places Stop underneath Pause, Rewind to the left, Forward to the right, and adds an Export Audio button directly above Pause for intuitive directional navigation.</li>
  <li><em>Static Single-Action Quick Listener Click Behavior:</em> Removed unconditional invocation of clipboard text capture on every bubble left-click regardless of whether audio was already playing. <em>Reason:</em> Clicking the bubble during active listening previously interrupted playback and redundantly opened new document tabs; replacing this with contextual playback awareness allows users to pause, resume, and seek active audio smoothly.</li>
  <li><em>Static Speaker Icon Display During Audio Playback:</em> Removed displaying the static speaker megaphone icon while audio is actively playing or paused. <em>Reason:</em> A static icon offered no visual indication of ongoing playback or available interactive controls; dynamically switching to pause and play icons gives immediate visual confirmation of audio status.</li>
  <li><em>White Monochrome Icon Styling in Quick Listener:</em> Removed the plain white icon color (color: #ffffff) from the listener bubble stylesheet. <em>Reason:</em> Plain white icons lacked visual connection with the application's signature golden yellow identity; styling all icons in matching bright yellow (#fee14d) delivers striking high-contrast vibrancy against the black circular bubble background.</li>
  <li><em>Generic Desktop Seek Symbolic Icons:</em> Removed reliance on generic desktop seek icon names (media-seek-backward-symbolic and media-seek-forward-symbolic). <em>Reason:</em> Desktop icon themes frequently override these icons with hardcoded grey fills (#dedede), generic double-arrows, or missing glyphs under Flatpak, failing to reflect the signature golden yellow styling or dedicated 15-second skip action.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>1.5-Second Anti-Flicker Hover Leave Debounce Delay:</em> Added a 1.5-second (1500ms) delay before collapsing the Quick Listener bubble when the pointer leaves the widget. If the user moves back into the bubble within 1.5 seconds, the collapse timer is cancelled immediately and controls remain smoothly expanded. <em>Reason:</em> Stops aggressive visual flickering and prevents accidental collapse when users accidentally move the mouse over or away from the play/pause and navigation buttons.</li>
  <li><em>Paused Seeking with Auto-Resume Playback:</em> Added automatic audio playback resumption when clicking the Rewind 15s or Fast Forward 15s buttons while playback is paused, alongside immediate word highlight updating and auto-scrolling to the new speech position. <em>Reason:</em> Allows users to quickly skip to a new passage while paused and immediately continue listening without needing a second click on the Play button.</li>
  <li><em>Quick Listener Export Audio Integration:</em> Added dedicated Export Audio button (export_box) located directly above the Pause icon in the top slot of the cross layout, using the bundled CD vinyl icon (im.zackarious.ReadAloud.cd). Clicking it invokes main_window.save_audio_dialog(), allowing users to export the current tab or batch export all open tabs directly from the desktop companion widget without opening or refocusing the main window. Added corresponding "Export Audio" (bubble.export) action to the right-click context menu. <em>Reason:</em> Empowers users to save synthesized audio files effortlessly from anywhere on the desktop while listening to speech.</li>
  <li><em>Quick Listener 5-Button Cross (D-pad) Expansion:</em> Added dynamic expansion from a 72×72px compact circle into a 216×216px circular cross layout when hovering over the Pause or Play icon during an active audio session, revealing Export Audio (Top), Rewind 15s (Left), Pause/Play (Center), Fast Forward 15s (Right), and Stop Playback (Bottom). <em>Reason:</em> Provides balanced, ergonomic directional navigation that groups all core playback and export actions around the central button.</li>
  <li><em>Quick Listener Complete Playback Stop Functionality:</em> Added dedicated Stop playback button (stop_box, im.zackarious.ReadAloud.stop-symbolic) underneath the Pause icon and in the right-click popover menu. Clicking Stop halts audio immediately, removes text highlight markers, resets playback state, and flips the Quick Listener bubble back to its compact 72×72px circular profile with the yellow speaker application icon. <em>Reason:</em> Allows users to fully terminate an audio reading session directly from the desktop companion widget without opening or refocusing the main application window.</li>
  <li><em>Dedicated 15-Second Rewind &amp; Fast-Forward Action Icons:</em> Added custom bundled action icons (im.zackarious.ReadAloud.rewind-15-symbolic and im.zackarious.ReadAloud.forward-15-symbolic) featuring crisp circular arrows with the number '15' in the center, built-in #fee14d golden yellow styling, GResource registration, and multi-tier embedded fallback. <em>Reason:</em> Ensures the 15-second skip controls render clearly, beautifully, and strictly in signature golden yellow under all desktop environments, themes, and Flatpak runtimes.</li>
  <li><em>Precision Audio Seeking &amp; Text Highlight Synchronization:</em> Added relative seeking backend methods (seek(seconds_delta)) in Reader, BaseAudioPlayer, GStreamerAudioPlayer, and SoundDeviceAudioPlayer, with instant binary search highlight synchronization, boundary clamping, and pause_resume_mark adjustment in ReadAloudWindow. <em>Reason:</em> Ensures audio playback, word highlight position, and text marks remain sample-accurate and visually synchronized when jumping forward or backward in time.</li>
  <li><em>Quick Listener Interactive Pause &amp; Resume Controls:</em> Added one-click pause and resume functionality to the floating Quick Listener bubble. Clicking the bubble while audio is playing immediately pauses playback; clicking it while paused resumes playback seamlessly from the exact character offset where it was paused. <em>Reason:</em> Eliminates the friction of switching windows, restoring minimized applications, or mouse navigation back to the main window just to pause or resume playback.</li>
  <li><em>Dynamic Context-Sensitive Right-Click Menu:</em> Added real-time context menu item updates in the bubble's right-click popover ("Export Audio", "Pause Playback" when playing, "Resume Playback" when paused, "Rewind 15s", "Stop Playback", "Fast Forward 15s", and "Read Highlighted Text" when idle). <em>Reason:</em> Ensures secondary right-click options remain fully synchronized with the user's active listening workflow.</li>
  <li><em>Bi-Directional Playback State Synchronization:</em> Added automated state dispatch from ReadAloudWindow (start_playback, toggle_pause, stop_playback, seek_playback) to ListenerBubbleWindow, reinforced with a state verification check in the bubble's periodic timer. <em>Reason:</em> Guarantees the floating listener widget accurately mirrors playback status even when playback is controlled via keyboard shortcuts (Ctrl+P, Escape) or bottom toolbar buttons in the main window.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Universal Play/Pause Hover Expansion:</em> Updated _on_motion_enter and _on_motion_move in ListenerBubbleWindow to trigger expansion when _current_playback_state in ("playing", "paused"), ensuring hovering over either the Play or Pause button reveals all controls. <em>Reason:</em> Restores user ability to view navigation and export options while paused without first resuming playback.</li>
  <li><em>Forced Highlight Update and Text Scrolling on Seek:</em> Updated _update_highlight with a force parameter and clamped boundary selection, ensuring seeking immediately applies highlight tags and scrolls the text buffer into view even during paused states. <em>Reason:</em> Eliminates desynchronization between audio position and visible editor text when navigating.</li>
  <li><em>Euclidean 5-Zone Coordinate Routing:</em> Updated _on_drag_end and pointer motion tracking to calculate Euclidean distance from cursor (x, y) to the 5 button centers in the 216×216px space (Top Export: 108, 36; Left Rewind: 36, 108; Center Pause/Play: 108, 108; Right Forward: 180, 108; Bottom Stop: 108, 180). <em>Reason:</em> Provides accurate, seamless hit detection and hover highlights across the circular cross layout while preserving drag repositioning when dragged greater than 8 pixels.</li>
  <li><em>Dynamic Tooltip &amp; Pointer Feedback:</em> Updated Quick Listener tooltips and pointer hover states to dynamically report the active control underneath the pointer ("Export Audio (current tab or all tabs)", "Rewind 15 seconds", "Pause playback", "Resume playback", "Stop playback", "Fast forward 15 seconds", "Read highlighted text"). <em>Reason:</em> Delivers immediate, clear affordance to users on mouse hover regarding what clicking each portion of the widget will do.</li>
  <li><em>Automated Test Suite Expansion (117 Tests Passing):</em> Added unit tests across tests/test_bubble.py and tests/test_pause_voice_switch.py verifying the 1.5s leave debounce delay, hover expansion when paused, and paused seek auto-resume. <em>Reason:</em> Guarantees high stability, complete code coverage, and automated regression prevention across all Quick Listener and audio seeking capabilities.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Flicker-Free 1.5s Debounced Hover Transitions:</em> Quick Listener controls linger stably for 1.5 seconds upon pointer leave, preventing flickering when moving across buttons or brushing past the widget. <em>Reason:</em> Completely eliminates rapid blinking or jarring collapse animations during mouse interaction.</li>
  <li><em>216×216px Circular Cross Layout (.listener-bubble-box.expanded):</em> Replaced horizontal capsule with a 216×216px circular container (border-radius: 50%) with a 3-row vertical box holding Export Audio at the top, a 3-column middle box for Rewind, Pause, and Forward, and Stop at the bottom. <em>Reason:</em> Replaces the elongated horizontal bar with an elegant, symmetrical circular controller that naturally fits all directional actions.</li>
  <li><em>Dead-Center Icon Alignment in Sub-Buttons:</em> Centered all 5 icons horizontally and vertically within their respective 54×54px circular hit boxes (halign=CENTER, valign=CENTER, hexpand=True, vexpand=True). <em>Reason:</em> Eliminates visual off-center skewing where icons were previously aligned against the left or top edge of their container cells.</li>
  <li><em>Uniform Optical 32px Icon Sizing:</em> Harmonized all 5 sub-button icons (Export CD, Rewind 15s, Pause/Play, Stop square, and Fast Forward 15s) to uniform 32px pixel size with matching visual weight and updated the Stop icon geometry to a 14×14 rounded square (rx=2.5). <em>Reason:</em> Resolves visual discrepancies where Pause was disproportionately large (45px) and Stop was tiny (16px), creating a cohesive, professional aesthetic.</li>
  <li><em>Complete Golden Yellow Icon Palette (#fee14d):</em> Styled the Rewind, Pause, Play, Stop, and Forward icons in signature golden yellow (#fee14d) against the deep black circular background, while rendering the bundled Export Audio CD icon in crisp full fidelity. <em>Reason:</em> Establishes strong brand consistency with the ReadAloud megaphone application identity and ensures maximum legibility.</li>
  <li><em>Sub-Button Circular Hover Halos &amp; Tactile Bounce Animations:</em> Added subtle translucent circular hover halos (rgba(255, 255, 255, 0.18)) and click bounce scaling animations (.icon-bounce, scale(0.85)) on all sub-buttons. <em>Reason:</em> Gives immediate, polished tactile feedback when hovering and clicking buttons in the expanded cross layout.</li>
  <li><em>Dynamic Icon State Machine (Speaker ➔ Pause ➔ Play ➔ Speaker):</em> The bubble center icon dynamically flips to a pause icon (media-playback-pause-symbolic) when playback starts, transitions to a play icon (media-playback-start-symbolic) when paused, and returns to the speaker app icon (im.zackarious.ReadAloud) when playback finishes or stop is clicked. <em>Reason:</em> Provides instantaneous visual indication of playback state directly on the desktop companion widget.</li>
  <li><em>3D Flip Transition Animation (.icon-flip):</em> Maintained CSS 3D Y-axis rotation (rotateY(180deg)) and scaling transitions (scale(0.75)) when transitioning between speaker, pause, and play icons. <em>Reason:</em> Delivers an engaging, tactile visual flip effect that feels responsive and polished.</li>
</ul>

<p><em>Version 1.6 - (15 September 2026)</em></p>
<p>Version 1.6 introduces dedicated Wayland window management integration for KDE Plasma 6 to automatically keep the Quick Listener bubble above other windows, resolves active-window focus conflicts when typing in the text editor, expands the floating Quick Listener bubble size by 25% with a mathematically circular profile, redesigns the bubble visual theme to a sleek high-contrast black fill with crisp white border and centered speaker icon with all outer shading removed, and increases default startup window height by 200px (700×700), supported by 97 automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Immediate Script Unlink in KWin Keep-Above Initialization:</em> Removed immediate os.unlink() deletion of the temporary KWin ECMAScript file. <em>Reason:</em> In KDE Plasma 6 on Wayland, KWin parses and executes script files asynchronously; immediately unlinking the temporary file caused KWin 6's script engine to fail with a "Could not open script file" error, preventing automatic keep-above window rules from being registered.</li>
  <li><em>Global /Scripting start DBus Invocation on KDE Plasma 6:</em> Removed calling the global /Scripting start DBus method. <em>Reason:</em> In KDE Plasma 6, /Scripting start is a legacy no-op when other scripts are already registered; executing run() directly on the loaded script object (/Scripting/Script{id}) guarantees script execution.</li>
  <li><em>Outer Drop-Shadow and Box Shading on Quick Listener:</em> Removed the fuzzy outer box-shadow and blur shading surrounding the floating Quick Listener bubble (.listener-bubble-box). <em>Reason:</em> Eliminates visual noise and halo artifacts, producing a crisp, clean aesthetic that integrates seamlessly against light and dark desktop wallpapers alike.</li>
  <li><em>Fixed Pixel Border-Radius on Listener Bubble:</em> Removed static pixel-based border rounding in favor of border-radius: 50%. <em>Reason:</em> Ensures the bubble remains a mathematically perfect circle regardless of container padding, scaling, or display DPI.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>KDE Plasma 6 / KWin Wayland Dedicated Script Object Runner:</em> Added capture of the integer script ID from loadScript and direct execution of org.kde.kwin.Script.run() on DBus path /Scripting/Script{id}, guarded by isScriptLoaded() with a persistent /tmp/kwin_readaloud_keepabove.js script file. <em>Reason:</em> Guarantees that the floating Quick Listener automatically stays above all windows (including full-screen and maximized applications like Firefox) on KDE Plasma 6 Wayland without requiring the user to manually right-click and set "Keep above other windows".</li>
  <li><em>Active-Window Focus &amp; Selection Guard:</em> Added an active-window check (main_window.is_active()) to the bubble's periodic keep-above timer to suppress present() while the main application window is active. <em>Reason:</em> Resolves an input conflict where typing or selecting text in the editor was unselected every two seconds by GTK window presentation calls.</li>
  <li><em>Mathematically Centered Speaker Icon:</em> Added precise zero-margin center alignment rules for the megaphone speaker icon within the circular listener bubble container. <em>Reason:</em> Eliminates visual asymmetry and ensures the speaker icon sits perfectly dead-center within the circular bubble frame.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Extended Default Startup Window Height (+200px, 700×700):</em> Updated default window dimensions in window.ui and recompiled readaloud.gresource to increase the initial startup window height from 500px to 700px. <em>Reason:</em> Provides an expansive, square 700×700 editing canvas for multi-paragraph reading and viewing upon application launch without vertical cramping.</li>
  <li><em>Automated Test Suite Expansion &amp; Validation (97 Tests Passing):</em> Updated tests/test_bubble.py and tests/test_system_integrity.py to validate 72px bubble dimensions, 45px icon scaling, 50% border radius, 700px default window height, and active-window focus preservation during keep-above cycles. <em>Reason:</em> Guarantees high stability and automated regression prevention across all window managers and desktop environments.</li>
  <li><em>KWin DBus Keep-Above Script Logic:</em> Updated the embedded KWin ECMAScript to monitor window addition events (workspace.windowAdded) and re-apply keepAbove = true dynamically to the ReadAloud floating listener. <em>Reason:</em> Ensures newly opened or fullscreen windows cannot eclipse the floating listener bubble during active desktop sessions.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>25% Quick Listener Bubble Size Increase (72×72px):</em> Enlarged the floating listener bubble diameter from 58px to 72px, paired with a proportionally scaled 45px megaphone speaker icon. <em>Reason:</em> Improves visual prominence and creates a larger, more accessible click and drag target on modern high-resolution displays.</li>
  <li><em>High-Contrast Monochrome Bubble Palette:</em> Redesigned the Quick Listener bubble with a solid black background (#000000), a crisp 2px solid white border (#ffffff), and a pure white megaphone icon. <em>Reason:</em> Delivers striking visual contrast and high legibility across any desktop wallpaper or application window.</li>
  <li><em>True 50% Circular Bubble Profile:</em> Applied border-radius: 50% to the bubble container. <em>Reason:</em> Replaces approximate rounded corners with a geometrically perfect circle.</li>
  <li><em>Enlarged 700×700 Main Document Window:</em> Scaled the primary application window to 700×700 pixels on startup. <em>Reason:</em> Eliminates cramped vertical viewing space and allows users to read and edit substantial text without immediate scrolling.</li>
</ul>

<p><em>Version 1.5 - (08 September 2026)</em></p>
<p>Version 1.5 introduces a floating desktop listener bubble icon for instant one-click playback of highlighted text from any application, a full-featured tabbed document system, multi-tab batch audio export with live progress counters, window close audio export safeguards with tab-specific options, instant playback audio caching for unedited text, fixed per-model acoustic pitches across all 35 Piper neural voice models, active selection checkmarks in dropdown menus, and a modern rounded word highlight with 2x padding and 10px border radius, supported by automated unit tests.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Pitch Control UI and Manual Adjustment Slider:</em> Removed the pitch button, popup menu, and slider from the bottom toolbar. <em>Reason:</em> Each voice model has an optimal acoustic frequency; replacing manual pitch sliders with fixed, curated per-model pitches prevents voice distortion and eliminates clutter from the toolbar.</li>
  <li><em>Truncated Text in Dropdown Popup Menus:</em> Removed character caps and ellipsis truncation from popup list items in both the voice model and language dropdowns. <em>Reason:</em> Ensures users can read complete model names, accents, and quality descriptions when choosing voices rather than truncated snippets.</li>
  <li><em>Hard-Edged Rectangular Word Highlighting:</em> Removed the 0px radius, 0-padding rectangular background highlight on active words during playback. <em>Reason:</em> The harsh rectangular box crowded characters; replacing it with a 10px rounded pill with 2x padding produces a smoother, more legible reading experience.</li>
  <li><em>Flickering Modal Re-creation in Batch Audio Export:</em> Removed destroying and re-instantiating the loading HUD dialog between sequential files during multi-tab audio export. <em>Reason:</em> Rapidly tearing down and creating modal dialogs caused severe visual screen flicker; preserving the HUD continuously ensures a smooth, non-disruptive export experience.</li>
  <li><em>Unprompted Window Closure on Exit:</em> Removed immediate silent exit on window close when tabs contain unexported text content. <em>Reason:</em> Exiting without checking for unexported audio risked accidental data loss; prompting users with export choices safeguards synthesized audio work.</li>
  <li><em>Unhandled File Chooser Cancellation Errors:</em> Removed unhandled GLib.GError exceptions when dismissing open and save text file dialogs. <em>Reason:</em> Dismissing or pressing Escape on file dialogs is normal user behavior; trapping cancellations cleanly prevents unhandled exception tracebacks in the terminal.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Standard Playback, Export &amp; Speed Keyboard Shortcuts:</em> Added Ctrl + P to Play/Pause, Ctrl + E to Save Audio to file, Ctrl + Up to increase speaking speed by 0.1, and Ctrl + Down to decrease speaking speed by 0.1, with dedicated application action accelerators (win.play-audio, win.save-audio-as, win.speed-up, win.speed-down). <em>Reason:</em> Provides effortless, hands-on-keyboard control over core speech playback, speed adjustment, and audio saving workflows without needing mouse navigation.</li>
  <li><em>Hardened File Dialog &amp; I/O Error Handling:</em> Added graceful exception handling across open and save dialog dismissals, missing/unreadable files with Latin-1 encoding fallback, and filesystem write errors with user-friendly error banners. <em>Reason:</em> Prevents unhandled Gio GError crashes when users dismiss file choosers or select unreadable/protected files.</li>
  <li><em>Playback Stop Precedence over Buffer Validation:</em> Added immediate stop handling in the Read/Stop button handler so clicking Stop when text buffer is blank or cleared stops playback directly rather than popping up a "No text to read" error. <em>Reason:</em> Guarantees users can always reliably stop ongoing audio playback regardless of changes to the text buffer.</li>
  <li><em>Synthesized Audio Playback Caching &amp; Instant Replay:</em> Added playback audio caching so stopping playback before completion and pressing Play again instantly replays the existing synthesized audio from the start without re-running Piper neural synthesis if text and speech parameters have not changed. <em>Reason:</em> Eliminates unnecessary synthesis wait times and CPU spikes when users pause, stop, and restart listening to unedited text.</li>
  <li><em>Batch Audio Export Progress Counter:</em> Added live progress feedback in the speech generation loading HUD showing the active file index and total files count (e.g. "Generating file 1 of 30"). <em>Reason:</em> Eliminates guesswork during multi-file operations by informing users of exact batch progress and remaining file count.</li>
  <li><em>Window Close Audio Export Safeguard Dialog:</em> Added confirmation dialog when clicking the Close button or pressing Ctrl + Q with unexported audio files, offering to export the current tab, export all tabs, close without exporting, or cancel. <em>Reason:</em> Prevents accidental loss of audio work upon exiting while allowing users to export single or multiple documents in one seamless flow.</li>
  <li><em>Per-Tab Audio Export State Tracking:</em> Added intelligent export tracking per tab that monitors audio generation and marks tabs unexported if buffer text is modified. <em>Reason:</em> Avoids redundant export prompts for already saved or empty tabs while ensuring edited speech content is never lost.</li>
  <li><em>Document Tab System:</em> Added full multi-tab document editing using AdwTabBar and AdwTabView with an inline add tab (+) button and Ctrl + T shortcut. <em>Reason:</em> Enables users to open, write, and manage multiple texts simultaneously without having to overwrite active documents.</li>
  <li><em>Tab Close Export Safeguard Dialog:</em> Added confirmation dialog when closing tabs with unsaved content, offering to export audio, export text, close without exporting, or cancel. <em>Reason:</em> Protects user work from accidental closure while making speech and text export effortlessly accessible.</li>
  <li><em>Batch Multi-Tab Audio Export:</em> Added prompt when clicking Save Audio with multiple open tabs to export all tabs or just the active tab. <em>Reason:</em> Allows users to export multi-chapter documents or notes into audio files in a single batch operation into a chosen folder.</li>
  <li><em>Fixed Pitch Presets for All 35 Piper Models:</em> Added curated pitch settings for all 35 bundled Piper models (from 0.8 to 1.4) applied across playback, pause/resume, demos, and audio export. <em>Reason:</em> Automatically guarantees optimal voice fidelity for every model without requiring manual trial and error.</li>
  <li><em>Active Selection Checkmark in Language Dropdown:</em> Added checkmark (✓) indicator next to the active language option in the popup list. <em>Reason:</em> Instantly confirms the currently selected language at a glance.</li>
  <li><em>Active Selection Checkmark in Voice Chooser Dropdown:</em> Added checkmark (✓) indicator next to the active voice model in the popup list. <em>Reason:</em> Provides clear visual feedback of the active model selection across extensive voice lists.</li>
  <li><em>Floating Desktop Listener Bubble:</em> Added a borderless, floating listener bubble window that launches automatically alongside ReadAloud and sits in the foreground. Clicking the bubble captures highlighted text selections from any application via the primary selection clipboard (with clipboard fallback), creates a new document tab in ReadAloud, and immediately starts audio playback with visual feedback. <em>Reason:</em> Provides effortless, one-click text-to-speech for text selected anywhere on the desktop across all applications without requiring manual copy-pasting.</li>
  <li><em>Expanded Automated Test Suite:</em> Added comprehensive test coverage for the floating listener bubble, document tabs, batch audio export, audio caching, and application lifecycle management. <em>Reason:</em> Prevents regressions and guarantees robust behavior across multi-window and clipboard interactions.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Batch Export Tab Audio Cache Assignment:</em> Updated multi-tab batch audio export to assign each completed synthesis reader to its respective tab. <em>Reason:</em> Enables tabs exported in a batch to immediately replay audio without redundant re-synthesis if the user switches to them.</li>
  <li><em>Word Highlight Offset Type Validation:</em> Updated playback position evaluation in highlight tracking to explicitly verify numeric types before boundary checks. <em>Reason:</em> Guards against potential TypeError runtime errors if non-numeric offsets are encountered.</li>
  <li><em>Standard Keyboard Shortcuts for File Actions (Ctrl + O, Ctrl + S):</em> Added Ctrl + O for Open Text File and Ctrl + S for Save Text to File, registered standard action accelerators, and documented them in the Shortcuts Help Overlay. <em>Reason:</em> Conforms to standard desktop conventions and accelerates document editing workflows.</li>
  <li><em>Per-Tab Audio Cache Persistence on Tab Switch:</em> Updated active tab navigation to preserve each document tab's synthesized audio reader and cleanly release temporary audio files on tab or window closure. <em>Reason:</em> Allows users to switch between open tabs and immediately replay audio without redundant synthesis, while preventing orphaned temporary files on disk.</li>
  <li><em>Version Date to 08 September 2026:</em> Updated application release date to 08 September 2026 across UI, About window, and metainfo metadata. <em>Reason:</em> Reflects today's release with audio export progress indicators, window exit safeguards, and system integrity hardening.</li>
  <li><em>Reader Dialog Lifecycle Control (hide_dialog_on_complete):</em> Updated Reader speech synthesis to accept hide_dialog_on_complete (default True, set False for batch exports). <em>Reason:</em> Gives callers explicit control over progress dialog persistence across sequential synthesis operations.</li>
  <li><em>Application Quit Action Routing (Ctrl + Q):</em> Updated app.quit to route through active window close(). <em>Reason:</em> Guarantees keyboard shortcut exit triggers the unexported audio safeguard dialog identically to the title bar Close button.</li>
  <li><em>_setup_dropdown_excerpt() Dynamic Selection Tracking:</em> Updated dropdown factory setup to support dynamic checkmark indicators with proper unbind signal disconnection (notify::selected). <em>Reason:</em> Maintains accurate selection states without leaking event handlers.</li>
  <li><em>Audio Playback Management on Tab Switch:</em> Updated active tab change handler to automatically stop playback and clear highlight marks. <em>Reason:</em> Prevents audio desynchronization and ensures clean state transitions when navigating between documents.</li>
  <li><em>main_text_view Backward-Compatible Property:</em> Updated main_text_view to dynamically return the active tab's text view. <em>Reason:</em> Seamlessly preserves compatibility with all existing methods and tests while supporting multi-tab architecture.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Keyboard Shortcuts Help Overlay (Playback &amp; File Groups):</em> Added dedicated "Playback" group in the Shortcuts Help Overlay documenting Play/Pause (Ctrl + P / F5), Stop Playback (Escape), and Speed Adjustments (Ctrl + Up / Down), alongside Save Audio to File (Ctrl + E) in the File group. <em>Reason:</em> Makes speech control and audio saving keybindings transparently visible and discoverable within the application UI.</li>
  <li><em>Loading HUD Batch Progress Label (.batch-label):</em> Added styled semi-bold label (105% font size, white text) in the translucent floating HUD displaying "Generating file X of Y". <em>Reason:</em> Delivers clear, prominent visual feedback of batch synthesis progress without crowding the time-remaining status label.</li>
  <li><em>Close Safeguard Dialog Response Styling:</em> Styled "Close Without Exporting" with destructive red styling and "All Tabs" with suggested blue accent. <em>Reason:</em> Conforms to GNOME Human Interface Guidelines to prevent accidental data loss and visually emphasize the primary action.</li>
  <li><em>AdwTabBar Document Tabs:</em> Added an elegant native tab bar with individual close buttons, titles, and an add tab button. <em>Reason:</em> Provides intuitive, native multi-document navigation adhering to GNOME Human Interface Guidelines.</li>
  <li><em>Streamlined Bottom Toolbar:</em> Cleaned up the bottom toolbar layout following the removal of pitch controls. <em>Reason:</em> Gives language, voice, speed, and playback buttons balanced spacing and prominence.</li>
  <li><em>Dropdown Popup Selection Checkmarks:</em> Rendered bold checkmarks (✓) next to active items in Language and Voice dropdown lists. <em>Reason:</em> Enhances usability by making the current selection immediately obvious.</li>
  <li><em>Modern 10px Rounded Word Highlight Pill:</em> Replaced rectangular text background with a 10px border radius pill with 2x padding and black text foreground. <em>Reason:</em> Conforms to contemporary design standards and provides smooth visual tracking.</li>
  <li><em>Fixed New Tab Button Icon:</em> Replaced missing tab-new-symbolic icon with standard list-add-symbolic (+). <em>Reason:</em> Fixes broken image placeholder on the tab bar across all platforms.</li>
</ul>

<p><em>Version 1.4 - (06 September 2026) — Public Release</em></p>
<p>This version marks ReadAloud's first public release milestone. All known stability regressions have been resolved, licensing and attribution documentation is now fully in-app, export workflows are streamlined with contextual file naming, button styling and dimensions have been unified across the window with borderless hover feedback, voice quality tiers and multi-speaker architecture are documented in the application description, and the user interface is polished and regression-tested across 21 automated unit tests. ReadAloud is ready for open-source distribution.</p>

<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Solid Pill and Suggested-Action Styling on Bottom Buttons:</em> Removed the permanent solid pill shape (pill class) and blue accent fill (suggested-action class) from the bottom-right playback and export controls. <em>Reason:</em> The heavy solid pill styling caused visual clutter and felt disconnected from the clean, flat style of the header controls; replacing them with flat action buttons creates an elegant, unified interface.</li>
  <li><em>Lined Border Outlines on Button Hover:</em> Removed the 1px solid border outline from button hover and active states across the interface. <em>Reason:</em> The rigid border line felt distracting and dated; removing the border leaves a soft, modern translucent background highlight (alpha(currentColor, 0.10)) consistent with modern GNOME HIG.</li>
  <li><em>Generic Desktop Icons on Action Buttons:</em> Removed generic system icons (document-open, document-save, and media-floppy-symbolic) from the top-left toolbar and export controls. <em>Reason:</em> Generic desktop icons lacked distinct visual identity, suffered from inconsistent scaling across themes, and did not clearly distinguish between saving text and exporting synthesized audio.</li>
  <li><em>Static "audio.mp3" Default Export Name:</em> Removed the hardcoded static default filename "audio.mp3" from the audio export dialog. <em>Reason:</em> Required users to manually type descriptive file names each time; replacing it with an automated date-and-content title format ensures exported files are immediately identifiable and organized chronologically.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Voice Quality Levels &amp; Multi-Speaker Architecture in Application Description:</em> Added comprehensive technical documentation explaining Piper's 4 voice quality tiers (x_low, low, medium, high with audio sample rates and parameter counts) and multi-speaker neural models directly inside the in-app Application Description sub-page and README. <em>Reason:</em> Educates users on the technical distinctions between bundled voices, helping them make informed choices regarding audio fidelity and multi-speaker trade-offs.</li>
  <li><em>Flaticon CD Audio Export Icon &amp; Full Legal Attribution:</em> Added custom CD audio disc icon from Flaticon for the Save Audio button, with complete open-source attribution in the Licensing and Copyright Information page and interactive hyperlink in the Credits section. <em>Reason:</em> Clearly differentiates exporting audio from saving text files using an unmistakable media symbol, while fulfilling open-source licensing requirements.</li>
  <li><em>Megaphone Application Icon:</em> Added vibrant new megaphone vector application icon and symbolic icon. <em>Reason:</em> Immediately conveys speech synthesis and vocal reading across desktop environments, docks, and application launchers.</li>
  <li><em>Contextual Audio Export Filename Generation:</em> Added dynamic default export filenames formatted as "[Day] [Month] [Year] - [First 5 Words].mp3" (e.g. "06 Sep 2026 - Hello World.mp3") with automatic sanitization of illegal filesystem characters and safe length limits. <em>Reason:</em> Automatically creates organized, readable, and chronologically sorted audio titles directly derived from the user's active text without requiring manual typing.</li>
  <li><em>Dedicated Licensing and Copyright Information Page:</em> Added a dedicated "Licensing and Copyright Information" sub-page inside About ReadAloud. <em>Reason:</em> Provides transparent, legally accurate attribution for the GPLv3 core application (ReadAloud as a fork of Parolu by wbernard), MIT-licensed Piper voice model files, Asam Munir UI icons (SVGRepo), and Flaticon CD icon, including full verbatim license texts and plain-English user rights summaries.</li>
  <li><em>Interactive Web Hyperlinks in Credits Sub-Page:</em> Added clickable URL subtitle rows for all project authors, designers, voice repositories, and license sources in the About dialog's Credits section. <em>Reason:</em> Allows users to navigate directly to upstream projects, portfolios, and license terms with a single click.</li>
  <li><em>Voice Change Applied on Resume After Pause During Synthesis:</em> Added support for correctly detecting and applying voice model changes when the user clicks Pause before synthesis has completed (i.e. before the GStreamer pipeline is created). <em>Reason:</em> A regression caused pause_audio() to return False when no pipeline existed yet, leaving is_paused = False. The fix introduces _is_paused and _stopped intent flags on Reader so pause intent is always recorded correctly regardless of synthesis state.</li>
  <li><em>Expanded Automated Unit Test Suite (21 Tests):</em> Added regression tests covering export filename formatting and sanitization, legal attribution links, and credits page hyperlinks, bringing the automated test suite to 21 tests (21/21 passing). <em>Reason:</em> Guarantees high stability and automated regression prevention across all filename generation, playback, and documentation flows.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Fine-Tuned 10% Icon Proportions for Visual Breathing Room:</em> Reduced action icon sizes by 10% across the interface (top-left header icons scaled from 32px to 29px; bottom playback icons scaled from 28px to 25px; CD export icon scaled from 30px to 27px). <em>Reason:</em> Eliminates tight edge crowding inside button frames, giving icons well-balanced margins and comfortable visual breathing room.</li>
  <li><em>Standardized Button Dimensions (48px × 42px):</em> Updated bottom-right playback and export buttons from wide 65px pills to 48px × 42px rectangles matching the top-left header buttons. <em>Reason:</em> Creates harmonious geometric consistency between top header controls and bottom toolbar controls across the entire window layout.</li>
  <li><em>SVGRepo Author Link in Legal Page:</em> Updated the SVGRepo link to point directly to the author collection (https://www.svgrepo.com/author/Asam%20Munir/). <em>Reason:</em> Provides accurate, specific attribution directly to the artist's repository collection.</li>
  <li><em>Custom Action Icons Standardized to 1:1 Square Canvas:</em> Standardized action SVGs (folder-open, disk, and cd) to exact 1:1 square dimensions with zero exterior margins. <em>Reason:</em> Meets strict Flatpak and AppStream icon validation specifications while ensuring graphics scale up to fill button frames without unwanted margin shrinking.</li>
  <li><em>Dynamic Icon Size Preservation (_set_button_icon):</em> Added a robust icon update method that maintains enlarged icon dimensions across dynamic button state transitions. <em>Reason:</em> Prevents GTK from resetting button icons to default 16px when toggling between Play, Pause, Resume, and Stop states.</li>
  <li><em>pause_audio() Pause Intent Tracking:</em> Updated to set _is_paused = True and return True even when no GStreamer pipeline exists yet. <em>Reason:</em> Ensures window.is_paused is always set correctly when the user pauses during synthesis, enabling the voice-change-on-resume path to trigger reliably.</li>
  <li><em>resume_audio() Intent Clearing:</em> Updated to clear _is_paused = False on resume. <em>Reason:</em> Prevents the pipeline from starting in the wrong PAUSED state if synthesis completes after the user has already resumed.</li>
  <li><em>_play_audio_file_async() Synthesis Guard and Pause-State Start:</em> Updated to bail immediately if _stopped is set, and to start the GStreamer pipeline in PAUSED state when _is_paused is True. <em>Reason:</em> Prevents a replaced Reader from playing audio on behalf of an old voice, and honours pause intent during synthesis.</li>
  <li><em>stop_audio() Bus Signal Watch Cleanup:</em> Updated to set _stopped = True, clear _is_paused, and remove the GStreamer bus signal watch before pipeline teardown. <em>Reason:</em> Eliminates ghost EOS callbacks that prematurely interrupted newly switched voices.</li>
  <li><em>_on_gst_message() Reader Identity Check:</em> Updated EOS and error handlers to verify self.window.reader is self before calling window.stop_playback(). <em>Reason:</em> Prevents a replaced Reader's completion callback from stopping the new Reader's playback.</li>
  <li><em>GTK Thread-Safety Fix (set_sensitive):</em> Updated set_sensitive(True) in the synthesis completion block to be dispatched via GLib.idle_add. <em>Reason:</em> Direct GTK widget operations from background threads violate GTK4's single-threaded model and can cause silent failures or deadlocks.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Unified Transparent Action Buttons with Borderless Hover:</em> Styled bottom-right playback and export buttons identically to the top-left header buttons, featuring transparent idle backgrounds and a smooth translucent background fill on hover without harsh border lines. <em>Reason:</em> Establishes visual harmony between top and bottom controls and conforms to modern GNOME HIG design patterns.</li>
  <li><em>10% Scaled Icon Dimensions (29px Header, 25px/27px Toolbar):</em> Refined icon rendering sizes across all buttons. <em>Reason:</em> Delivers an aesthetically pleasing balance between icon prominence and button padding.</li>
  <li><em>Megaphone Application Icon:</em> Replaced the application icon and symbolic icon with a vibrant megaphone graphic. <em>Reason:</em> Immediately conveys speech synthesis and vocal reading across desktop environments and application launchers.</li>
  <li><em>Dedicated CD Audio Export Icon:</em> Replaced the floppy disk audio export icon with a dedicated CD audio disc icon from Flaticon. <em>Reason:</em> Differentiates saving audio recordings from saving text files with an unmistakable, intuitive media symbol.</li>
  <li><em>Custom Asam Munir Disk and Folder Icons:</em> Replaced monochrome icons with custom yellow folder and green floppy disk vector designs. <em>Reason:</em> Greatly enhances visual clarity, charm, and immediate recognition of file operations.</li>
  <li><em>Aligned Header Button Heights (42px):</em> Unified heights of Open, Save Text, and Test Demo Selector buttons to 42px. <em>Reason:</em> Maintains harmonious height and vertical alignment across the header bar.</li>
  <li><em>Voice Chooser Popup Full-Text Factory:</em> Fixed _setup_dropdown_excerpt() to always create a dedicated full-text list factory for the voice chooser dropdown popup. <em>Reason:</em> Displays full, untruncated voice names in the popup list while keeping the closed button neatly abbreviated.</li>
</ul>

<p><em>Version 1.3 - (05 September 2026)</em></p>


<p><em>Features and Fixes Removed:</em></p>
<ul>
  <li><em>Standalone Starred Icon for Demos:</em> Removed the generic star icon (starred-symbolic) on the header bar demo button. <em>Reason:</em> A generic star icon lacked immediate clarity for users; replacing it with an explicit text label "Test Demo Selector" instantly communicates its purpose and invites exploration.</li>
  <li><em>Ambiguous Model Variant Fallback:</em> Removed ambiguous voice matching by voice prefix alone in speech synthesis and selection. <em>Reason:</em> When multiple quality variants of a voice exist (such as Low, Medium, and High), prefix matching caused lower-quality models to shadow higher-quality models; matching exact model IDs ensures the chosen quality variant is strictly honored.</li>
  <li><em>Static Playback Pipeline on Resume:</em> Removed the static GStreamer pipeline resume behavior that unconditionally played pre-synthesized audio when unpausing. <em>Reason:</em> Prevented users from changing the voice model, language, pitch, or speed while playback was paused, as resuming merely unpaused the old audio stream.</li>
  <li><em>Single-Export Limitation &amp; Coupled Pipeline:</em> Removed the monolithic speech synthesis pipeline that restricted saving audio to only once per session. <em>Reason:</em> Pipeline file locks and unreleased GStreamer bus resources caused subsequent exports to fail; decoupling synthesis from playback enables unlimited sequential saves.</li>
  <li><em>Stale Playback Audio Caching:</em> Removed saving from playback cache. <em>Reason:</em> Editing text in the input box and clicking Save previously saved old audio from previous playback; dynamic synthesis ensures active text buffer is always exported.</li>
  <li><em>Uncompressed WAV as Default Format:</em> Removed WAV as the sole/default export format. <em>Reason:</em> WAV produces enormous uncompressed PCM files (~10x-20x larger); voice notes and audiobooks require efficient, shareable formats.</li>
  <li><em>Intrusive Modal Loading Dialog:</em> Removed the heavy modal dialog with window borders, titlebar, and indeterminate progress bar. <em>Reason:</em> Blocked user view and disrupted workflow during background synthesis.</li>
  <li><em>Overly Long Dropdown Labels:</em> Removed full country names ("English (United Kingdom)" and "English (United States)"). <em>Reason:</em> Full names cluttered the toolbar and crowded playback buttons.</li>
  <li><em>Unclipped Dropdown Button Text:</em> Removed 76-character unclipped labels on closed toolbar dropdown buttons. <em>Reason:</em> Long voice descriptions severely stretched the top toolbar and distorted the window layout.</li>
  <li><em>Generic Document Save Icon:</em> Removed the generic document-save icon. <em>Reason:</em> Did not clearly convey immediate audio file export compared to the classic disk symbol.</li>
</ul>

<p><em>Features and Fixes Added:</em></p>
<ul>
  <li><em>Curated Preset Voice Demos (Demos 1, 2, 3):</em> Added built-in preset voice demos showcasing different voices, languages, pitches, speeds, and content: Demo 1: English (UK), Jenny Dioco Voice (en_GB-jenny_dioco-medium), pitch 1.3, speed 0.5 (William Wallace Betrayal). Demo 2: English (UK), Northern English Male (en_GB-northern_english_male-medium), pitch 1.3, speed 0.5 (Death of King Henry VIII). Demo 3: English (US), Joe Voice Medium Quality (en_US-joe-medium), pitch 1.2, speed 0.6 (Indigenous Peoples of the Americas). <em>Reason:</em> Enables users to instantly experience and test high quality Piper neural voice synthesis across varied accents and speech rates with one click.</li>
  <li><em>Overwrite Warning Protection Dialog:</em> Added an Adw.AlertDialog confirmation prompt when selecting a demo with existing text in the input box. <em>Reason:</em> Prevents accidental loss of user-written text while allowing immediate one-click loading if the text box is empty.</li>
  <li><em>Automatic Demo Settings and Playback:</em> Added automatic configuration of language, voice, pitch, speed, and immediate speech playback upon selecting a demo. <em>Reason:</em> Delivers an effortless, instant demo listening experience without requiring manual button clicks or control tweaking.</li>
  <li><em>Loading Window Visual Progress Bar:</em> Added a modern progress bar (Gtk.ProgressBar) inside the speech generation HUD. <em>Reason:</em> Gives clear visual feedback on the exact percentage of speech synthesis completed rather than an indeterminate spinner alone.</li>
  <li><em>Dynamic Time Remaining Countdown:</em> Added real-time calculation and display of remaining synthesis time (e.g. Generating audio: 45% (~3s remaining)). <em>Reason:</em> Informs the user of expected wait times during multi-sentence speech generation.</li>
  <li><em>Demo Menu Integration:</em> Added a dedicated "Test Demo Selector" button in the header bar and a "Preset Demos" submenu in the hamburger menu. <em>Reason:</em> Ensures presets are highly accessible and discoverable from anywhere in the interface.</li>
  <li><em>Dynamic Mid-Stream Voice Switching on Resume:</em> Added ability to change voice model, language, pitch, or speed while paused, seamlessly re-synthesizing and resuming playback from the paused word using the newly selected voice. <em>Reason:</em> Resolves the bug where changing voice models during pause had no effect when resuming playback.</li>
  <li><em>Text-Anchored Position Tracking (pause_resume_mark):</em> Added Gtk.TextMark anchoring to the exact character offset of the paused word. <em>Reason:</em> Guarantees playback resumes accurately at the right word even if text before or after the paused word is edited while paused.</li>
  <li><em>Keyboard Playback Shortcuts (F5 &amp; Escape):</em> Added F5 to toggle Play/Pause and Escape to stop playback. <em>Reason:</em> Provides immediate hands-on-keyboard audio control without requiring mouse interaction.</li>
  <li><em>Voice-Optimized MP3 Export (64 kbps Mono):</em> Added native GStreamer MP3 encoding with descriptive format options. <em>Reason:</em> Delivers clear spoken-word audio with ~95% file size reduction, ideal for voice notes, podcasts, and portable listening.</li>
  <li><em>Descriptive Quality Explanations in Save Dialog:</em> Added explicit format explanations in file chooser dialog ("MP3 Audio — 64 kbps Mono, Voice/Podcast Optimized (*.mp3)" and "WAV Audio — Lossless Uncompressed PCM (*.wav)"). <em>Reason:</em> Helps users make informed decisions about format and file size tradeoffs without technical confusion.</li>
  <li><em>Audio Playback Controls (Pause &amp; Resume):</em> Added dedicated Pause and Resume controls for speech playback. <em>Reason:</em> Allows users to pause and resume listening without losing text position.</li>
  <li><em>Real-Time Word Highlighting:</em> Added synchronized yellow word-by-word highlighting with automatic view scrolling. <em>Reason:</em> Provides a clear visual tracking aid following speech progression in real time.</li>
  <li><em>Read from Cursor or Selection:</em> Added synthesis starting cleanly from active cursor position or highlighted text. <em>Reason:</em> Allows users to listen to specific paragraphs or resume reading without starting from beginning.</li>
  <li><em>Dynamic Text Zoom:</em> Added font scaling (70% to 300%) via Ctrl +, Ctrl -, Ctrl 0, and Ctrl + Mouse Scroll Wheel. <em>Reason:</em> Improves reading comfort and accessibility across different display sizes.</li>
  <li><em>Dedicated Change Logs Page:</em> Added native Change Logs subpage inside About ReadAloud and direct menu action. <em>Reason:</em> Provides transparent, structured release notes and feature history in the app.</li>
</ul>

<p><em>Features and Fixes Updated:</em></p>
<ul>
  <li><em>Version Number to 1.3:</em> Updated application version by 0.1 to Version 1.3 with release date formatting across UI, Meson, metainfo, and documentation. <em>Reason:</em> Reflects the addition of preset demos, overwrite confirmation safety, loading progress bar with countdown, and header bar demo controls.</li>
  <li><em>Voice Selection by Exact Model ID:</em> Updated voice chooser and reader communication to use full model IDs (e.g. en_US-joe-medium, en_US-ryan-high) instead of raw voice names. <em>Reason:</em> Accurately differentiates between different quality variants (Low, Medium, High) of the same voice.</li>
  <li><em>Demo 3 Voice Configuration:</em> Updated Demo 3 from Ryan High Quality to Joe Voice Medium Quality (en_US-joe-medium) with pitch 1.2 and speed 0.6. <em>Reason:</em> User requested Joe voice preset for better demonstration of US English narration.</li>
  <li><em>Expanded Unit Test Suite:</em> Added tests/test_demos.py covering demo presets, overwrite logic, auto-playback, model resolution, and wait dialog progress updates (10/10 tests passing). <em>Reason:</em> Guarantees high stability and automated regression detection across all new preset and loading features.</li>
  <li><em>Language Dropdown Options:</em> Updated dropdown labels to "English (UK)" and "English (US)" with automatic migration for existing settings. <em>Reason:</em> Standardizes abbreviations while seamlessly preserving saved user preferences.</li>
  <li><em>Model Discovery Scanner:</em> Updated directory scanning to safely handle read-only environments and support local development models. <em>Reason:</em> Prevents startup failures in sandboxed systems and simplifies testing.</li>
</ul>

<p><em>Visual Changes and UI Updates:</em></p>
<ul>
  <li><em>Header Bar "Test Demo Selector" Button:</em> Replaced the icon-only star button with a prominent text label "Test Demo Selector". <em>Reason:</em> Greatly increases UI clarity and discoverability on desktop displays.</li>
  <li><em>Sleek Loading HUD with Progress Bar &amp; Countdown:</em> Enhanced the translucent floating HUD with an Adw.Spinner, a rounded blue progress bar (Gtk.ProgressBar), and a typography-optimized status label. <em>Reason:</em> Upgrades speech generation from an opaque wait into a polished, modern, and informative visual indicator.</li>
  <li><em>Preset Submenu in Hamburger Menu:</em> Added a structured "Preset Demos" section in the primary menu. <em>Reason:</em> Follows GNOME Human Interface Guidelines for secondary actions while keeping the header bar tidy.</li>
  <li><em>Save Button Disk Icon:</em> Replaced document-save icon with the classic floppy disk icon (media-floppy-symbolic). <em>Reason:</em> The floppy disk is the universally recognized symbol for quick save actions, providing immediate visual affordance.</li>
  <li><em>Dropdown 40-Character Excerpt:</em> Configured closed dropdown buttons to display an excerpt of 40 characters with an ellipsis and full tooltip, while preserving the full text in the dropdown menu. <em>Reason:</em> Keeps toolbar buttons neatly proportioned while still allowing users to read complete voice descriptions in the list.</li>
  <li><em>Immediate Resume Word Highlight:</em> Configured the paused word to highlight immediately when resuming with a new voice. <em>Reason:</em> Provides visual continuity showing users exactly where the newly selected voice will start reading.</li>
  <li><em>Change Log Window Sizing (+150px Width, 600×750):</em> Increased default window width by an additional 150px (from 450×750 to 600×750) and scaled internal clamp limits to 650px. <em>Reason:</em> Provides a wider, more spacious reading canvas for release notes with longer line lengths, optimal paragraph margins, and reduced vertical scrolling.</li>
  <li><em>Modern Transparent Loading HUD:</em> Replaced the old dialog with a borderless, floating on-screen HUD with translucent frosted glass styling and AdwSpinner. <em>Reason:</em> Creates a sleek, non-intrusive visual indicator during speech generation.</li>
</ul>
"""

LICENSING_TEXT = """\
ReadAloud - Licensing and Copyright Information

The ReadAloud application combines core source code with bundled text-to-speech \
data models. Because of this dual composition, the repository utilizes two distinct \
open-source licenses.

1. Core Application: ReadAloud (GPLv3)

ReadAloud is a customized fork of Parolu, originally created by GitHub user wbernard.

Original Software Repository: https://github.com/wbernard/parolu

The core software, including all original Parolu code and all subsequent \
modifications, additions, and scripts created for ReadAloud, is free software \
licensed under the GNU General Public License Version 3 (GPLv3).

What this means for you:

Under the GPLv3, you are completely free to:
  • Use this software for any purpose.
  • Modify the source code to suit your needs.
  • Distribute copies of this software to others.

Under the condition that:

If you distribute modified copies of this software (or use it as part of a larger \
program), you must make your modifications open-source under the exact same GPLv3 \
license, and you must make the complete source code available to whoever receives \
the software.

A full copy of the GPLv3 license text can be found in the LICENSE file located in \
the root of this repository, or online at:
https://www.gnu.org/licenses/gpl-3.0.txt

2. Bundled Voice Models: Piper Voices (MIT License)

The Piper voice model files (.onnx and .onnx.json) bundled with ReadAloud are the \
work of the Piper project contributors and are distributed under the MIT License.

MIT License terms permit you to use, copy, modify, merge, publish, distribute, \
sublicense, and/or sell copies of the voice model files, provided that the original \
copyright notice and this permission notice are included in all copies or substantial \
portions of the files.

Piper Project Repository: https://github.com/rhasspy/piper
Piper Voice Models Repository: https://github.com/rhasspy/piper-voices

────────────────────────────────────────────────────────────────────────

What this means for you:

The MIT License is highly permissive. You can use, modify, and distribute \
these specific .onnx and .json model files freely, provided that you include \
the original copyright notice and license text below.

MIT License Text for Piper Voice Models:

Copyright (c) 2023 Rhasspy / Michael Hansen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

────────────────────────────────────────────────────────────────────────

3. UI Icons Attribution

The following icons used in the ReadAloud interface are used with attribution:

• Asam Munir Collection (SVGRepo):
  - Floppy Disk icon (Save Text File button)
  - Open Folder icon (Open Text File button)

Designer: Asam Munir
Designer Portfolio: https://dribbble.com/asammunir
Source: https://www.svgrepo.com/author/Asam%20Munir/

• CD Audio Export Icon (Flaticon):
  - Compact Disc icon (Save Audio to File button)

Author Website: https://www.flaticon.com/free-icon/cd_6749218?
Source: https://www.flaticon.com/free-icon/cd_6749218

These icons are used with attribution as required. No modifications have been \
made to the original icon designs.
"""

APP_DESCRIPTION = (
    "ReadAloud is a modern, privacy-focused text-to-speech desktop application "
    "crafted with GTK4 and Libadwaita. Powered by the high-performance Piper neural "
    "speech engine, ReadAloud transforms your written text into rich, natural-sounding "
    "audio across diverse voices, accents, pitches, and speeds—complete with synchronized "
    "word highlighting, seamless playback controls, preset demos, and voice-optimized audio export.\n\n"
    "Unlike conventional cloud-based voice assistants and commercial speech tools, ReadAloud "
    "is completely offline. Every syllable is synthesized locally on your own machine using "
    "efficient on-device neural models. ReadAloud requires zero internet connection, contains "
    "no telemetry, and transmits no data to external servers or third parties. Your personal "
    "documents, confidential manuscripts, private notes, and generated recordings remain "
    "entirely private, secure, and under your absolute personal control at all times.\n\n"
    "While I leveraged AI tools like Anti-gravity and Claude to accelerate the development of this "
    "software, the core engineering remains entirely mine apart from any contributions mentioned "
    "such as the language models which are bundled with this software and rightfully credited to "
    "the owners. But, wow, AI allowed me to move much faster, but I still rigorously review the "
    "generated code before shipping. Ultimately, I own the architecture, technical decisions, and "
    "trade-offs—because while AI is excellent at writing code quickly, it doesn't replace a deep "
    "understanding of how the entire system operates. What's truly great is that software is "
    "released under a licence which ensures open-source and that if you take or modify the code "
    "yourself you must again, release it open-source and for free :-)\n\n"
    "ReadAloud is proud to be free and open-source software, licensed under the GNU General "
    "Public License v3.0. There are no subscriptions, no recurring fees, no locked paywalls, "
    "and no artificial daily usage limits. Transparent by design, the entire source code is "
    "openly audited and maintained by the community on GitHub. Whether you are proofreading "
    "drafts, studying long articles, creating audio notes, or enhancing accessibility, "
    "ReadAloud offers an ethical, dependable, and always-accessible speech companion that "
    "forever puts your personal privacy and freedom first.\n\n"
    "Quality\n"
    "Voices are trained at one of 4 \"quality\" levels:\n\n"
    "    x_low - 16Khz audio, 5-7M params\n"
    "    low - 16Khz audio, 15-20M params\n"
    "    medium - 22.05Khz audio, 15-20M params\n"
    "    high - 22.05Khz audio, 28-32M params\n\n"
    "Multi-Speaker\n"
    "Some voices contain multiple speakers, which captures the style of multiple people within a single model.\n"
    "Multi-speaker models can quickly switch between different speakers, but the quality of an individual speaker may be less than a single speaker model.\n\n"
    "Minimum PC Requirements (Basic / Normal Voice Playback)\n\n"
    "• Processor: 1.6 GHz or faster, 2-core processor (x86-64, ARM64, or Apple Silicon with SSE4.2 / NEON)\n"
    "• Operating System: Windows 11, Windows Server 2025, or Windows Server 2022 (Note: Windows 10 support ended in October 2025, though apps may continue to run); Ubuntu 22.04 LTS+, Debian 12+, Fedora 38+; macOS 12 (Monterey) or later\n"
    "• Memory (RAM): 4 GB RAM (or 2 GB minimum available system memory)\n"
    "• Hard Disk Space: 4 GB of available space for application, Piper neural engine, and pre-bundled offline voice models\n"
    "• Display: 1280 x 768 screen resolution\n"
    "• Graphics Card & Drivers: DirectX 11 / OpenGL 3.3 capable GPU (Intel HD Graphics 4000+, AMD Radeon R5/HD 7000+, NVIDIA GeForce 400 series or newer with standard WDDM 1.2+ drivers; Mesa llvmpipe software rasterizer supported as fallback)\n"
    "• Audio Output: Standard audio output device, sound card, or headphone jack (DirectSound / WASAPI on Windows, PulseAudio / PipeWire / ALSA on Linux, CoreAudio on macOS)\n\n"
    "Recommended PC Requirements (High-Quality Voice Models & Batch Synthesis)\n\n"
    "• Processor: 2.5 GHz or faster quad-core (4 cores / 8 threads) or higher (Intel Core i5/i7 8th Gen+, AMD Ryzen 3000+, ARM64 Snapdragon X Elite, Apple Silicon M1/M2/M3/M4) with AVX2 / FMA instruction support\n"
    "• Operating System: Windows 11 64-bit (23H2 or newer), Windows Server 2025; Ubuntu 24.04 LTS, Fedora 40+; macOS 14 (Sonoma) or newer\n"
    "• Memory (RAM): 8 GB RAM or higher for rapid multi-tab processing and uncompressed high-fidelity audio buffers\n"
    "• Hard Disk Space: 8 GB of available space on a solid-state drive (NVMe SSD recommended for instant voice model loading and multi-chapter audio rendering)\n"
    "• Display: 1920 x 1080 (Full HD) or higher resolution\n"
    "• Graphics Card & Drivers: Dedicated or modern integrated GPU with Direct3D 12 / Vulkan / Metal support:\n"
    "    - NVIDIA: GeForce GTX 1050 / RTX 2060 or newer (GeForce Game Ready / Studio Driver 535.xx or later)\n"
    "    - AMD: Radeon RX 5000 / 6000 series or newer (AMD Software: Adrenalin Edition 23.x or later)\n"
    "    - Intel: Intel Iris Xe Graphics, Arc A-Series, or UHD 630+ (Intel Graphics Driver 31.0.101.4000 or newer)\n"
    "    - Apple: Apple Silicon Integrated GPU (M1, M2, M3, M4 with Metal 3)\n"
    "• Audio Output: 24-bit / 48kHz or 96kHz low-latency stereo output device or USB DAC"
)


class AboutReadAloudWindow(Adw.Window):
    """Condensed About ReadAloud window featuring sub-tabs matching GNOME HIG."""

    application_name = GObject.Property(type=str, default='ReadAloud')
    application_icon = GObject.Property(type=str, default='im.zackarious.ReadAloud')
    developer_name = GObject.Property(type=str, default='zackarious')
    version = GObject.Property(type=str, default='Version 1.8.13 - (04 November 2026)')
    website = GObject.Property(type=str, default='https://github.com/Zackarious/ReadAloud')
    issue_url = GObject.Property(type=str, default='https://github.com/Zackarious/ReadAloud/issues')
    support_url = GObject.Property(type=str, default='https://github.com/Zackarious/ReadAloud')
    comments = GObject.Property(type=str, default=APP_DESCRIPTION)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(_("About ReadAloud"))
        self.set_default_size(600, 680)
        self.set_modal(True)

        # Close on Escape key
        esc_controller = Gtk.ShortcutController()
        esc_controller.set_scope(Gtk.ShortcutScope.LOCAL)
        esc_trigger = Gtk.KeyvalTrigger.new(Gdk.KEY_Escape, 0)
        esc_action = Gtk.CallbackAction.new(lambda *_: (self.close(), True)[1])
        esc_shortcut = Gtk.Shortcut.new(esc_trigger, esc_action)
        esc_controller.add_shortcut(esc_shortcut)
        self.add_controller(esc_controller)

        # Main vertical container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.add_css_class("background")
        self.set_content(main_box)

        # HeaderBar with centered StackSwitcher
        self.header_bar = Adw.HeaderBar(show_end_title_buttons=True)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.switcher = Gtk.StackSwitcher(stack=self.stack)
        self.switcher.add_css_class("linked")
        self.header_bar.set_title_widget(self.switcher)
        main_box.append(self.header_bar)

        # Add Stack
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        main_box.append(self.stack)

        # Build 5 sub-tabs
        self.about_page = self._build_about_page()
        self.stack.add_titled(self.about_page, "about", _("About"))

        self.changelogs_page = self._build_changelogs_page()
        self.stack.add_titled(self.changelogs_page, "changelogs", _("Change Logs"))

        self.description_page = self._build_description_page()
        self.stack.add_titled(self.description_page, "description", _("Description"))

        self.credits_page = self._build_credits_page()
        self.stack.add_titled(self.credits_page, "credits", _("Credits"))

        self.legal_page = self._build_legal_page()
        self.stack.add_titled(self.legal_page, "legal", _("Legal"))

        # Configure window controls tooltips (Close button)
        self._set_window_controls_tooltips()
        self.connect("map", lambda *_: self._set_window_controls_tooltips())

    def _set_window_controls_tooltips(self):
        def find_ctrls(widget):
            if isinstance(widget, Gtk.WindowControls):
                c = widget.get_first_child()
                while c:
                    if "close" in c.get_css_classes():
                        c.set_tooltip_text(_("Close"))
                    c = c.get_next_sibling()
            child = widget.get_first_child()
            while child:
                find_ctrls(child)
                child = child.get_next_sibling()
        find_ctrls(self)

    def _build_about_page(self):
        clamp = Adw.Clamp(maximum_size=520, tightening_threshold=420)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.FILL)
        box.set_margin_top(36)
        box.set_margin_bottom(36)
        box.set_margin_start(24)
        box.set_margin_end(24)
        clamp.set_child(box)

        # App Icon
        icon = Gtk.Image.new_from_icon_name("im.zackarious.ReadAloud")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)
        box.append(icon)

        # App Title
        title_label = Gtk.Label(label="ReadAloud")
        title_label.add_css_class("title-1")
        box.append(title_label)

        # Developer Subtitle
        dev_label = Gtk.Label(label=_("By zackarious"))
        dev_label.add_css_class("subtitle")
        dev_label.add_css_class("dim-label")
        box.append(dev_label)

        # Version
        ver_label = Gtk.Label(label="Version 1.8.13 - (04 November 2026)")
        ver_label.add_css_class("caption")
        ver_label.add_css_class("dim-label")
        box.append(ver_label)

        # Tagline / Summary
        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        summary_box.set_margin_top(8)
        summary_box.set_margin_bottom(8)

        sum1 = Gtk.Label(label=_("View, read, and listen to documents offline"))
        sum1.add_css_class("body")
        sum1.set_justify(Gtk.Justification.CENTER)
        sum1.set_wrap(True)
        summary_box.append(sum1)

        sum2 = Gtk.Label(label=_("100% Offline • Free and Open Source • Privacy-First"))
        sum2.add_css_class("caption")
        sum2.add_css_class("dim-label")
        sum2.set_justify(Gtk.Justification.CENTER)
        summary_box.append(sum2)
        box.append(summary_box)

        # Links Box (Website & Issue Tracker)
        links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        links_box.set_halign(Gtk.Align.CENTER)
        links_box.set_margin_top(4)

        website_btn = Gtk.LinkButton.new_with_label(self.website, _("Website"))
        issue_btn = Gtk.LinkButton.new_with_label(self.issue_url, _("Report an Issue"))
        links_box.append(website_btn)
        links_box.append(issue_btn)
        box.append(links_box)

        # Copyright & Disclaimer
        legal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        legal_box.set_margin_top(16)

        c_label = Gtk.Label(label="© 2025-2026 zackarious\nAuthor: Walter Bernard")
        c_label.add_css_class("caption")
        c_label.add_css_class("dim-label")
        c_label.set_justify(Gtk.Justification.CENTER)
        legal_box.append(c_label)

        disclaimer = Gtk.Label(label=_("This program comes with absolutely no warranty.\nSee the Legal tab for details."))
        disclaimer.add_css_class("caption")
        disclaimer.add_css_class("dim-label")
        disclaimer.set_justify(Gtk.Justification.CENTER)
        legal_box.append(disclaimer)

        box.append(legal_box)
        return scroll

    def _build_changelogs_page(self):
        clamp = Adw.Clamp(maximum_size=560, tightening_threshold=460)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(24)
        box.set_margin_bottom(28)
        box.set_margin_start(20)
        box.set_margin_end(20)
        clamp.set_child(box)

        # Parse CHANGELOG_XML
        pattern = re.compile(
            r'<p><em>(Version [^<]+)</em></p>\s*<p>(.*?)</p>(.*?)(?=<p><em>Version|\Z)',
            re.DOTALL
        )
        matches = list(pattern.finditer(CHANGELOG_XML))

        for match in matches:
            ver_title = match.group(1).strip()
            summary_text = match.group(2).strip()
            details_html = match.group(3).strip()

            # Version Card
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            card.add_css_class("card")
            card.set_margin_top(4)
            card.set_margin_bottom(4)

            # Card Header
            header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            header.set_margin_start(16)
            header.set_margin_end(16)
            header.set_margin_top(16)

            v_label = Gtk.Label(label=ver_title)
            v_label.add_css_class("title-3")
            v_label.set_halign(Gtk.Align.START)
            header.append(v_label)

            s_label = Gtk.Label(label=summary_text)
            s_label.add_css_class("body")
            s_label.set_wrap(True)
            s_label.set_halign(Gtk.Align.START)
            s_label.set_xalign(0.0)
            header.append(s_label)
            card.append(header)

            # Sections: Removed, Added, Updated, Visual Changes
            sec_pattern = re.compile(
                r'<p><em>(Features and Fixes [^<]+):</em></p>\s*<ul>(.*?)</ul>',
                re.DOTALL
            )
            sections = list(sec_pattern.finditer(details_html))

            if sections:
                details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                details_box.set_margin_start(16)
                details_box.set_margin_end(16)
                details_box.set_margin_bottom(16)

                for sec in sections:
                    sec_name = sec.group(1).replace("Features and Fixes ", "").strip()
                    items_html = sec.group(2)

                    sec_title = Gtk.Label(label=sec_name)
                    sec_title.add_css_class("heading")
                    sec_title.set_halign(Gtk.Align.START)
                    details_box.append(sec_title)

                    # Extract <li> items
                    li_pattern = re.compile(r'<li>(.*?)</li>', re.DOTALL)
                    for li in li_pattern.finditer(items_html):
                        raw_text = li.group(1).strip()
                        raw_text = re.sub(r'</?[ie]m>', '', raw_text)
                        clean_text = ' '.join(raw_text.split())

                        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                        row_box.set_halign(Gtk.Align.FILL)

                        bullet = Gtk.Label(label="•")
                        bullet.set_valign(Gtk.Align.START)
                        bullet.add_css_class("dim-label")
                        row_box.append(bullet)

                        item_label = Gtk.Label()
                        item_label.set_wrap(True)
                        item_label.set_halign(Gtk.Align.START)
                        item_label.set_xalign(0.0)
                        item_label.set_hexpand(True)

                        if "Reason:" in clean_text:
                            prefix, rest = clean_text.split("Reason:", 1)
                            markup = f"<b>{GLib.markup_escape_text(prefix.strip())}</b> <i>Reason:</i>{GLib.markup_escape_text(rest)}"
                            item_label.set_markup(markup)
                        else:
                            item_label.set_text(clean_text)

                        row_box.append(item_label)
                        details_box.append(row_box)

                card.append(details_box)

            box.append(card)

        return scroll

    def _build_description_page(self):
        clamp = Adw.Clamp(maximum_size=560, tightening_threshold=460)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(28)
        box.set_margin_start(20)
        box.set_margin_end(20)
        clamp.set_child(box)

        paragraphs = [p.strip() for p in APP_DESCRIPTION.split("\n\n") if p.strip()]

        if len(paragraphs) > 0:
            box.append(self._create_desc_card(_("Overview"), paragraphs[0]))
        if len(paragraphs) > 1:
            box.append(self._create_desc_card(_("100% Offline & Privacy-First"), paragraphs[1]))
        if len(paragraphs) > 2:
            box.append(self._create_desc_card(_("Architecture & Development"), paragraphs[2]))
        if len(paragraphs) > 3:
            box.append(self._create_desc_card(_("Free & Open Source"), paragraphs[3]))
        if len(paragraphs) > 4:
            qual_text = "\n\n".join(paragraphs[4:7]) if len(paragraphs) > 6 else "\n\n".join(paragraphs[4:])
            box.append(self._create_desc_card(_("Voice Quality & Multi-Speaker Models"), qual_text))
        if len(paragraphs) > 8:
            box.append(self._create_desc_card(_("Minimum PC Requirements"), paragraphs[8]))
        if len(paragraphs) > 10:
            box.append(self._create_desc_card(_("Recommended PC Requirements (High-Quality Voice Models)"), "\n\n".join(paragraphs[10:])))

        return scroll

    def _create_desc_card(self, title, text):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_start(2)
        card.set_margin_end(2)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_margin_top(16)
        content.set_margin_bottom(16)

        t_lbl = Gtk.Label(label=title)
        t_lbl.add_css_class("heading")
        t_lbl.set_halign(Gtk.Align.START)
        content.append(t_lbl)

        body_lbl = Gtk.Label(label=text)
        body_lbl.set_wrap(True)
        body_lbl.set_halign(Gtk.Align.START)
        body_lbl.set_xalign(0.0)
        content.append(body_lbl)

        card.append(content)
        return card

    def _build_credits_page(self):
        clamp = Adw.Clamp(maximum_size=560, tightening_threshold=460)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(24)
        box.set_margin_bottom(28)
        box.set_margin_start(20)
        box.set_margin_end(20)
        clamp.set_child(box)

        credit_data = [
            (_("Developers"), [
                ("zackarious", "https://github.com/Zackarious/ReadAloud"),
                ("Walter Bernard (Original Creator of Parolu)", "https://github.com/wbernard/parolu"),
            ]),
            (_("Designers"), [
                ("Asam Munir (UI Icons)", "https://dribbble.com/asammunir"),
            ]),
            (_("Speech Engine and Voice Models"), [
                ("Piper Neural Text-to-Speech Engine", "https://github.com/rhasspy/piper"),
                ("Piper Voice Models Repository", "https://github.com/rhasspy/piper-voices"),
                ("Michael Hansen (Rhasspy)", "https://github.com/synesthesiam"),
            ]),
            (_("Icon Providers"), [
                ("SVGRepo (Asam Munir Collection)", "https://www.svgrepo.com/author/Asam%20Munir/"),
                ("Flaticon (CD Audio Icon)", "https://www.flaticon.com/free-icon/cd_6749218"),
            ]),
            (_("Open Source Licenses"), [
                ("GNU General Public License v3.0", "https://www.gnu.org/licenses/gpl-3.0.txt"),
                ("The MIT License", "https://opensource.org/licenses/MIT"),
            ]),
        ]

        for group_title, items in credit_data:
            group = Adw.PreferencesGroup(title=group_title)
            for title, url in items:
                row = Adw.ActionRow()
                row.set_title(title)
                row.set_subtitle(url)
                row.set_activatable(True)

                icon = Gtk.Image.new_from_icon_name("adw-external-link-symbolic")
                icon.add_css_class("dim-label")
                row.add_suffix(icon)

                def on_row_activated(r, u=url):
                    Gio.AppInfo.launch_default_for_uri(u, None)
                row.connect("activated", on_row_activated)

                group.add(row)

            box.append(group)

        return scroll

    def _build_legal_page(self):
        clamp = Adw.Clamp(maximum_size=560, tightening_threshold=460)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(24)
        box.set_margin_bottom(28)
        box.set_margin_start(20)
        box.set_margin_end(20)
        clamp.set_child(box)

        group = Adw.PreferencesGroup(title=_("Licensing and Copyright Information"))

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        card.set_margin_top(4)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_margin_top(16)
        text_view.set_margin_bottom(16)
        text_view.set_margin_start(16)
        text_view.set_margin_end(16)
        text_view.get_buffer().set_text(LICENSING_TEXT)

        card.append(text_view)
        group.add(card)
        box.append(group)

        return scroll


class ReadAloudApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        app_flags = Gio.ApplicationFlags.DEFAULT_FLAGS
        if sys.platform == "win32":
            app_flags = Gio.ApplicationFlags.NON_UNIQUE
        super().__init__(application_id='im.zackarious.ReadAloud',
                         flags=app_flags)
        self.create_action('quit', self._on_quit_action, ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('changelog', self.on_changelog_action)
        self.create_action('toggle-bubble', self.on_toggle_bubble_action)
        self.bubble = None
        self.set_accels_for_action("win.open", ["<primary>o"])
        self.set_accels_for_action("win.save-as", ["<primary>s"])
        self.set_accels_for_action("win.save-audio-as", ["<primary>e"])
        self.set_accels_for_action("win.play-audio", ["<primary>p"])
        self.set_accels_for_action("win.speed-up", ["<primary>Up"])
        self.set_accels_for_action("win.speed-down", ["<primary>Down"])
        self.set_accels_for_action("win.new-tab", ["<primary>t"])
        self.set_accels_for_action("win.close-tab", ["<primary>w"])
        self.set_accels_for_action("win.unwrap-text", ["<primary><shift>w", "<primary>j"])

    def _on_quit_action(self, *args):
        if hasattr(self, 'bubble') and self.bubble:
            self.bubble.close()
        win = self.props.active_window
        if win:
            win.close()
        else:
            self.quit()

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary, and load the floating listener bubble.
        """
        win = self.props.active_window
        if not win:
            win = ReadAloudWindow(application=self)
        win.present()

        if not hasattr(self, 'bubble') or not self.bubble:
            self.bubble = ListenerBubbleWindow(application=self, main_window=win)
        self.bubble.present()

    def on_toggle_bubble_action(self, widget, _):
        """Toggle visibility of the floating listener bubble."""
        if not hasattr(self, 'bubble') or not self.bubble:
            win = self.props.active_window
            self.bubble = ListenerBubbleWindow(application=self, main_window=win)
        if self.bubble.is_visible():
            self.bubble.set_visible(False)
        else:
            self.bubble.set_visible(True)
            self.bubble.present()

    def _create_about_window(self):
        """Creates and configures the About ReadAloud window with sub-tabs."""
        about = AboutReadAloudWindow(transient_for=self.props.active_window)
        return about

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = self._create_about_window()
        about.stack.set_visible_child_name("about")
        about.present()

    def on_changelog_action(self, widget, _):
        """Callback for the app.changelog action to present Change Logs directly."""
        about = self._create_about_window()
        about.stack.set_visible_child_name("changelogs")
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print('app.preferences action activated')

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    try:
        from .error_logger import install_exception_hooks
        install_exception_hooks()
    except Exception:
        pass
    ensure_resources_loaded()
    app = ReadAloudApplication()
    result = app.run(sys.argv)
    return result

if __name__ == "__main__":
    main("1.8.13")
