# window.py
#
# Copyright 2025 Walter Bernard (Original Creator)
# Modified and renamed to ReadAloud by zackarious
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

from gi.repository import Adw
from gi.repository import Gtk, Gio, GLib, Gdk, Pango, Gsk, Graphene

import os
import glob
import json
import shutil
import re
import datetime
import threading

from .reader import Reader
from .pipervoice import VoiceManager
from .demos import DEMOS
from .paths import get_model_search_paths, get_resource_bundle_path
from .document_importer import load_document_chapters
from .wikipedia_importer import (
    fetch_wikipedia_articles,
    normalize_wikipedia_topic_or_url,
    WikipediaArticle,
    fetch_wikipedia_suggestions,
    fetch_thumbnail_bytes,
    WikipediaSuggestion,
    WikipediaTrendingTopic,
    fetch_wikipedia_top_25,
)

def _ensure_resources_loaded():
    bundle_path = get_resource_bundle_path()
    if bundle_path and bundle_path.is_file():
        try:
            res = Gio.Resource.load(str(bundle_path))
            res._register()
        except Exception:
            pass

_ensure_resources_loaded()

import gettext   # Required so that the underscore means translatable
_ = gettext.gettext

display = Gdk.Display.get_default()
if display:
    icon_theme = Gtk.IconTheme.get_for_display(display)
    if os.path.isdir("/app/share/icons"):
        icon_theme.add_search_path("/app/share/icons")
    icon_theme.add_resource_path("/im/zackarious/ReadAloud/icons")

# Fixed optimal pitches per voice model
FIXED_VOICE_PITCHES = {
    "en_GB-alan-low": 1.0,
    "en_GB-alan-medium": 1.2,
    "en_GB-alba-medium": 1.2,
    "en_GB-aru-medium": 1.3,
    "en_GB-cori-high": 1.2,
    "en_GB-cori-medium": 1.2,
    "en_GB-jenny_dioco-medium": 1.2,
    "en_GB-northern_english_male-medium": 1.2,
    "en_GB-semaine-medium": 1.0,
    "en_GB-southern_english_female-low": 0.8,
    "en_GB-vctk-medium": 1.2,
    "en_US-amy-low": 0.9,
    "en_US-amy-medium": 1.2,
    "en_US-arctic-medium": 1.4,
    "en_US-bryce-medium": 1.3,
    "en_US-danny-low": 1.0,
    "en_US-hfc_female-medium": 1.1,
    "en_US-hfc_male-medium": 1.1,
    "en_US-joe-medium": 1.2,
    "en_US-john-medium": 1.1,
    "en_US-kathleen-low": 0.9,
    "en_US-kristin-medium": 1.0,
    "en_US-kusal-medium": 1.3,
    "en_US-l2arctic-medium": 1.3,
    "en_US-lessac-high": 1.2,
    "en_US-lessac-low": 0.9,
    "en_US-lessac-medium": 1.1,
    "en_US-libritts-high": 1.3,
    "en_US-libritts_r-medium": 1.2,
    "en_US-ljspeech-high": 1.2,
    "en_US-ljspeech-medium": 1.2,
    "en_US-norman-medium": 1.4,
    "en_US-ryan-high": 1.2,
    "en_US-ryan-low": 0.8,
    "en_US-ryan-medium": 1.2,
}

def get_pitch_for_voice(voice_id):
    """Returns the fixed pitch for the specified voice model ID or filename, defaulting to 1.0."""
    if not voice_id:
        return 1.0
    cleaned = str(voice_id).replace(".onnx", "").strip()
    if cleaned in FIXED_VOICE_PITCHES:
        return FIXED_VOICE_PITCHES[cleaned]
    for k, v in FIXED_VOICE_PITCHES.items():
        if cleaned == k or cleaned.endswith(f"-{k}") or k in cleaned:
            return v
    return 1.0

# Simplified 5-choice speeds per voice model: Slower, Slow, Normal, Fast, Super Fast
SPEED_CHOICES = ["Slower", "Slow", "Normal", "Fast", "Super Fast"]

VOICE_MODEL_SPEEDS = {
    "en_GB-alan-low": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.0, "Super Fast": 1.2},
    "en_GB-alan-medium": {"Slower": 0.8, "Slow": 0.9, "Normal": 1.0, "Fast": 1.2, "Super Fast": 1.4},
    "en_GB-alba-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_GB-aru-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_GB-cori-high": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_GB-cori-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_GB-jenny_dioco-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_GB-northern_english_male-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_GB-semaine-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_GB-southern_english_female-low": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_GB-vctk-medium": {"Slower": 0.2, "Slow": 0.3, "Normal": 0.4, "Fast": 0.9, "Super Fast": 1.2},
    "en_US-amy-low": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-amy-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-arctic-medium": {"Slower": 0.4, "Slow": 0.5, "Normal": 0.6, "Fast": 0.9, "Super Fast": 1.2},
    "en_US-bryce-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-danny-low": {"Slower": 0.4, "Slow": 0.5, "Normal": 0.6, "Fast": 0.9, "Super Fast": 1.2},
    "en_US-hfc_female-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-hfc_male-medium": {"Slower": 0.7, "Slow": 0.8, "Normal": 0.9, "Fast": 1.2, "Super Fast": 1.5},
    "en_US-joe-medium": {"Slower": 0.7, "Slow": 0.8, "Normal": 0.9, "Fast": 1.2, "Super Fast": 1.5},
    "en_US-john-medium": {"Slower": 0.8, "Slow": 0.9, "Normal": 1.0, "Fast": 1.2, "Super Fast": 1.4},
    "en_US-kathleen-low": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-kristin-medium": {"Slower": 0.8, "Slow": 0.9, "Normal": 1.0, "Fast": 1.2, "Super Fast": 1.4},
    "en_US-kusal-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-l2arctic-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-lessac-high": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-lessac-low": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-lessac-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-libritts-high": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-libritts_r-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-ljspeech-high": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-ljspeech-medium": {"Slower": 0.6, "Slow": 0.7, "Normal": 0.8, "Fast": 1.1, "Super Fast": 1.4},
    "en_US-norman-medium": {"Slower": 0.4, "Slow": 0.5, "Normal": 0.6, "Fast": 0.9, "Super Fast": 1.2},
    "en_US-ryan-high": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-ryan-low": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
    "en_US-ryan-medium": {"Slower": 0.5, "Slow": 0.6, "Normal": 0.7, "Fast": 1.0, "Super Fast": 1.3},
}

def get_speed_for_voice(voice_id, speed_mode="Normal"):
    """Returns the speed value for a given voice model and speed mode ('Slower', 'Slow', 'Normal', 'Fast', 'Super Fast')."""
    if isinstance(speed_mode, int):
        modes = SPEED_CHOICES
        speed_mode = modes[speed_mode] if 0 <= speed_mode < len(modes) else "Normal"
    elif not speed_mode or str(speed_mode).title() not in ("Slower", "Slow", "Normal", "Fast", "Super Fast"):
        speed_mode = "Normal"
    else:
        speed_mode = str(speed_mode).title()

    if not voice_id:
        return {"Slower": 0.8, "Slow": 0.9, "Normal": 1.0, "Fast": 1.2, "Super Fast": 1.4}.get(speed_mode, 1.0)

    cleaned = str(voice_id).replace(".onnx", "").strip()
    if cleaned in VOICE_MODEL_SPEEDS:
        return VOICE_MODEL_SPEEDS[cleaned].get(speed_mode, 1.0)

    for k, v in VOICE_MODEL_SPEEDS.items():
        if cleaned == k or cleaned.endswith(f"-{k}") or k in cleaned:
            return v.get(speed_mode, 1.0)

    return {"Slower": 0.8, "Slow": 0.9, "Normal": 1.0, "Fast": 1.2, "Super Fast": 1.4}.get(speed_mode, 1.0)


def clean_round_brackets(text: str) -> str:
    """Removes all text between () round brackets and the brackets themselves,
    normalizing whitespace and punctuation spacing."""
    if not text:
        return ""
    # Strip markdown images to prevent orphan '!' artifacts: ![alt](url)
    text = re.sub(r'(?<!\w)!\s*\[[^\[\]]*\]\([^()]*\)', '', text, flags=re.DOTALL)
    # Remove matching pairs of () including multiline blocks and nested parentheses
    pattern = r'\([^()]*\)'
    while re.search(pattern, text, flags=re.DOTALL):
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    # Remove whitespace before punctuation like , . ; : ? !
    text = re.sub(r'[ \t]+([,.;:?!])', r'\1', text)
    # Collapse consecutive horizontal ASCII spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Clean up whitespace on each line while removing orphan '!' lines
    lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result)


def clean_square_brackets(text: str) -> str:
    """Removes all text between [] square brackets and the brackets themselves,
    normalizing whitespace and punctuation spacing."""
    if not text:
        return ""
    # Remove markdown images first: ![alt](url) or ![alt][ref] or ![alt]
    text = re.sub(r'(?<!\w)!\s*\[[^\[\]]*\](?:\([^()]*\)|\[[^\[\]]*\])?', '', text, flags=re.DOTALL)
    # If a bracket is attached to a word and immediately precedes a space and '(', clean space before '('
    text = re.sub(r'(?<=\S)\[[^\[\]]*\][ \t]+(?=\()', '', text, flags=re.DOTALL)
    # Remove matching pairs of [] including multiline blocks and nested brackets
    pattern = r'\[[^\[\]]*\]'
    while re.search(pattern, text, flags=re.DOTALL):
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    # Remove whitespace before punctuation like , . ; : ? !
    text = re.sub(r'[ \t]+([,.;:?!])', r'\1', text)
    # Collapse consecutive horizontal ASCII spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Clean up whitespace on each line while removing orphan '!' lines
    lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result)


def clean_hash_symbols(text: str) -> str:
    """Removes all # characters from the text, normalizing whitespace and spacing."""
    if not text:
        return ""
    text = text.replace("#", "")
    text = re.sub(r'[ \t]{2,}', ' ', text)
    lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result)


def is_table_separator(line: str) -> bool:
    """Checks whether a line is a markdown table delimiter row (e.g. | --- | --- | or --- | ---)."""
    stripped = line.strip()
    if not stripped or '|' not in stripped:
        return False
    return bool(re.match(r'^[\|\-\:\s]+$', stripped) and '-' in stripped)


def clean_pipe_brackets(text: str) -> str:
    """Removes all markdown tables, text between | pipe characters, and the pipes themselves,
    normalizing whitespace and punctuation spacing."""
    if not text:
        return ""

    lines = text.splitlines()
    n = len(lines)
    is_table_line = [False] * n

    # Step 1: Identify markdown table delimiter rows and connected header/data rows
    for i, line in enumerate(lines):
        stripped = line.strip()
        if is_table_separator(stripped):
            is_table_line[i] = True
            # Scan upwards for table header line(s)
            up = i - 1
            while up >= 0 and not is_table_line[up] and '|' in lines[up] and lines[up].strip():
                is_table_line[up] = True
                up -= 1
            # Scan downwards for table data rows
            down = i + 1
            while down < n and not is_table_line[down] and '|' in lines[down] and lines[down].strip():
                is_table_line[down] = True
                down += 1

    # Step 2: Any line that starts and ends with | is a table row / pipe-enclosed line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|') and len(stripped) >= 1:
            is_table_line[i] = True

    # Filter out table lines
    filtered_lines = [line for i, line in enumerate(lines) if not is_table_line[i]]
    text = '\n'.join(filtered_lines)

    # Step 3: Remove inline pipe blocks and multiline pipe blocks
    text = re.sub(r'\|[^|]*\|', '', text, flags=re.DOTALL)

    # Step 4: Remove whitespace before punctuation like , . ; : ? !
    text = re.sub(r'[ \t]+([,.;:?!])', r'\1', text)

    # Step 5: Collapse consecutive horizontal ASCII spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    result_lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']

    # Collapse excessive blank lines
    result = '\n'.join(result_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip('\n')


def clean_star_symbols(text: str) -> str:
    """Removes all * (asterisk) characters from the text, normalizing whitespace and spacing."""
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and all(c in '* \t' for c in stripped) and stripped.count('*') >= 3:
            lines.append('')
            continue
        lines.append(line)
    text = '\n'.join(lines)
    text = text.replace('*', '')
    text = re.sub(r'[ \t]+([,.;:?!])', r'\1', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result)


def apply_text_tag_stripping(text: str, strip_round: bool = False, strip_square: bool = False, strip_pipe: bool = False, strip_hash: bool = False, strip_stars: bool = False) -> str:
    """Applies one or more tag stripping operations to the given text."""
    if not text:
        return ""
    # Strip markdown images if any tag stripping is active to eliminate orphan '!' artifacts
    if strip_round or strip_square or strip_pipe or strip_hash or strip_stars:
        text = re.sub(r'(?<!\w)!\s*\[[^\[\]]*\](?:\([^()]*\)|\[[^\[\]]*\])?', '', text, flags=re.DOTALL)
        lines = [line for line in text.splitlines() if line.strip(' \t') != '!']
        text = '\n'.join(lines)
    if strip_pipe:
        text = clean_pipe_brackets(text)
    if strip_round:
        text = clean_round_brackets(text)
    if strip_square:
        text = clean_square_brackets(text)
    if strip_hash:
        text = clean_hash_symbols(text)
    if strip_stars:
        text = clean_star_symbols(text)
    lines = [line.strip(' \t') for line in text.splitlines() if line.strip(' \t') != '!']
    result = '\n'.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip('\n')


def clean_all_tags(text: str) -> str:
    """Applies all text cleaning operations: pipes/tables, round brackets, square brackets,
    hash symbols, and star/asterisk symbols, normalizing whitespace and punctuation spacing."""
    return apply_text_tag_stripping(
        text,
        strip_round=True,
        strip_square=True,
        strip_pipe=True,
        strip_hash=True,
        strip_stars=True
    )


def unwrap_text(text: str) -> str:
    """
    Unwraps and reflows physical line breaks from multi-column PDFs, OCR scans,
    and terminals into natural flowing paragraphs while preserving paragraph breaks.

    - Joins hyphenated line breaks (e.g. 'diffu-\\nsion' -> 'diffusion').
    - Joins soft single line wraps within paragraphs with a space.
    - Preserves distinct paragraph breaks (\\n\\n or \\n\\s*\\n+).
    """
    if text is None:
        return None
    if not text:
        return ""

    # Normalize CRLF and CR
    norm = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into paragraphs by 2 or more newlines
    paragraphs = re.split(r'\n\s*\n+', norm)
    unwrapped_paras = []

    for para in paragraphs:
        p = para.strip()
        if not p:
            continue
        # Join hyphenated line breaks at word boundary: word-\nword -> wordword
        p = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', p)
        # Replace soft single newlines within paragraph with a single space
        p = re.sub(r'\s*\n\s*', ' ', p)
        unwrapped_paras.append(p)

    return "\n\n".join(unwrapped_paras)


def ensure_paragraph_gaps(text: str) -> str:
    """Ensures each line/paragraph is separated by an empty line gap (\\n\\n).

    Single newlines become double newlines. Existing multiple newlines are normalized
    so there is a clean gap between paragraphs for comfortable reading and speech playback.
    """
    if text is None:
        return None
    if not text:
        return ""
    # Normalize CRLF and CR
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Clean whitespace on blank lines
    normalized = re.sub(r"\n[ \t]+(?=\n)", "\n", normalized)
    # Normalize excessive newlines (3 or more) down to 2
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    # Convert single newlines into double newlines
    normalized = re.sub(r"(?<!\n)\n(?!\n)", "\n\n", normalized)
    return normalized


class HighlightTextView(Gtk.TextView):
    """GtkTextView subclass that renders active speech word highlighting with
    2x padding and 10px rounded corners in the BELOW_TEXT layer, inserts a separate line
    with a gap on Return key, normalizes paragraph gaps on clipboard paste,
    automatically removes tags while typing or pasting when auto-remove-tags is enabled,
    and shows font zoom popup buttons when idle hovering for 1.5s."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._highlight_range = None
        self._hover_timer_id = None
        self._window = None

        # Return key controller to insert a separate line with a gap (\n\n)
        # and keyboard listener for typing tag removal & dismissing font zoom popup
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

        # Intercept clipboard paste to apply tag cleaning and paragraph gap formatting
        self.connect("paste-clipboard", self._on_paste_clipboard)

    def is_auto_remove_tags_enabled(self):
        win = getattr(self, '_window', None)
        if not win and hasattr(self, 'get_root'):
            win = self.get_root()
        if win and hasattr(win, 'auto_remove_tags'):
            return bool(win.auto_remove_tags)
        return True

    def dismiss_font_zoom_popup(self):
        pass

    def _clean_completed_tag_at_cursor(self, closing_char):
        if not self.is_auto_remove_tags_enabled():
            return False
        buf = self.get_buffer()
        if not buf or not self.get_editable():
            return False

        opener_map = {')': '(', ']': '[', '|': '|'}
        opener = opener_map.get(closing_char)
        if not opener:
            return False

        cursor_mark = buf.get_insert()
        cursor_iter = buf.get_iter_at_mark(cursor_mark)

        end_iter = cursor_iter.copy()
        check_iter = end_iter.copy()
        if not check_iter.backward_char():
            return False

        def _iter_char(it):
            c = it.get_char()
            return c if isinstance(c, str) else chr(c)

        if _iter_char(check_iter) != closing_char:
            return False

        start_iter = check_iter.copy()
        found_opener = False
        max_scan = 2000
        steps = 0

        while steps < max_scan and start_iter.backward_char():
            steps += 1
            c = _iter_char(start_iter)
            if c == opener:
                found_opener = True
                break
            if closing_char != '|' and (c == closing_char or c == '\n'):
                break
            elif closing_char == '|' and c == '\n':
                break

        if found_opener:
            buf.begin_user_action()

            has_space_before = False
            space_before_iter = start_iter.copy()
            if space_before_iter.backward_char() and _iter_char(space_before_iter) == ' ':
                has_space_before = True

            has_space_after = False
            is_followed_by_punct = False
            if not end_iter.is_end():
                next_c = _iter_char(end_iter)
                if next_c == ' ':
                    has_space_after = True
                elif next_c in ',.;:?!':
                    is_followed_by_punct = True

            if has_space_before and (has_space_after or end_iter.is_end() or is_followed_by_punct):
                start_iter.backward_char()
            elif not has_space_before and has_space_after:
                end_iter.forward_char()

            buf.delete(start_iter, end_iter)
            buf.end_user_action()
            self.scroll_mark_onscreen(buf.get_insert())

        return False

    def _on_key_pressed(self, controller, keyval, keycode, state):
        self.dismiss_font_zoom_popup()

        if self.is_auto_remove_tags_enabled() and self.get_editable():
            modifiers = state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK | Gdk.ModifierType.META_MASK)
            unicode_val = Gdk.keyval_to_unicode(keyval)
            ch = chr(unicode_val) if unicode_val > 0 else ""

            # Standalone hash and asterisk symbols: consume to prevent insertion
            if not modifiers and (ch in ('#', '*') or keyval in (Gdk.KEY_numbersign, Gdk.KEY_asterisk, Gdk.KEY_KP_Multiply)):
                return True

            # Closing brackets or pipes: schedule real-time tag cleanup upon insertion
            if not modifiers and ch in (')', ']', '|'):
                GLib.idle_add(self._clean_completed_tag_at_cursor, ch)

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            # Ignore if Ctrl, Alt, or Super/Meta are pressed
            modifiers = state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK | Gdk.ModifierType.META_MASK)
            if not modifiers:
                if not self.get_editable():
                    return False
                buf = self.get_buffer()
                if buf:
                    buf.begin_user_action()
                    buf.delete_selection(True, self.get_editable())
                    if state & Gdk.ModifierType.SHIFT_MASK:
                        buf.insert_at_cursor("\n")
                    else:
                        buf.insert_at_cursor("\n\n")
                    buf.end_user_action()
                    mark = buf.get_insert()
                    self.scroll_mark_onscreen(mark)
                    return True
        return False

    def _on_paste_clipboard(self, textview):
        self.stop_emission_by_name("paste-clipboard")
        self.dismiss_font_zoom_popup()
        clipboard = self.get_clipboard()
        if not clipboard:
            return

        def on_read_text(cb, res, _):
            try:
                raw_text = cb.read_text_finish(res)
            except Exception:
                raw_text = None
            if raw_text:
                if self.is_auto_remove_tags_enabled():
                    raw_text = clean_all_tags(raw_text)
                formatted_text = ensure_paragraph_gaps(raw_text)
                buf = self.get_buffer()
                if buf and self.get_editable():
                    buf.begin_user_action()
                    buf.delete_selection(True, self.get_editable())
                    buf.insert_at_cursor(formatted_text)
                    buf.end_user_action()
                    mark = buf.get_insert()
                    self.scroll_mark_onscreen(mark)

        clipboard.read_text_async(None, on_read_text, None)

    def set_highlight_range(self, start_char, end_char):
        if self._highlight_range != (start_char, end_char):
            self._highlight_range = (start_char, end_char) if start_char is not None else None
            self.queue_draw()

    def _get_highlight_rectangles(self, buf, it1, it2):
        """Computes bounding boxes for each visual display line spanned by [it1, it2)."""
        lines = []
        cur = it1.copy()
        while cur.compare(it2) < 0:
            loc = self.get_iter_location(cur)
            if not lines or abs(loc.y - lines[-1]['y']) > max(loc.height, lines[-1]['height']) * 0.5:
                lines.append({
                    'min_x': loc.x,
                    'max_x': loc.x + loc.width,
                    'y': loc.y,
                    'height': loc.height
                })
            else:
                line = lines[-1]
                line['min_x'] = min(line['min_x'], loc.x)
                line['max_x'] = max(line['max_x'], loc.x + loc.width)
                line['y'] = min(line['y'], loc.y)
                line['height'] = max(line['height'], loc.height)
            if not cur.forward_char():
                break
        return [(l['min_x'], l['y'], max(0, l['max_x'] - l['min_x']), l['height']) for l in lines]

    def do_snapshot_layer(self, layer, snapshot):
        if layer == Gtk.TextViewLayer.BELOW_TEXT and self._highlight_range:
            start_char, end_char = self._highlight_range
            buf = self.get_buffer()
            char_count = buf.get_char_count()
            if 0 <= start_char < char_count and start_char < end_char:
                it1 = buf.get_iter_at_offset(start_char)
                it2 = buf.get_iter_at_offset(min(end_char, char_count))
                loc1 = self.get_iter_location(it1)
                loc2 = self.get_iter_location(it2)

                color = Gdk.RGBA()
                color.parse("#f6d32d")
                radius = 10.0

                if loc1.y == loc2.y and loc2.x > loc1.x:
                    rects = [(loc1.x, loc1.y, max(loc2.x - loc1.x, loc1.width), loc1.height)]
                else:
                    rects = self._get_highlight_rectangles(buf, it1, it2)

                for bx, by, bw, bh in rects:
                    if bw <= 0 or bh <= 0:
                        continue
                    pad_x = max(6, int(bh * 0.25))
                    pad_y = max(3, int(bh * 0.125))

                    rect = Graphene.Rect()
                    rect.init(bx - pad_x, by - pad_y, bw + (pad_x * 2), bh + (pad_y * 2))
                    rrect = Gsk.RoundedRect()
                    rrect.init_from_rect(rect, radius)
                    snapshot.push_rounded_clip(rrect)
                    snapshot.append_color(color, rect)
                    snapshot.pop()


@Gtk.Template(resource_path='/im/zackarious/ReadAloud/window.ui')
class ReadAloudWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ReadAloudWindow'

    header_bar = Gtk.Template.Child()      # Header bar containing window controls
    tab_bar = Gtk.Template.Child()         # Tab bar for document tabs
    tab_bar_overlay = Gtk.Template.Child() # Overlay wrapping tab_bar for nav buttons
    tab_bar_end_box = Gtk.Template.Child() # End action container in tab bar
    tab_nav_prev_revealer = Gtk.Template.Child() # Revealer for previous tab navigation button
    tab_nav_prev_btn = Gtk.Template.Child()      # Previous tab navigation button
    tab_nav_next_revealer = Gtk.Template.Child() # Revealer for next tab navigation button
    tab_nav_next_btn = Gtk.Template.Child()      # Next tab navigation button
    tab_view = Gtk.Template.Child()        # Tab view holding document pages
    open_button = Gtk.Template.Child()     # Opens a file
    wiki_button = Gtk.Template.Child()     # Wikipedia importer
    save_text_button = Gtk.Template.Child()     # Saves the text
    rewind_button = Gtk.Template.Child()   # Rewinds audio playback 15 seconds
    forward_button = Gtk.Template.Child()  # Forwards audio playback 15 seconds
    stop_button = Gtk.Template.Child()     # Stops audio playback
    playback_toolbar_revealer = Gtk.Template.Child() # Revealer for playback popup toolbar
    playback_toolbar = Gtk.Template.Child()          # Popup toolbar containing playback controls
    font_zoom_revealer = None                        # Backward compatibility (controls now in tab bar)
    font_zoom_popup = Gtk.Template.Child()           # Box containing font zoom controls
    font_decrease_btn = Gtk.Template.Child()         # Button to decrease font size
    font_zoom_label = Gtk.Template.Child()           # Label displaying font zoom level
    font_increase_btn = Gtk.Template.Child()         # Button to increase font size
    new_tab_button = Gtk.Template.Child()            # Button to open new tab
    read_button = Gtk.Template.Child()     # Plays audio file
    pause_button = Gtk.Template.Child()    # Pauses/resumes audio playback
    save_button = Gtk.Template.Child()     # Saves audio file
    lang_chooser= Gtk.Template.Child()     # Loads language
    voice_chooser= Gtk.Template.Child()    # Loads voice
    speed_chooser= Gtk.Template.Child()    # Loads speaking speed
    speed_button= Gtk.Template.Child()
    editor_overlay = Gtk.Template.Child()  # Overlay wrapping tab_view
    drop_placeholder = Gtk.Template.Child()# Empty tab drag-and-drop placeholder

    _override_main_text_view = None
    _custom_pitch_chooser = None
    _override_adjustment_1 = None
    _tab_counter = 0
    _active_tab_page = None

    def _get_pitch_for_voice(self, voice_id=None):
        if voice_id is None:
            voice_id = self._get_selected_voice_name()
        return get_pitch_for_voice(voice_id)

    @property
    def pitch_chooser(self):
        """Backward-compatible pitch chooser returning get_value() matching selected voice fixed pitch."""
        if self._custom_pitch_chooser is not None:
            return self._custom_pitch_chooser
        pitch = self._get_pitch_for_voice()
        return type('_PitchHolder', (), {'get_value': lambda s: pitch})()

    @pitch_chooser.setter
    def pitch_chooser(self, val):
        self._custom_pitch_chooser = val

    @property
    def adjustment_1(self):
        """Backward-compatible adjustment_1 returning fixed pitch value."""
        if self._override_adjustment_1 is not None:
            return self._override_adjustment_1
        pitch = self._get_pitch_for_voice()
        return type('_AdjHolder', (), {
            'get_value': lambda s: pitch,
            'set_value': lambda s, v: None,
            'connect': lambda s, sig, cb: None
        })()

    @adjustment_1.setter
    def adjustment_1(self, val):
        self._override_adjustment_1 = val

    @property
    def main_text_view(self):
        """Returns the GtkTextView of the currently active tab page, maintaining full backward compatibility."""
        if getattr(self, '_override_main_text_view', None) is not None:
            return self._override_main_text_view
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page'):
            page = self.tab_view.get_selected_page()
            if page:
                sw = page.get_child()
                if sw and hasattr(sw, 'get_child'):
                    return sw.get_child()
        return None

    @main_text_view.setter
    def main_text_view(self, val):
        self._override_main_text_view = val


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.demos_button = None
        self._last_import_dialog = None

        # Connect to the window closing event to save settings
        self.connect("close-request", self._on_close_request)

        # Apply global styling and transparent loading window styling via CSS
        css_provider = Gtk.CssProvider()
        css_data = """
        * { font-size: 101%; }
        textview { font-size: 130%; }
        window.transparent-loading-window,
        window.transparent-loading-window.background {
            background: transparent;
            background-color: transparent;
            box-shadow: none;
            border: none;
        }
        .loading-indicator-box {
            background-color: rgba(30, 30, 30, 0.88);
            border-radius: 20px;
            padding: 24px 28px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
            color: #ffffff;
        }
        .loading-indicator-box progressbar > trough {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            min-height: 8px;
        }
        .loading-indicator-box progressbar > trough > progress {
            background-color: #3584e4;
            border-radius: 6px;
            min-height: 8px;
        }
        .loading-indicator-box .progress-label {
            font-size: 92%;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 500;
        }
        .loading-indicator-box .batch-label {
            font-size: 105%;
            font-weight: 600;
            color: #ffffff;
        }
        .loading-indicator-box .cancel-generation-button {
            margin-top: 14px;
            padding: 5px 22px;
            font-size: 92%;
            font-weight: 500;
            background-color: rgba(255, 255, 255, 0.16);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 9999px;
            transition: background-color 150ms ease-in-out;
        }
        .loading-indicator-box .cancel-generation-button:hover {
            background-color: rgba(255, 255, 255, 0.28);
            color: #ffffff;
        }
        .loading-indicator-box .cancel-generation-button:active {
            background-color: rgba(255, 255, 255, 0.38);
            color: #ffffff;
        }

        /* Drag and Drop empty tab card */
        .drag-drop-card {
            padding: 34px 44px;
            border-radius: 20px;
            border: 2px dashed alpha(@borders, 0.65);
            background-color: alpha(@window_bg_color, 0.88);
            box-shadow: 0 4px 20px alpha(#000000, 0.18);
            transition: all 200ms ease-in-out;
        }
        .drag-drop-card:hover {
            border-color: @accent_color;
            background-color: alpha(@card_bg_color, 0.95);
        }
        .drag-drop-card.drag-hover {
            border-color: @accent_color;
            border-style: solid;
            background-color: alpha(@accent_color, 0.12);
        }
        .drag-drop-desc {
            line-height: 1.45;
            color: alpha(@window_fg_color, 0.85);
        }

        /* Header and bottom toolbar action buttons - styled with hover background */
        .header-icon-btn,
        .action-icon-btn,
        headerbar button.header-icon-btn {
            min-width: 48px;
            min-height: 42px;
            padding: 2px 4px;
            background: transparent;
            background-color: transparent;
            border: none;
            border-radius: 8px;
            box-shadow: none;
            transition: background-color 150ms ease-in-out;
        }

        .header-icon-btn:hover:not(:disabled),
        .action-icon-btn:hover:not(:disabled),
        headerbar button.header-icon-btn:hover:not(:disabled) {
            background-color: alpha(currentColor, 0.10);
            border: none;
        }

        .header-icon-btn:active:not(:disabled),
        .action-icon-btn:active:not(:disabled),
        headerbar button.header-icon-btn:active:not(:disabled) {
            background-color: alpha(currentColor, 0.16);
            border: none;
        }

        .header-icon-btn:disabled,
        .action-icon-btn:disabled,
        headerbar button.header-icon-btn:disabled {
            background-color: transparent;
            border: none;
            opacity: 0.45;
        }

        .header-icon-btn image {
            min-width: 29px;
            min-height: 29px;
            -gtk-icon-size: 29px;
        }

        .action-icon-btn image {
            min-width: 25px;
            min-height: 25px;
            -gtk-icon-size: 25px;
        }

        #save_button image {
            min-width: 27px;
            min-height: 27px;
            -gtk-icon-size: 27px;
        }

        /* Highlight-accent buttons (Open, Play, Pause, Stop) in signature yellow #f6d32d */
        #open_button,
        #read_button,
        #pause_button,
        #stop_button,
        .highlight-accent-btn,
        headerbar button#open_button {
            color: #f6d32d;
        }

        #open_button image,
        #read_button image,
        #pause_button image,
        #stop_button image,
        .highlight-accent-btn image {
            color: #f6d32d;
        }

        #open_button:hover:not(:disabled),
        #read_button:hover:not(:disabled),
        #pause_button:hover:not(:disabled),
        #stop_button:hover:not(:disabled),
        .highlight-accent-btn:hover:not(:disabled),
        headerbar button#open_button:hover:not(:disabled) {
            color: #f8e45c;
            background-color: alpha(#f6d32d, 0.14);
        }

        #open_button:hover:not(:disabled) image,
        #read_button:hover:not(:disabled) image,
        #pause_button:hover:not(:disabled) image,
        #stop_button:hover:not(:disabled) image,
        .highlight-accent-btn:hover:not(:disabled) image {
            color: #f8e45c;
        }

        #open_button:active:not(:disabled),
        #read_button:active:not(:disabled),
        #pause_button:active:not(:disabled),
        #stop_button:active:not(:disabled),
        .highlight-accent-btn:active:not(:disabled),
        headerbar button#open_button:active:not(:disabled) {
            color: #e5a50a;
            background-color: alpha(#f6d32d, 0.24);
        }

        #open_button:active:not(:disabled) image,
        #read_button:active:not(:disabled) image,
        #pause_button:active:not(:disabled) image,
        #stop_button:active:not(:disabled) image,
        .highlight-accent-btn:active:not(:disabled) image {
            color: #e5a50a;
        }

        #read_button:disabled,
        #pause_button:disabled,
        #stop_button:disabled,
        .highlight-accent-btn:disabled {
            color: alpha(#f6d32d, 0.38);
            opacity: 0.50;
        }

        #read_button:disabled image,
        #pause_button:disabled image,
        #stop_button:disabled image,
        .highlight-accent-btn:disabled image {
            color: alpha(#f6d32d, 0.38);
        }

        /* Wikipedia Top 25 Trending Topics Right Pane */
        .trending-pane-card {
            background-color: alpha(currentColor, 0.03);
            border: 1px solid alpha(currentColor, 0.08);
            border-radius: 12px;
        }

        .trending-rank-badge {
            font-weight: 700;
            font-size: 11px;
            color: #f6d32d;
            background-color: alpha(#f6d32d, 0.16);
            border-radius: 6px;
            padding: 2px 6px;
            min-width: 24px;
        }

        .trending-thumb {
            border-radius: 8px;
            border: 1px solid alpha(currentColor, 0.08);
            background-color: alpha(currentColor, 0.04);
        }

        .trending-row {
            padding: 6px 8px;
            border-radius: 8px;
            transition: background-color 120ms ease;
        }

        .trending-row:hover {
            background-color: alpha(currentColor, 0.05);
        }

        .trending-import-btn {
            min-width: 32px;
            min-height: 32px;
            padding: 5px;
            border-radius: 9999px;
            transition: all 150ms ease;
        }

        .trending-import-btn:hover {
            background-color: alpha(#f6d32d, 0.25);
            color: #f6d32d;
        }

        .trending-toggle-btn {
            font-weight: 600;
            margin-top: 2px;
            margin-bottom: 2px;
        }

        .header-demos-btn {
            min-height: 42px;
            padding: 0 14px;
            font-weight: 500;
        }

        /* Playback popup toolbar appearing below bottom fixed bar */
        .playback-popup-toolbar {
            background-color: alpha(currentColor, 0.06);
            border: 1px solid alpha(currentColor, 0.12);
            border-radius: 12px;
            padding: 2px 8px;
        }

        /* Font Zoom Controls in Tab Bar (Before New Tab Button) */
        .font-zoom-tab-bar,
        .font-zoom-popup {
            background-color: alpha(currentColor, 0.06);
            border: 1px solid alpha(currentColor, 0.12);
            border-radius: 9999px;
            padding: 2px 4px;
        }
        .font-zoom-tab-bar button,
        .font-zoom-tab-bar button.circular,
        .font-zoom-popup button,
        .font-zoom-popup button.circular {
            min-width: 28px;
            min-height: 28px;
            border-radius: 9999px;
            padding: 0;
            margin: 0;
            border: none;
            background: transparent;
            box-shadow: none;
            transition: all 150ms ease-in-out;
        }
        .font-zoom-tab-bar button:hover,
        .font-zoom-tab-bar button.circular:hover,
        .font-zoom-popup button:hover,
        .font-zoom-popup button.circular:hover {
            background-color: alpha(currentColor, 0.14);
        }
        .font-zoom-tab-bar button:active,
        .font-zoom-tab-bar button.circular:active,
        .font-zoom-popup button:active,
        .font-zoom-popup button.circular:active {
            background-color: alpha(currentColor, 0.22);
        }
        .font-zoom-tab-bar label,
        .font-zoom-popup label {
            font-weight: 600;
            padding: 0 4px;
            min-width: 42px;
        }

        /* Semi-transparent Tab Navigation Left/Right Buttons */
        .tab-nav-btn {
            background-color: alpha(@window_bg_color, 0.76);
            color: @window_fg_color;
            border: 1px solid alpha(currentColor, 0.16);
            border-radius: 9999px;
            min-width: 28px;
            min-height: 28px;
            padding: 0;
            margin: 0;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.28);
            transition: all 150ms ease-in-out;
            opacity: 0.85;
        }
        .tab-nav-btn:hover {
            background-color: alpha(currentColor, 0.20);
            border-color: alpha(currentColor, 0.32);
            opacity: 1.0;
        }
        .tab-nav-btn:active {
            background-color: alpha(currentColor, 0.30);
            opacity: 1.0;
        }
        .tab-nav-btn:disabled {
            opacity: 0.35;
        }
        """
        css_provider.load_from_string(css_data)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.is_playing = False
        self.is_paused = False
        self.bubble = None
        self.wait_dialog = None

        # Load user preferences
        self.default_settings = {}
        config_path = os.path.join(GLib.get_user_data_dir(), "settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.default_settings = json.load(f)
            except Exception as e:
                print(f"Error loading defaults: {e}")

        # Dictionaries to translate raw codes into readable UI names
        self.LANG_MAP = {
            "en": "English", "eo": "Esperanto", "de": "Deutsch",
            "it": "Italiano", "es": "Español", "fr": "Français"
        }
        self.COUNTRY_MAP = {
            "GB": "UK", "US": "US", "DE": "Germany",
            "FR": "France", "ES": "Spain", "IT": "Italy"
        }
        self.installed_models = {}
        self.lang_name_to_code = {}
        self.current_voices = []
        self.lang_code = "en"

        # Add the action to open a file
        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.open_file_dialog)
        self.add_action(open_action)

        # Add the action to save the text
        save_action = Gio.SimpleAction(name="save-as")
        save_action.connect("activate", self.save_text_dialog)
        self.add_action(save_action)

        # Add the action to save the audio file
        save_audio_action = Gio.SimpleAction(name="save-audio-as")
        save_audio_action.connect("activate", self.save_audio_dialog)
        self.add_action(save_audio_action)

        # Add the action to load a preset demo
        load_demo_action = Gio.SimpleAction(name="load-demo", parameter_type=GLib.VariantType.new("s"))
        load_demo_action.connect("activate", self.on_load_demo_action)
        self.add_action(load_demo_action)

        # Add the actions for text tools (remove round / square brackets)
        remove_round_brackets_action = Gio.SimpleAction(name="remove-round-brackets")
        remove_round_brackets_action.connect("activate", self.on_remove_round_brackets_action)
        self.add_action(remove_round_brackets_action)

        remove_square_brackets_action = Gio.SimpleAction(name="remove-square-brackets")
        remove_square_brackets_action.connect("activate", self.on_remove_square_brackets_action)
        self.add_action(remove_square_brackets_action)

        remove_pipe_brackets_action = Gio.SimpleAction(name="remove-pipe-brackets")
        remove_pipe_brackets_action.connect("activate", self.on_remove_pipe_brackets_action)
        self.add_action(remove_pipe_brackets_action)

        remove_hashes_action = Gio.SimpleAction(name="remove-hashes")
        remove_hashes_action.connect("activate", self.on_remove_hashes_action)
        self.add_action(remove_hashes_action)

        remove_stars_action = Gio.SimpleAction(name="remove-stars")
        remove_stars_action.connect("activate", self.on_remove_stars_action)
        self.add_action(remove_stars_action)

        remove_all_tags_action = Gio.SimpleAction(name="remove-all-tags")
        remove_all_tags_action.connect("activate", self.on_remove_all_tags_action)
        self.add_action(remove_all_tags_action)

        # Stateful toggle action for automatically removing tags on typing/pasting/importing
        auto_remove_tags_default = self.default_settings.get("auto_remove_tags", True)
        self._auto_remove_tags = bool(auto_remove_tags_default)
        self._auto_remove_tags_action = Gio.SimpleAction.new_stateful(
            "auto-remove-tags",
            None,
            GLib.Variant.new_boolean(self._auto_remove_tags)
        )
        self._auto_remove_tags_action.connect("change-state", self._on_auto_remove_tags_change_state)
        self.add_action(self._auto_remove_tags_action)

        import_wikipedia_action = Gio.SimpleAction(name="import-wikipedia")
        import_wikipedia_action.connect("activate", self.on_import_wikipedia_action)
        self.add_action(import_wikipedia_action)

        # Add the action to unwrap / reflow text
        unwrap_text_action = Gio.SimpleAction(name="unwrap-text")
        unwrap_text_action.connect("activate", self.on_unwrap_text_action)
        self.add_action(unwrap_text_action)

        # Add the action to create a new tab
        new_tab_action = Gio.SimpleAction(name="new-tab")
        new_tab_action.connect("activate", lambda *_: self.create_new_tab())
        self.add_action(new_tab_action)

        # Add the action to close the active tab
        close_tab_action = Gio.SimpleAction(name="close-tab")
        close_tab_action.connect("activate", self._on_close_current_tab_action)
        self.add_action(close_tab_action)

        # Add the action to minimize the window
        minimize_action = Gio.SimpleAction(name="minimize")
        minimize_action.connect("activate", lambda *_: self.minimize_window())
        self.add_action(minimize_action)

        # Add the action to toggle maximize the window
        maximize_action = Gio.SimpleAction(name="toggle-maximize")
        maximize_action.connect("activate", lambda *_: self.toggle_maximize_window())
        self.add_action(maximize_action)

        # Ensure minimize, maximize, and close title buttons are always displayed after the burger menu
        if hasattr(self, 'header_bar') and self.header_bar:
            self.header_bar.set_decoration_layout(":minimize,maximize,close")
            self._update_window_controls_tooltips()
            self.connect("notify::maximized", self._update_window_controls_tooltips)
            self.connect("map", self._update_window_controls_tooltips)

        # Add the action to play/toggle audio
        play_action = Gio.SimpleAction(name="play-audio")
        play_action.connect("activate", lambda *_: self.play_audio())
        self.add_action(play_action)

        # Add the action to increase speed
        speed_up_action = Gio.SimpleAction(name="speed-up")
        speed_up_action.connect("activate", lambda *_: self.increase_speed())
        self.add_action(speed_up_action)

        # Add the action to decrease speed
        speed_down_action = Gio.SimpleAction(name="speed-down")
        speed_down_action.connect("activate", lambda *_: self.decrease_speed())
        self.add_action(speed_down_action)

        # Add the action to rewind/forward 15 seconds
        if hasattr(self, 'rewind_button') and hasattr(self.rewind_button, 'connect'):
            self.rewind_button.connect('clicked', self.rewind_15s)
        if hasattr(self, 'forward_button') and hasattr(self.forward_button, 'connect'):
            self.forward_button.connect('clicked', self.forward_15s)

        # Add the action to stop audio playback from popup toolbar
        if hasattr(self, 'stop_button') and hasattr(self.stop_button, 'connect'):
            self.stop_button.connect('clicked', lambda *_: self.stop_playback())

        # Add the action to listen to the text
        self.read_button.connect('clicked', self.read_text)

        # Add the action to pause/resume audio playback
        self.pause_button.connect('clicked', self.toggle_pause)

        # Add the action to save the audio file
        self.save_button.connect('clicked', self.save_audio_dialog)

        # Wire up speed chooser methods and compatibility adjustment
        self.label_2 = None
        self.SPEED_OPTIONS = SPEED_CHOICES
        self.speed_chooser.get_value = self._get_current_speed
        self.speed_chooser.set_value = self._set_speed_value
        default_speed_idx = self.SPEED_OPTIONS.index("Normal") if "Normal" in self.SPEED_OPTIONS else 2
        self.speed_chooser.set_selected(default_speed_idx)
        self.adjustment_2 = Gtk.Adjustment.new(self._get_current_speed(), 0.1, 2.0, 0.1, 0.5, 0.0)
        self.adjustment_2.connect("value-changed", self.on_adjustment_value_changed)
        self.speed_chooser.connect("notify::selected", self._on_speed_chooser_selected)

        # Setup dropdowns to show full text with no excerpt in popup choices and on button
        self._setup_dropdown_excerpt(self.lang_chooser, show_selection_check=True)
        self._setup_dropdown_excerpt(self.voice_chooser, show_selection_check=True)
        self._setup_dropdown_excerpt(self.speed_chooser, show_selection_check=True, icon_name="im.zackarious.ReadAloud.speed-symbolic")

        # Initial UI update
        self._setup_lang_chooser()

        # Set default values for speed if they exist
        if "speed" in self.default_settings:
            GLib.idle_add(self.speed_chooser.set_value, self.default_settings["speed"])

        # Button styling and pixel sizes for action icons
        GLib.idle_add(self.get_style_context().add_class, "view")
        if hasattr(self, 'rewind_button') and hasattr(self.rewind_button, 'get_style_context'):
            GLib.idle_add(self.rewind_button.get_style_context().add_class, "action-icon-btn")
            GLib.idle_add(self.rewind_button.get_style_context().add_class, "flat")
        if hasattr(self, 'forward_button') and hasattr(self.forward_button, 'get_style_context'):
            GLib.idle_add(self.forward_button.get_style_context().add_class, "action-icon-btn")
            GLib.idle_add(self.forward_button.get_style_context().add_class, "flat")
        if hasattr(self, 'stop_button') and hasattr(self.stop_button, 'get_style_context'):
            GLib.idle_add(self.stop_button.get_style_context().add_class, "action-icon-btn")
            GLib.idle_add(self.stop_button.get_style_context().add_class, "flat")
            GLib.idle_add(self.stop_button.get_style_context().add_class, "highlight-accent-btn")
        GLib.idle_add(self.read_button.get_style_context().add_class, "action-icon-btn")
        GLib.idle_add(self.read_button.get_style_context().add_class, "flat")
        GLib.idle_add(self.read_button.get_style_context().add_class, "highlight-accent-btn")
        GLib.idle_add(self.pause_button.get_style_context().add_class, "action-icon-btn")
        GLib.idle_add(self.pause_button.get_style_context().add_class, "flat")
        GLib.idle_add(self.pause_button.get_style_context().add_class, "highlight-accent-btn")
        GLib.idle_add(self.save_button.get_style_context().add_class, "action-icon-btn")
        GLib.idle_add(self.save_button.get_style_context().add_class, "flat")
        GLib.idle_add(self.open_button.get_style_context().add_class, "header-icon-btn")
        GLib.idle_add(self.open_button.get_style_context().add_class, "highlight-accent-btn")
        if hasattr(self, 'wiki_button') and self.wiki_button:
            wiki_paintable = self._get_wikipedia_logo_paintable()
            if wiki_paintable:
                wiki_img = Gtk.Image.new_from_paintable(wiki_paintable)
                wiki_img.set_pixel_size(28)
                self.wiki_button.set_child(wiki_img)
            GLib.idle_add(self.wiki_button.get_style_context().add_class, "header-icon-btn")
        GLib.idle_add(self.save_text_button.get_style_context().add_class, "header-icon-btn")
        if hasattr(self, 'demos_button') and self.demos_button:
            GLib.idle_add(self.demos_button.get_style_context().add_class, "header-demos-btn")
        GLib.idle_add(self.lang_chooser.get_first_child().get_style_context().add_class, "flat")
        GLib.idle_add(self.voice_chooser.get_first_child().get_style_context().add_class, "flat")
        if hasattr(self, 'speed_chooser') and self.speed_chooser:
            first_child = self.speed_chooser.get_first_child()
            if first_child and hasattr(first_child, 'get_style_context'):
                GLib.idle_add(first_child.get_style_context().add_class, "flat")
        if hasattr(self, 'speed_button') and self.speed_button and hasattr(self.speed_button, 'get_style_context'):
            GLib.idle_add(self.speed_button.get_style_context().add_class, "flat")

        def _apply_button_and_icon_sizes():
            # Apply pixel sizes to icon images so they fill the button area space
            buttons_to_size = [
                (self.open_button, 29),
                (getattr(self, 'wiki_button', None), 28),
                (self.save_text_button, 29),
                (self.save_button, 27),
                (getattr(self, 'rewind_button', None), 25),
                (getattr(self, 'forward_button', None), 25),
                (getattr(self, 'stop_button', None), 25),
                (self.read_button, 25),
                (self.pause_button, 25),
            ]
            for btn, sz in buttons_to_size:
                if not btn or not hasattr(btn, 'get_child'):
                    continue
                child = btn.get_child()
                if isinstance(child, Gtk.Image):
                    child.set_pixel_size(sz)
            self.open_button.set_size_request(48, 42)
            if hasattr(self, 'wiki_button') and self.wiki_button:
                self.wiki_button.set_size_request(48, 42)
            self.save_text_button.set_size_request(48, 42)
            if hasattr(self, 'demos_button') and self.demos_button:
                self.demos_button.set_size_request(-1, 42)
            if hasattr(self, 'rewind_button') and hasattr(self.rewind_button, 'set_size_request'):
                self.rewind_button.set_size_request(48, 42)
            if hasattr(self, 'forward_button') and hasattr(self.forward_button, 'set_size_request'):
                self.forward_button.set_size_request(48, 42)
            if hasattr(self, 'stop_button') and hasattr(self.stop_button, 'set_size_request'):
                self.stop_button.set_size_request(48, 42)
            self.read_button.set_size_request(48, 42)
            self.pause_button.set_size_request(48, 42)
            self.save_button.set_size_request(48, 42)

        GLib.idle_add(_apply_button_and_icon_sizes)

        # Setup tab management
        self._tab_counter = 0
        self._highlight_timeout_id = None
        self._current_highlight_index = None
        self._last_scrolled_line_y = None

        # Setup dynamic text zoom provider globally
        self.text_zoom_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.text_zoom_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        saved_zoom = self.default_settings.get("text_zoom", 130)
        self.set_text_zoom(saved_zoom)

        # Wire font zoom controls in tab bar (always visible)
        if hasattr(self, 'font_zoom_popup') and self.font_zoom_popup:
            self.font_zoom_popup.add_css_class("font-zoom-tab-bar")
        if hasattr(self, 'font_increase_btn') and self.font_increase_btn:
            self.font_increase_btn.add_css_class("flat")
            self.font_increase_btn.add_css_class("circular")
            self.font_increase_btn.connect("clicked", lambda *_: self.zoom_in())
        if hasattr(self, 'font_decrease_btn') and self.font_decrease_btn:
            self.font_decrease_btn.add_css_class("flat")
            self.font_decrease_btn.add_css_class("circular")
            self.font_decrease_btn.connect("clicked", lambda *_: self.zoom_out())
        if hasattr(self, 'font_zoom_label') and self.font_zoom_label:
            self.font_zoom_label.add_css_class("caption")
            self.font_zoom_label.add_css_class("dim-label")

        # Tab navigation buttons setup (overlay over tab bar)
        self._tab_bar_is_hovered = False
        if hasattr(self, 'tab_nav_prev_btn') and self.tab_nav_prev_btn:
            self.tab_nav_prev_btn.add_css_class("flat")
            self.tab_nav_prev_btn.add_css_class("circular")
            self.tab_nav_prev_btn.add_css_class("tab-nav-btn")
            self.tab_nav_prev_btn.connect("clicked", lambda *_: self.navigate_previous_tab())
        if hasattr(self, 'tab_nav_next_btn') and self.tab_nav_next_btn:
            self.tab_nav_next_btn.add_css_class("flat")
            self.tab_nav_next_btn.add_css_class("circular")
            self.tab_nav_next_btn.add_css_class("tab-nav-btn")
            self.tab_nav_next_btn.connect("clicked", lambda *_: self.navigate_next_tab())

        if hasattr(self, 'tab_bar_overlay') and self.tab_bar_overlay:
            tab_motion = Gtk.EventControllerMotion.new()
            tab_motion.connect("enter", self._on_tab_bar_enter)
            tab_motion.connect("motion", self._on_tab_bar_enter)
            tab_motion.connect("leave", self._on_tab_bar_leave)
            self.tab_bar_overlay.add_controller(tab_motion)

        # Keyboard controller for shortcuts (Ctrl +, -, 0, Ctrl+T, Ctrl+W, Ctrl+P, Ctrl+E, Ctrl+Up, Ctrl+Down, F5, Esc)
        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Setup file drag and drop target on window
        file_drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        file_drop_target.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        file_drop_target.connect("drop", self._on_files_dropped)
        file_drop_target.connect("enter", self._on_drop_enter)
        file_drop_target.connect("leave", self._on_drop_leave)
        self.add_controller(file_drop_target)

        # Setup click gesture on drop placeholder to focus textview
        if isinstance(getattr(self, 'drop_placeholder', None), Gtk.Widget):
            placeholder_click = Gtk.GestureClick.new()
            placeholder_click.connect("released", self._on_placeholder_clicked)
            self.drop_placeholder.add_controller(placeholder_click)

        # Connect tab view signals
        self.tab_view.connect("notify::selected-page", self._on_selected_page_changed)
        self.tab_view.connect("close-page", self._on_close_page)
        self.tab_view.connect("page-attached", lambda *_: self._update_tab_nav_buttons())
        self.tab_view.connect("page-detached", lambda *_: self._update_tab_nav_buttons())
        self.tab_view.connect("page-reordered", lambda *_: self._update_tab_nav_buttons())

        # Create initial default tab
        self.create_new_tab(title=_("Untitled Document"))
        self._update_seek_buttons_visibility()

    def _save_settings(self):
        """Saves settings automatically when the application is closing."""
        self._clear_highlight()
        lang_item = self.lang_chooser.get_selected_item() if hasattr(self, 'lang_chooser') and self.lang_chooser else None
        voice_item = self.voice_chooser.get_selected_item() if hasattr(self, 'voice_chooser') and self.voice_chooser else None

        settings = {
            "language": lang_item.get_string() if lang_item else "",
            "voice": voice_item.get_string() if voice_item else "",
            "pitch": self.adjustment_1.get_value() if hasattr(self, 'adjustment_1') and self.adjustment_1 else 1.0,
            "speed": self.speed_chooser.get_selected() if hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_selected') else (self.adjustment_2.get_value() if hasattr(self, 'adjustment_2') and self.adjustment_2 else 0),
            "text_zoom": getattr(self, "text_zoom_level", 130),
            "auto_remove_tags": self.auto_remove_tags
        }

        config_path = os.path.join(GLib.get_user_data_dir(), "settings.json")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(settings, f)
        except Exception as e:
            print(f"Could not save defaults: {e}")

    def _do_close(self):
        """Closes the window after saving settings."""
        self._force_close = True
        self._save_settings()
        self._cleanup_temp_audio()
        try:
            from .error_logger import mark_clean_exit
            mark_clean_exit()
        except Exception:
            pass
        app = self.get_application()
        if app and hasattr(app, 'bubble') and app.bubble:
            app.bubble.close()
        self.close()

    def _cleanup_temp_audio(self):
        """Cleans up temporary synthesized audio files when closing."""
        readers_to_clean = set()
        if hasattr(self, 'reader') and self.reader:
            readers_to_clean.add(self.reader)
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_n_pages'):
            for i in range(self.tab_view.get_n_pages()):
                page = self.tab_view.get_nth_page(i)
                reader = getattr(page, '_reader', None)
                if reader:
                    readers_to_clean.add(reader)
        for r in readers_to_clean:
            temp_path = getattr(r, 'temp_path', None)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    def _page_has_unexported_audio(self, page):
        """Returns True if the page contains text that has not been exported to audio."""
        text = self._get_text_for_page(page)
        if not text.strip():
            return False
        return getattr(page, '_exported_audio_text', None) != text

    def _get_unexported_audio_pages(self):
        """Returns a list of TabPages that contain unexported text."""
        if not hasattr(self, 'tab_view') or not hasattr(self.tab_view, 'get_n_pages'):
            return []
        unexported = []
        for i in range(self.tab_view.get_n_pages()):
            page = self.tab_view.get_nth_page(i)
            if self._page_has_unexported_audio(page):
                unexported.append(page)
        return unexported

    def _on_close_request(self, window):
        """Intercepts window close and prompts user to export unexported audio."""
        if getattr(self, '_force_close', False):
            return False

        unexported_pages = self._get_unexported_audio_pages()
        if not unexported_pages:
            self._save_settings()
            self._cleanup_temp_audio()
            app = self.get_application()
            if app and hasattr(app, 'bubble') and app.bubble:
                app.bubble.close()
            return False

        if self.is_playing:
            self.stop_playback()

        dialog = Adw.AlertDialog(
            heading=_("Export Audio Before Closing?"),
            body=_("There are audio files that have not been exported yet. Do you wish to export the current tab or all tabs before closing?")
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("discard", _("Close Without Exporting"))
        dialog.add_response("current", _("Current Tab"))
        dialog.add_response("all", _("All Tabs"))

        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("current", Adw.ResponseAppearance.DEFAULT)
        dialog.set_response_appearance("all", Adw.ResponseAppearance.SUGGESTED)

        def on_choose(dlg, result):
            try:
                choice = dlg.choose_finish(result)
            except Exception:
                return

            if choice == "discard":
                self._do_close()
            elif choice == "current":
                current_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') else None
                target_page = current_page if (current_page and self._get_text_for_page(current_page).strip()) else unexported_pages[0]
                self._export_audio_for_page(
                    target_page,
                    on_complete=self._do_close
                )
            elif choice == "all":
                pages_to_export = [
                    (p, self._get_text_for_page(p))
                    for p in unexported_pages
                ]
                self._export_all_tabs_audio_dialog(
                    pages_to_export=pages_to_export,
                    on_complete=self._do_close
                )

        dialog.choose(self, None, on_choose)
        return True

    def show_wait_dialog(self, batch_text=None):
        if hasattr(self, '_batch_export_status') and self._batch_export_status and not batch_text:
            batch_text = self._batch_export_status

        if hasattr(self, 'wait_dialog') and self.wait_dialog:
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.set_fraction(0.0)
            if hasattr(self, 'batch_label') and self.batch_label:
                if batch_text:
                    self.batch_label.set_text(batch_text)
                    self.batch_label.set_visible(True)
                else:
                    self.batch_label.set_visible(False)
            if hasattr(self, 'progress_label') and self.progress_label:
                self.progress_label.set_text(_("Preparing audio..."))
            return

        self._allow_dialog_close = False
        self.wait_dialog = Gtk.Window(
            transient_for=self,
            modal=True,
            decorated=False,
            resizable=False,
            deletable=False,
        )
        self.wait_dialog.add_css_class("transparent-loading-window")
        self.wait_dialog.connect("close-request", lambda w: not getattr(self, '_allow_dialog_close', False))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.add_css_class("osd")
        box.add_css_class("loading-indicator-box")

        self.spinner = Adw.Spinner()
        self.spinner.set_size_request(36, 36)
        box.append(self.spinner)

        self.batch_label = Gtk.Label()
        self.batch_label.set_margin_top(10)
        self.batch_label.add_css_class("batch-label")
        if batch_text:
            self.batch_label.set_text(batch_text)
            self.batch_label.set_visible(True)
        else:
            self.batch_label.set_visible(False)
        box.append(self.batch_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_size_request(240, -1)
        self.progress_bar.set_margin_top(12)
        box.append(self.progress_bar)

        self.progress_label = Gtk.Label()
        self.progress_label.set_text(_("Preparing audio..."))
        self.progress_label.set_margin_top(8)
        self.progress_label.add_css_class("progress-label")
        box.append(self.progress_label)

        self.cancel_button = Gtk.Button(label=_("Cancel"))
        self.cancel_button.set_halign(Gtk.Align.CENTER)
        self.cancel_button.add_css_class("pill")
        self.cancel_button.add_css_class("cancel-generation-button")
        self.cancel_button.connect("clicked", self._on_cancel_generation_clicked)
        box.append(self.cancel_button)

        self.wait_dialog.set_child(box)

        # Key controller for Escape key cancellation
        key_controller = Gtk.EventControllerKey()
        def on_key_pressed(controller, keyval, keycode, state):
            if keyval == Gdk.KEY_Escape:
                self._on_cancel_generation_clicked()
                return True
            return False
        key_controller.connect("key-pressed", on_key_pressed)
        self.wait_dialog.add_controller(key_controller)

        self.wait_dialog.present()

    def update_wait_dialog(self, fraction, text=None, batch_text=None):
        """Updates the progress bar fraction and countdown status label on the loading HUD."""
        if hasattr(self, 'wait_dialog') and self.wait_dialog:
            if hasattr(self, 'progress_bar') and self.progress_bar:
                clamped_fraction = max(0.0, min(float(fraction), 1.0))
                self.progress_bar.set_fraction(clamped_fraction)
            if hasattr(self, 'batch_label') and self.batch_label and batch_text is not None:
                self.batch_label.set_text(batch_text)
                self.batch_label.set_visible(bool(batch_text))
            if hasattr(self, 'progress_label') and self.progress_label and text:
                self.progress_label.set_text(text)
        return False

    def hide_wait_dialog(self):
        if hasattr(self, '_batch_export_status'):
            self._batch_export_status = None
        self._allow_dialog_close = True
        if hasattr(self, 'wait_dialog') and self.wait_dialog:
            try:
                self.wait_dialog.set_visible(False)
                self.wait_dialog.close()
            except Exception:
                pass
            self.wait_dialog = None
        self.progress_bar = None
        self.progress_label = None
        self.batch_label = None
        self.cancel_button = None
        return False

    def _on_cancel_generation_clicked(self, widget=None):
        """Cancels active audio generation, aborting synthesis and closing HUD."""
        self._batch_export_cancelled = True
        if hasattr(self, 'reader') and self.reader:
            self.reader.cancel_synthesis()
        self.hide_wait_dialog()
        self.set_sensitive(True)
        self.stop_playback()

    def _scan_models(self):
        """Scans both system and user directories for .onnx models and parses their names."""
        user_dir = os.path.join(GLib.get_user_data_dir(), "models")
        try:
            os.makedirs(user_dir, exist_ok=True) # Creates the drag-and-drop folder if it doesn't exist
        except OSError:
            pass

        available_models = {}

        # Scan directories
        search_dirs = [str(p) for p in get_model_search_paths() if p.is_dir()]

        for search_dir in search_dirs:
            for filepath in glob.glob(f"{search_dir}/*.onnx"):
                filename = os.path.basename(filepath)

                # e.g., "en_GB-cori-high.onnx" -> ["en_GB", "cori", "high"]
                base_name = filename.replace(".onnx", "")
                parts = base_name.split("-")

                if len(parts) >= 3:
                    locale_str = parts[0]
                    voice_name = parts[1].capitalize()
                    quality = parts[2].capitalize()

                    # Parse "en_GB" into "English (UK)"
                    if "_" in locale_str:
                        lang_code, country_code = locale_str.split("_", 1)
                        lang = self.LANG_MAP.get(lang_code, lang_code.upper())
                        country = self.COUNTRY_MAP.get(country_code, country_code.upper())
                        display_lang = f"{lang} ({country})"
                    else:
                        display_lang = self.LANG_MAP.get(locale_str, locale_str.upper())

                    # Organize into our dictionary
                    if display_lang not in available_models:
                        available_models[display_lang] = []

                    # Map quality to user-friendly descriptors
                    quality_descriptors = {
                        "High": "High quality - (Slow to generate)",
                        "Medium": "Medium quality - (Optimised speed to generate)",
                        "Low": "Low quality - (Fast to generate)"
                    }
                    quality_text = quality_descriptors.get(quality, f"{quality} quality")

                    # Format: "Cori Voice - High quality - (Slow to generate)"
                    display_voice = f"{voice_name} Voice - {quality_text}"

                    # Prevent duplicates
                    if not any(v['id'] == base_name for v in available_models[display_lang]):
                        available_models[display_lang].append({
                            "id": base_name,
                            "display_name": display_voice,
                            "path": filepath,
                            "lang_code": locale_str,
                            "raw_voice_name": parts[1]
                        })

        return available_models

    def _show_error(self, message, exc=None, traceback_text=None, context=None, **kwargs):
        log_path = None
        try:
            from .error_logger import log_error
            log_path = log_error(
                str(message),
                exc=exc,
                traceback_text=traceback_text,
                context=context or "Application Window",
            )
        except Exception as log_err:
            print(f"Warning: Failed to log error: {log_err}")

        body_text = str(message)
        if log_path:
            body_text = f"{body_text}\n\n{_('A detailed error log has been saved to:')}\n{log_path}"

        dialog = Adw.AlertDialog(
            heading=_("Error"),
            body=body_text
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        try:
            dialog.present(self)
        except Exception:
            pass
        return dialog

    def _setup_dropdown_excerpt(self, dropdown, max_chars=None, show_selection_check=False, icon_name=None):
        """Configures a dropdown to display full text without excerpt in the popup list,
        optionally displaying a selection tick next to the currently selected option,
        and full text on the button with responsive ellipsizing if window space is constrained."""

        # --- List factory: full text in the popup with no excerpt ---
        list_factory = Gtk.SignalListItemFactory()

        def _on_list_setup(factory, list_item):
            label = Gtk.Label(xalign=0.0)
            list_item.set_child(label)

        def _on_list_bind(factory, list_item):
            label = list_item.get_child()
            item = list_item.get_item()
            if isinstance(item, Gtk.StringObject):
                raw_text = item.get_string()

                def _update_label_text(*_):
                    pos = list_item.get_position() if hasattr(list_item, 'get_position') else -1
                    is_selected = (pos >= 0 and pos == dropdown.get_selected())
                    if show_selection_check and is_selected:
                        label.set_text(f"✓  {raw_text}")
                    else:
                        label.set_text(raw_text)

                _update_label_text()
                if show_selection_check and hasattr(list_item, 'get_position'):
                    handler_id = dropdown.connect("notify::selected", _update_label_text)
                    list_item._notify_handler_id = handler_id

        def _on_list_unbind(factory, list_item):
            if show_selection_check:
                handler_id = getattr(list_item, '_notify_handler_id', None)
                if handler_id and dropdown.handler_is_connected(handler_id):
                    dropdown.disconnect(handler_id)
                    list_item._notify_handler_id = None

        list_factory.connect("setup", _on_list_setup)
        list_factory.connect("bind", _on_list_bind)
        if show_selection_check:
            list_factory.connect("unbind", _on_list_unbind)
        dropdown.set_list_factory(list_factory)

        # --- Button factory: full text on closed button, responsive ellipsize if space is constrained ---
        button_factory = Gtk.SignalListItemFactory()

        def _on_setup(factory, list_item):
            if icon_name:
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                img = Gtk.Image.new_from_icon_name(icon_name)
                label = Gtk.Label(xalign=0.0)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                box.append(img)
                box.append(label)
                list_item.set_child(box)
            else:
                label = Gtk.Label(xalign=0.0)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                list_item.set_child(label)

        def _on_bind(factory, list_item):
            child = list_item.get_child()
            if icon_name and isinstance(child, Gtk.Box):
                label = child.get_last_child()
            else:
                label = child
            item = list_item.get_item()
            if isinstance(item, Gtk.StringObject):
                text = item.get_string()
                if max_chars is not None and len(text) > max_chars:
                    label.set_text(text[:max_chars].rstrip() + "...")
                else:
                    label.set_text(text)
                label.set_tooltip_text(text)

        button_factory.connect("setup", _on_setup)
        button_factory.connect("bind", _on_bind)
        dropdown.set_factory(button_factory)

        # --- Auto-scroll popup list to selected item when opened ---
        def _find_widget(root, target_type):
            if isinstance(root, target_type):
                return root
            if hasattr(root, 'get_first_child'):
                child = root.get_first_child()
                while child:
                    res = _find_widget(child, target_type)
                    if res:
                        return res
                    child = child.get_next_sibling()
            return None

        popover = _find_widget(dropdown, Gtk.Popover)
        if popover:
            def _scroll_to_selected(*_):
                selected = dropdown.get_selected()
                if selected < 0:
                    return
                list_view = _find_widget(popover, Gtk.ListView)
                if not list_view:
                    return
                try:
                    list_view.scroll_to(selected, Gtk.ListScrollFlags.NONE, None)
                except Exception:
                    pass

                def _center():
                    scrolled = list_view.get_ancestor(Gtk.ScrolledWindow) if hasattr(list_view, 'get_ancestor') else None
                    if scrolled and hasattr(scrolled, 'get_vadjustment'):
                        vadj = scrolled.get_vadjustment()
                        upper = vadj.get_upper()
                        page_size = vadj.get_page_size()
                        model = dropdown.get_model()
                        n = model.get_n_items() if model and hasattr(model, 'get_n_items') else 0
                        if n > 0 and upper > page_size:
                            item_h = upper / n
                            center_y = (selected + 0.5) * item_h - (page_size / 2.0)
                            target_val = max(0.0, min(center_y, upper - page_size))
                            vadj.set_value(target_val)

                GLib.timeout_add(30, _center)

            def _on_popover_visible(p, _param):
                if p.get_visible():
                    GLib.idle_add(_scroll_to_selected)

            popover.connect("notify::visible", _on_popover_visible)

    def _set_button_icon(self, button, icon_name, size=25):
        """Sets the icon name on a button while ensuring the internal image maintains custom pixel size."""
        if hasattr(button, 'set_icon_name'):
            button.set_icon_name(icon_name)
        if hasattr(button, 'get_child'):
            child = button.get_child()
            if isinstance(child, Gtk.Image):
                child.set_pixel_size(size)

    def _setup_lang_chooser(self):
        # Scan for models dynamically
        self.installed_models = self._scan_models()
        self.lang_name_to_code = {}

        lang_model = Gtk.StringList.new()

        saved_lang = self.default_settings.get("language")
        if saved_lang == "English (United Kingdom)":
            saved_lang = "English (UK)"
        elif saved_lang == "English (United States)":
            saved_lang = "English (US)"
        selected_idx = 0

        # Populate language dropdown
        for i, lang in enumerate(sorted(self.installed_models.keys())):
            lang_model.append(lang)
            if lang == saved_lang:
                selected_idx = i
            if self.installed_models[lang]:
                self.lang_name_to_code[lang] = self.installed_models[lang][0]["lang_code"]

        self.lang_chooser.set_model(lang_model)

        if self.installed_models and lang_model.get_n_items() > 0:
            self.lang_chooser.set_selected(selected_idx)
            first_lang = lang_model.get_string(selected_idx)
            self.lang_code = self.lang_name_to_code.get(first_lang, "en")
            self._update_voice_chooser(first_lang)

        # Connect signal
        self.lang_chooser.connect("notify::selected", self._on_lang_changed)

    def _on_lang_changed(self, dropdown, _):
        item = self.lang_chooser.get_selected_item()
        if item:
            lang_name = item.get_string()
            self.lang_code = self.lang_name_to_code.get(lang_name, "en")
            self._update_voice_chooser(lang_name)

    def _update_voice_chooser(self, display_lang):
        """Dynamically updates and sorts the dropdown selection alphabetically"""
        self.installed_models = self._scan_models()
        voices = self.installed_models.get(display_lang, [])

        # Sort voices alphabetically by display name
        sorted_voices = sorted(voices, key=lambda v: v['display_name'])

        model = Gtk.StringList.new()
        self.current_voices = []

        saved_voice = self.default_settings.get("voice")
        selected_idx = 0

        for i, voice in enumerate(sorted_voices):
            model.append(voice['display_name'])
            self.current_voices.append(voice)
            if voice['display_name'] == saved_voice:
                selected_idx = i

        self.voice_chooser.set_model(model)

        if model.get_n_items() > 0:
            self.voice_chooser.set_selected(selected_idx)

    ## ================================================================##
    # Dialog for opening a file is defined
    def open_file_dialog(self, action=None, param=None):
        self.set_auto_remove_tags(True)
        # Create a new file selection dialog, using the "open" mode
        native = Gtk.FileDialog()

        filter_all_supported = Gtk.FileFilter()
        filter_all_supported.set_name(_("Supported Documents (*.txt, *.md, *.pdf, *.epub)"))
        filter_all_supported.add_pattern("*.txt")
        filter_all_supported.add_pattern("*.md")
        filter_all_supported.add_pattern("*.pdf")
        filter_all_supported.add_pattern("*.epub")

        filter_books = Gtk.FileFilter()
        filter_books.set_name(_("Books & PDF (*.pdf, *.epub)"))
        filter_books.add_pattern("*.pdf")
        filter_books.add_pattern("*.epub")

        filter_txt = Gtk.FileFilter()
        filter_txt.set_name(_("Text Documents (*.txt, *.md)"))
        filter_txt.add_pattern("*.txt")
        filter_txt.add_pattern("*.md")

        filter_all = Gtk.FileFilter()
        filter_all.set_name(_("All Files"))
        filter_all.add_pattern("*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_all_supported)
        filters.append(filter_books)
        filters.append(filter_txt)
        filters.append(filter_all)
        native.set_filters(filters)
        native.set_default_filter(filter_all_supported)

        native.open(self, None, self.on_open_response)

    # Dialog for saving a text file is defined
    def save_text_dialog(self, action=None, param=None):
        page = self.tab_view.get_selected_page() if (hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page')) else None
        title = page.get_title() if page else "text"
        default_name = f"{title}.txt" if title and not title.endswith(".txt") else "text.txt"
        default_name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', '', default_name)
        if not default_name.endswith(".txt"):
            default_name += ".txt"
        native = Gtk.FileDialog()
        native.set_initial_name(default_name)
        native.save(self, None, self.on_save_text_response)

    def _get_text_for_saving(self):
        if not self.main_text_view:
            return ""
        buffer = self.main_text_view.get_buffer()
        selection = buffer.get_selection_bounds()
        if selection:
            return buffer.get_text(selection[0], selection[1], False)
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def _get_selected_voice_name(self):
        selected_idx = self.voice_chooser.get_selected()
        if hasattr(self, 'current_voices') and 0 <= selected_idx < len(self.current_voices):
            return self.current_voices[selected_idx].get('id', self.current_voices[selected_idx].get('raw_voice_name', ''))
        item = self.voice_chooser.get_selected_item()
        return item.get_string() if item else ""

    def _generate_default_audio_filename(self, text):
        """Generates a default audio export filename in format:
        Day - Month - Year - First 5 words of the text input, for example:
        06 Sep 2026 - Hello World.mp3
        """
        now = datetime.datetime.now()
        date_str = now.strftime("%d %b %Y")
        words = text.strip().split()[:5]
        clean_words = [re.sub(r'[\\/*?:"<>|\x00-\x1f]', '', w) for w in words]
        clean_words = [w.strip() for w in clean_words if w.strip()]
        words_part = " ".join(clean_words) if clean_words else "Audio"
        if len(words_part) > 80:
            words_part = words_part[:80].rstrip()
        return f"{date_str} - {words_part}.mp3"

    ## ================================================================##
    # Tab Management
    def create_new_tab(self, title=None, text="", file=None):
        """Creates a new tab with its own ScrolledWindow and GtkTextView."""
        if not hasattr(self, '_tab_counter') or self._tab_counter is None:
            self._tab_counter = 0
        self._tab_counter += 1
        if title is None:
            if self._tab_counter == 1 and self.tab_view.get_n_pages() == 0:
                title = _("Untitled Document")
            else:
                title = f"{_('Untitled')} {self._tab_counter}"

        scrolled_window = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
            margin_top=0,
            margin_bottom=0,
            margin_start=0,
            margin_end=0
        )

        text_view = HighlightTextView(
            top_margin=6,
            bottom_margin=350,
            left_margin=12,
            right_margin=12,
            wrap_mode=Gtk.WrapMode.WORD_CHAR
        )
        text_view._window = self
        text_view.add_css_class("zoomable-text")

        # Mouse scroll controller for Ctrl + Mouse Wheel zoom on text box
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll_controller.connect("scroll", self._on_scroll)
        text_view.add_controller(scroll_controller)

        buffer = text_view.get_buffer()
        buffer.create_tag(
            "current_word_highlight",
            foreground="#000000"
        )
        buffer.connect("changed", self._on_buffer_changed_for_drop_placeholder)
        if text:
            initial_text = clean_all_tags(text) if self.auto_remove_tags else text
            buffer.set_text(ensure_paragraph_gaps(initial_text))

        scrolled_window.set_child(text_view)

        page = self.tab_view.append(scrolled_window)
        page.set_title(title)
        page.set_tooltip(title)
        page._file = file
        page._reader = None
        page._is_playing = False
        page._is_paused = False
        page._paused_offset = 0
        page._highlight_index = None

        self.tab_view.set_selected_page(page)
        self._update_drop_placeholder_visibility()
        self._update_tab_nav_buttons()
        text_view.grab_focus()
        return page

    def load_text_and_play(self, text, title=None):
        """Creates a new tab with the provided text, presents the window, and begins playback."""
        if not text or not text.strip():
            return None

        if self.is_playing:
            self.stop_playback()

        clean_text = text.strip()
        if not title:
            first_line = clean_text.splitlines()[0].strip()
            if len(first_line) > 500:
                first_line = first_line[:500] + "…"
            title = f"{_('Quick Read')}: {first_line}" if first_line else _("Quick Read")

        page = self.create_new_tab(title=title, text=clean_text)
        self.present()

        if self.main_text_view:
            buffer = self.main_text_view.get_buffer()
            start_iter = buffer.get_start_iter()
            buffer.place_cursor(start_iter)

        self.read_text(self.read_button)
        return page

    def _ensure_at_least_one_tab(self):
        """Ensures that there is always at least one open tab in the window."""
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_n_pages') and self.tab_view.get_n_pages() == 0:
            self.create_new_tab()

    def _on_tab_bar_enter(self, controller=None, x=0, y=0):
        """Reveals tab navigation buttons when hovering over the tab bar."""
        self._tab_bar_is_hovered = True
        self._update_tab_nav_buttons(is_hovered=True)

    def _on_tab_bar_leave(self, controller=None):
        """Hides tab navigation buttons when the cursor leaves the tab bar."""
        self._tab_bar_is_hovered = False
        self._update_tab_nav_buttons(is_hovered=False)

    def _find_tab_bar_scrolled_window(self):
        """Recursively finds the main non-pinned GtkScrolledWindow inside AdwTabBar."""
        if not hasattr(self, 'tab_bar') or not self.tab_bar:
            return None
        queue = [self.tab_bar]
        main_sw = None
        while queue:
            curr = queue.pop(0)
            if isinstance(curr, Gtk.ScrolledWindow):
                if "pinned" not in curr.get_css_classes():
                    return curr
                main_sw = curr
            child = curr.get_first_child() if hasattr(curr, 'get_first_child') else None
            while child:
                queue.append(child)
                child = child.get_next_sibling() if hasattr(child, 'get_next_sibling') else None
        return main_sw

    def _scroll_tab_bar_to_selected_tab(self):
        """Smoothly adjusts the tab bar scrolled window so the selected tab is in view."""
        if not hasattr(self, 'tab_view') or not self.tab_view:
            return
        if not hasattr(self.tab_view, 'get_selected_page'):
            return
        page = self.tab_view.get_selected_page()
        if not page or not hasattr(self.tab_view, 'get_page_position'):
            return
        try:
            idx = int(self.tab_view.get_page_position(page))
            n_pages = int(self.tab_view.get_n_pages())
        except (TypeError, ValueError):
            return
        sw = self._find_tab_bar_scrolled_window()
        if not sw or not hasattr(sw, 'get_hadjustment'):
            return
        hadj = sw.get_hadjustment()
        if not hadj or not hasattr(hadj, 'get_value'):
            return

        # Try to find the exact tab widget corresponding to idx
        tab_box = sw.get_child() if hasattr(sw, 'get_child') else None
        if tab_box:
            tabs = []
            child = tab_box.get_first_child() if hasattr(tab_box, 'get_first_child') else None
            while child:
                if hasattr(child, 'get_css_name') and child.get_css_name() == 'tabboxchild':
                    tabs.append(child)
                child = child.get_next_sibling() if hasattr(child, 'get_next_sibling') else None

            if 0 <= idx < len(tabs):
                target_tab = tabs[idx]
                if hasattr(target_tab, 'compute_bounds'):
                    ok, rect = target_tab.compute_bounds(tab_box)
                    if ok:
                        val = hadj.get_value()
                        ps = hadj.get_page_size()
                        tx = rect.get_x()
                        tw = rect.get_width()
                        if tx < 0:
                            hadj.set_value(max(hadj.get_lower(), val + tx - 12))
                            return
                        elif tx + tw > ps:
                            hadj.set_value(min(hadj.get_upper() - ps, val + (tx + tw - ps) + 12))
                            return
                        else:
                            return

        # Fallback proportional scroll if compute_bounds is not yet available or bounds check fell through
        try:
            ps = hadj.get_page_size()
            upper = hadj.get_upper()
            if upper > ps and n_pages > 1:
                target_val = (idx / (n_pages - 1)) * (upper - ps)
                hadj.set_value(target_val)
        except Exception:
            pass

    def _update_tab_nav_buttons(self, is_hovered=None):
        """Updates visibility, sensitivity, and positioning of tab navigation buttons."""
        if is_hovered is not None:
            self._tab_bar_is_hovered = is_hovered

        if not hasattr(self, 'tab_view') or not self.tab_view:
            return

        try:
            n_pages = int(self.tab_view.get_n_pages())
        except (TypeError, ValueError):
            n_pages = 0

        should_reveal = bool(n_pages >= 2 and getattr(self, '_tab_bar_is_hovered', False))

        if hasattr(self, 'tab_nav_prev_revealer') and self.tab_nav_prev_revealer:
            if hasattr(self.tab_nav_prev_revealer, 'set_reveal_child'):
                self.tab_nav_prev_revealer.set_reveal_child(should_reveal)
            if hasattr(self.tab_nav_prev_revealer, 'set_can_target'):
                self.tab_nav_prev_revealer.set_can_target(should_reveal)
        if hasattr(self, 'tab_nav_next_revealer') and self.tab_nav_next_revealer:
            if hasattr(self.tab_nav_next_revealer, 'set_reveal_child'):
                self.tab_nav_next_revealer.set_reveal_child(should_reveal)
            if hasattr(self.tab_nav_next_revealer, 'set_can_target'):
                self.tab_nav_next_revealer.set_can_target(should_reveal)
            if hasattr(self, 'tab_bar_end_box') and self.tab_bar_end_box and hasattr(self.tab_bar_end_box, 'get_width'):
                end_w = self.tab_bar_end_box.get_width()
                if isinstance(end_w, (int, float)) and end_w > 0:
                    if hasattr(self.tab_nav_next_revealer, 'set_margin_end'):
                        self.tab_nav_next_revealer.set_margin_end(int(end_w) + 4)

        cur_page = self.tab_view.get_selected_page() if hasattr(self.tab_view, 'get_selected_page') else None
        if cur_page and hasattr(self.tab_view, 'get_page_position'):
            try:
                cur_idx = int(self.tab_view.get_page_position(cur_page))
            except (TypeError, ValueError):
                cur_idx = 0
        else:
            cur_idx = 0

        if hasattr(self, 'tab_nav_prev_btn') and self.tab_nav_prev_btn and hasattr(self.tab_nav_prev_btn, 'set_sensitive'):
            self.tab_nav_prev_btn.set_sensitive(cur_idx > 0)
        if hasattr(self, 'tab_nav_next_btn') and self.tab_nav_next_btn and hasattr(self.tab_nav_next_btn, 'set_sensitive'):
            self.tab_nav_next_btn.set_sensitive(cur_idx < n_pages - 1)

    def navigate_previous_tab(self):
        """Switches to the previous tab and smoothly scrolls the tab bar to make it visible."""
        if not hasattr(self, 'tab_view') or not self.tab_view:
            return
        if self.tab_view.select_previous_page():
            self._scroll_tab_bar_to_selected_tab()
            self._update_tab_nav_buttons()

    def navigate_next_tab(self):
        """Switches to the next tab and smoothly scrolls the tab bar to make it visible."""
        if not hasattr(self, 'tab_view') or not self.tab_view:
            return
        if self.tab_view.select_next_page():
            self._scroll_tab_bar_to_selected_tab()
            self._update_tab_nav_buttons()

    def _on_selected_page_changed(self, tab_view, pspec=None):
        """Callback when the active tab is switched."""
        prev_page = getattr(self, '_active_tab_page', None)
        cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None

        # Switching away from prev_page: if audio was playing on prev_page, pause it and record state
        if prev_page is not None and prev_page != cur_page:
            if getattr(self, 'is_playing', False):
                if not getattr(self, 'is_paused', False):
                    if hasattr(self, 'reader') and self.reader and hasattr(self.reader, 'pause_audio'):
                        try:
                            self.reader.pause_audio()
                        except Exception:
                            pass
                char_offset = self._get_current_playback_char_offset()
                prev_page._reader = getattr(self, 'reader', None)
                prev_page._is_playing = True
                prev_page._is_paused = True
                prev_page._paused_offset = char_offset
                prev_page._highlight_index = getattr(self, '_current_highlight_index', None)

                # Set pause_resume_mark on prev_page's buffer without clearing word highlight
                prev_tv = self._get_text_view_for_page(prev_page)
                if prev_tv:
                    buf = prev_tv.get_buffer()
                    total_chars = buf.get_char_count()
                    clamped_offset = max(0, min(char_offset, total_chars))
                    iter_at_pause = buf.get_iter_at_offset(clamped_offset)
                    mark = buf.get_mark("pause_resume_mark")
                    if mark:
                        buf.move_mark(mark, iter_at_pause)
                    else:
                        buf.create_mark("pause_resume_mark", iter_at_pause, left_gravity=False)
                    buf.place_cursor(iter_at_pause)

                # Stop the highlight polling timer while on another tab
                if getattr(self, '_highlight_timeout_id', None) is not None:
                    try:
                        GLib.source_remove(self._highlight_timeout_id)
                    except Exception:
                        pass
                    self._highlight_timeout_id = None
        elif prev_page is None and getattr(self, 'is_playing', False):
            # Fallback if _active_tab_page was not previously tracked: pause active reader
            if hasattr(self, 'reader') and self.reader and hasattr(self.reader, 'pause_audio'):
                try:
                    self.reader.pause_audio()
                except Exception:
                    pass
            if getattr(self, '_highlight_timeout_id', None) is not None:
                try:
                    GLib.source_remove(self._highlight_timeout_id)
                except Exception:
                    pass
                self._highlight_timeout_id = None

        self._active_tab_page = cur_page

        if cur_page:
            page_reader = getattr(cur_page, '_reader', None)
            page_is_playing = getattr(cur_page, '_is_playing', False)
            page_is_paused = getattr(cur_page, '_is_paused', False)

            if page_is_playing and page_is_paused:
                self.reader = page_reader
                self.is_playing = True
                self.is_paused = True
                self._current_highlight_index = getattr(cur_page, '_highlight_index', None)
                if hasattr(self, 'pause_button') and self.pause_button:
                    self.pause_button.set_sensitive(True)
                    self._set_button_icon(self.pause_button, "media-playback-start-symbolic", 25)
                    self.pause_button.set_tooltip_text(_("Resume"))
                if hasattr(self, 'read_button') and self.read_button:
                    self._set_button_icon(self.read_button, "media-playback-stop-symbolic", 25)
                    self.read_button.set_tooltip_text(_("Stop"))
                self._notify_bubble_playback_state()
            else:
                self.reader = page_reader
                self.is_playing = False
                self.is_paused = False
                self._current_highlight_index = None
                if hasattr(self, 'pause_button') and self.pause_button:
                    self.pause_button.set_sensitive(False)
                    self._set_button_icon(self.pause_button, "media-playback-pause-symbolic", 25)
                    self.pause_button.set_tooltip_text(_("Pause"))
                if hasattr(self, 'read_button') and self.read_button:
                    self._set_button_icon(self.read_button, "media-playback-start-symbolic", 25)
                    self.read_button.set_tooltip_text(_("Read Text"))
                self._notify_bubble_playback_state()

            self._update_seek_buttons_visibility()

        self._update_drop_placeholder_visibility()
        self._scroll_tab_bar_to_selected_tab()
        self._update_tab_nav_buttons()

    def _get_text_view_for_page(self, page):
        """Helper to get GtkTextView from an AdwTabPage."""
        if not page:
            return None
        sw = page.get_child()
        if not sw or not hasattr(sw, 'get_child'):
            return None
        return sw.get_child()

    def _on_buffer_changed_for_drop_placeholder(self, buffer):
        """Update the drop placeholder visibility when the buffer text changes."""
        placeholder = getattr(self, 'drop_placeholder', None)
        if not isinstance(placeholder, Gtk.Widget):
            return
        cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
        if cur_page:
            tv = self._get_text_view_for_page(cur_page)
            if tv and tv.get_buffer() == buffer:
                has_text = buffer.get_char_count() > 0
                placeholder.set_visible(not has_text)

    def _update_drop_placeholder_visibility(self):
        """Show the drag and drop explanation if the active tab has no text; hide if text is present."""
        placeholder = getattr(self, 'drop_placeholder', None)
        if not isinstance(placeholder, Gtk.Widget):
            return
        if not hasattr(self, 'tab_view') or not hasattr(self.tab_view, 'get_selected_page'):
            return
        cur_page = self.tab_view.get_selected_page()
        if not cur_page:
            placeholder.set_visible(True)
            return
        cur_text = self._get_text_for_page(cur_page)
        has_text = len(cur_text) > 0
        placeholder.set_visible(not has_text)

    def _on_placeholder_clicked(self, gesture, n_press, x, y):
        """When placeholder is clicked, focus the active tab's textview."""
        if self.main_text_view:
            self.main_text_view.grab_focus()

    def _on_drop_enter(self, target, x, y):
        placeholder = getattr(self, 'drop_placeholder', None)
        if isinstance(placeholder, Gtk.Widget):
            placeholder.add_css_class("drag-hover")
        return Gdk.DragAction.COPY

    def _on_drop_leave(self, target):
        placeholder = getattr(self, 'drop_placeholder', None)
        if isinstance(placeholder, Gtk.Widget):
            placeholder.remove_css_class("drag-hover")

    def _normalize_loaded_items(self, items):
        """Normalizes dropped items into (title, text, file) tuples."""
        normalized = []
        for item in items:
            if len(item) == 3:
                title, text, f = item
                normalized.append((title, text, f))
            elif len(item) == 2:
                first, text = item
                if hasattr(first, 'get_basename'):
                    normalized.append((first.get_basename(), text, first))
                elif isinstance(first, str):
                    normalized.append((first, text, None))
                else:
                    normalized.append((str(first), text, None))
        return normalized

    def _alert_incompatible_files(self, invalid_files=None):
        """Alerts the user that ReadAloud is compatible with TXT, MD, PDF, and EPUB files."""
        heading = _("Incompatible File Format")
        body = _("ReadAloud is compatible with TXT, MD, PDF, and EPUB files.")
        if invalid_files:
            file_list_str = ", ".join(f"'{name}'" for name in invalid_files[:3])
            if len(invalid_files) > 3:
                file_list_str += f" and {len(invalid_files) - 3} more"
            body += f"\n\n{_('The following file(s) cannot be imported')}: {file_list_str}\n{_('Please drop files with .txt, .md, .pdf, or .epub extensions.')}"

        dialog = Adw.AlertDialog(
            heading=heading,
            body=body
        )
        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        dialog.choose(self, None, None)

    def _on_files_dropped(self, drop_target, value, x, y):
        """Handle drag and drop of files into the application."""
        self.set_auto_remove_tags(True)
        placeholder = getattr(self, 'drop_placeholder', None)
        if isinstance(placeholder, Gtk.Widget):
            placeholder.remove_css_class("drag-hover")

        files = []
        if hasattr(value, 'get_files'):
            files = list(value.get_files())
        elif isinstance(value, (list, tuple)):
            files = list(value)

        if not files:
            return False

        # Validate file extensions: TXT, MD, PDF, and EPUB allowed
        SUPPORTED_EXTS = ('.txt', '.md', '.pdf', '.epub')
        invalid_files = []
        for f in files:
            name = f.get_basename() or ""
            root, ext = os.path.splitext(name.lower())
            if ext not in SUPPORTED_EXTS:
                invalid_files.append(name)

        if invalid_files:
            self._alert_incompatible_files(invalid_files)
            return True

        # Load file contents and extract chapters
        loaded_items = []
        for f in files:
            name = f.get_basename() or ""
            try:
                success, contents, _ = f.load_contents(None)
                if not success:
                    continue
                chapters = load_document_chapters(f, filename=name, raw_bytes=contents)
                for ch_title, ch_text in chapters:
                    if ch_text.strip():
                        loaded_items.append((ch_title, ch_text, f))
            except Exception as e:
                print(f"Error loading dropped file {name}: {e}")

        if not loaded_items:
            return True

        # Check if the currently active tab already contains text
        cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
        cur_text = self._get_text_for_page(cur_page) if cur_page else ""
        has_text = bool(cur_text.strip())

        if has_text:
            # Active tab already has text: prompt user
            self._prompt_dropped_files_import_choice(loaded_items)
        else:
            # Active tab is empty: prompt user with tag stripping options
            self._prompt_empty_tab_import(loaded_items, cur_page)

        return True

    def _create_tag_stripping_checkbox_box(self):
        """Creates a Gtk.Box with checkbuttons and a 'Select All' button for stripping tags on import."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        box.set_margin_start(16)
        box.set_margin_end(16)

        btn_select_all = Gtk.Button(label=_("Select All"))
        btn_select_all.set_halign(Gtk.Align.START)
        btn_select_all.set_margin_bottom(2)

        chk_round = Gtk.CheckButton(label=_("Remove ( ) round brackets and text"))
        chk_square = Gtk.CheckButton(label=_("Remove [ ] square brackets and text"))
        chk_pipe = Gtk.CheckButton(label=_("Remove | pipes and text"))
        chk_hash = Gtk.CheckButton(label=_("Remove # hashes"))
        chk_star = Gtk.CheckButton(label=_("Remove * stars (asterisks)"))

        chk_list = [chk_round, chk_square, chk_pipe, chk_hash, chk_star]

        def update_select_all_label():
            all_active = all(c.get_active() for c in chk_list)
            btn_select_all.set_label(_("Deselect All") if all_active else _("Select All"))

        def on_select_all_clicked(_btn):
            all_active = all(c.get_active() for c in chk_list)
            new_state = not all_active
            for c in chk_list:
                c.set_active(new_state)
            update_select_all_label()

        btn_select_all.connect("clicked", on_select_all_clicked)
        for c in chk_list:
            c.connect("toggled", lambda _chk: update_select_all_label())

        box.append(btn_select_all)
        for chk in chk_list:
            chk.set_active(False)
            box.append(chk)

        return box, {
            "round": chk_round,
            "square": chk_square,
            "pipe": chk_pipe,
            "hash": chk_hash,
            "star": chk_star,
            "select_all": btn_select_all,
        }

    def _get_selected_stripping_from_checkboxes(self, check_map):
        """Extracts boolean stripping flags from checkbuttons."""
        if not check_map:
            return {}
        return {
            "strip_round": bool(check_map.get("round") and check_map["round"].get_active()),
            "strip_square": bool(check_map.get("square") and check_map["square"].get_active()),
            "strip_pipe": bool(check_map.get("pipe") and check_map["pipe"].get_active()),
            "strip_hash": bool(check_map.get("hash") and check_map["hash"].get_active()),
            "strip_stars": bool(check_map.get("star") and check_map["star"].get_active()),
        }

    def _apply_stripping_to_loaded_files(self, loaded_files, stripping_options):
        """Applies chosen tag stripping operations to each loaded file's text."""
        if not loaded_files or not stripping_options or not any(stripping_options.values()):
            return loaded_files
        norm_items = self._normalize_loaded_items(loaded_files)
        cleaned = []
        for title, t, f in norm_items:
            cleaned_text = apply_text_tag_stripping(
                t,
                strip_round=stripping_options.get("strip_round", False),
                strip_square=stripping_options.get("strip_square", False),
                strip_pipe=stripping_options.get("strip_pipe", False),
                strip_hash=stripping_options.get("strip_hash", False),
                strip_stars=stripping_options.get("strip_stars", False),
            )
            cleaned.append((title, cleaned_text, f))
        return cleaned

    def _prompt_empty_tab_import(self, loaded_files, cur_page=None):
        """Prompt user when dropping files into an empty tab to optionally choose tag stripping."""
        norm_items = self._normalize_loaded_items(loaded_files)
        heading = _("Import Dropped Document") if len(norm_items) == 1 else _("Import Dropped Documents")
        item_count = len(norm_items)

        distinct_files = set(f_val.get_basename() for t_val, txt_val, f_val in norm_items if f_val and hasattr(f_val, 'get_basename'))
        if len(distinct_files) == 1:
            filename = list(distinct_files)[0]
            if item_count > 1:
                body = _("Import '{filename}' ({count} chapters) into ReadAloud? Select any tags to strip below:").format(
                    filename=filename, count=item_count
                )
            else:
                body = _("Import '{filename}' into ReadAloud? Select any tags to strip below:").format(
                    filename=filename
                )
        elif item_count == 1:
            body = _("Import '{title}' into ReadAloud? Select any tags to strip below:").format(
                title=norm_items[0][0]
            )
        else:
            body = _("Import {count} items into ReadAloud? Select any tags to strip below:").format(count=item_count)

        dialog = Adw.AlertDialog(
            heading=heading,
            body=body
        )
        box, check_map = self._create_tag_stripping_checkbox_box()
        dialog.set_extra_child(box)

        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("import", _("Import"))
        dialog.set_response_appearance("import", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("import")
        dialog.set_close_response("cancel")

        def on_response(dlg, resp):
            if resp == "import":
                stripping_options = self._get_selected_stripping_from_checkboxes(check_map)
                cleaned_files = self._apply_stripping_to_loaded_files(norm_items, stripping_options)
                self._import_dropped_files_into_empty_tab(cleaned_files, cur_page)

        dialog.connect("response", on_response)
        self._last_import_dialog = dialog
        dialog.present(self)
        return dialog

    def _import_dropped_files_into_empty_tab(self, loaded_files, cur_page=None):
        """Imports dropped files when the active tab is empty."""
        if not loaded_files:
            return

        norm_items = self._normalize_loaded_items(loaded_files)
        is_untitled = cur_page and (cur_page.get_title() == _("Untitled Document") or cur_page.get_title().startswith(_("Untitled")))

        if is_untitled:
            first_title, first_text, first_file = norm_items[0]
            tv = self._get_text_view_for_page(cur_page)
            if tv:
                buf = tv.get_buffer()
                buf.set_text(ensure_paragraph_gaps(first_text))
                start = buf.get_start_iter()
                buf.place_cursor(start)
            cur_page.set_title(first_title)
            cur_page.set_tooltip(first_title)
            cur_page._file = first_file

            # Remaining items create new tabs
            for title, t, f in norm_items[1:]:
                self.create_new_tab(title=title, text=t, file=f)
        else:
            for title, t, f in norm_items:
                self.create_new_tab(title=title, text=t, file=f)

        self._update_drop_placeholder_visibility()

    def _prompt_dropped_files_import_choice(self, loaded_files):
        """Prompt user when dropping files into a tab that already contains text."""
        norm_items = self._normalize_loaded_items(loaded_files)
        heading = _("Import Dropped Documents")
        item_count = len(norm_items)

        distinct_files = set(f_val.get_basename() for t_val, txt_val, f_val in norm_items if f_val and hasattr(f_val, 'get_basename'))
        if len(distinct_files) == 1:
            filename = list(distinct_files)[0]
            if item_count > 1:
                body = _("The current tab already contains text. Choose how to import '{filename}' ({count} chapters) and select tags to strip:").format(filename=filename, count=item_count)
            else:
                body = _("The current tab already contains text. Choose how to import '{filename}' and select tags to strip:").format(filename=filename)
        elif item_count == 1:
            body = _("The current tab already contains text. Choose how to import '{title}' and select tags to strip:").format(title=norm_items[0][0])
        else:
            body = _("The current tab already contains text. Choose how to import {count} items and select tags to strip:").format(count=item_count)

        dialog = Adw.AlertDialog(
            heading=heading,
            body=body
        )
        box, check_map = self._create_tag_stripping_checkbox_box()
        dialog.set_extra_child(box)

        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("existing", _("Import into Existing Tab"))
        tabs_label = _("Create New Tabs per Chapter") if (len(distinct_files) == 1 and item_count > 1) else _("Create New Tabs per File")
        dialog.add_response("new_tabs", tabs_label)
        dialog.add_response("all_in_one", _("All into One New Tab"))
        dialog.set_default_response("new_tabs")
        dialog.set_close_response("cancel")

        dialog.connect("response", lambda dlg, resp: self._on_import_choice_response(resp, norm_items, check_map))
        self._last_import_dialog = dialog
        dialog.present(self)
        return dialog

    def _on_import_choice_response(self, response, loaded_files, check_map=None):
        """Handle response from import choice prompt dialog."""
        if not isinstance(response, str):
            return
        if response == "cancel":
            return

        norm_items = self._normalize_loaded_items(loaded_files)

        if check_map:
            stripping_options = self._get_selected_stripping_from_checkboxes(check_map)
            norm_items = self._apply_stripping_to_loaded_files(norm_items, stripping_options)

        if response == "existing":
            tv = self.main_text_view
            if tv:
                buffer = tv.get_buffer()
                buffer.begin_user_action()
                end_iter = buffer.get_end_iter()
                combined_text = "\n\n".join(ensure_paragraph_gaps(txt_val) for t_val, txt_val, f_val in norm_items)
                if buffer.get_char_count() > 0:
                    end_char = buffer.get_text(buffer.get_iter_at_offset(buffer.get_char_count() - 1), end_iter, False)
                    sep = "\n\n" if end_char != "\n" else "\n"
                    buffer.insert(end_iter, sep + combined_text)
                else:
                    buffer.set_text(combined_text)
                end = buffer.get_end_iter()
                buffer.place_cursor(end)
                buffer.end_user_action()
                self._update_drop_placeholder_visibility()
                tv.grab_focus()
        elif response == "new_tabs":
            for title, t, f in norm_items:
                self.create_new_tab(title=title, text=t, file=f)
        elif response == "all_in_one":
            combined_text = "\n\n".join(txt_val for t_val, txt_val, f_val in norm_items)
            distinct_files = list(set(f_val.get_basename() for t_val, txt_val, f_val in norm_items if f_val and hasattr(f_val, 'get_basename')))
            if len(distinct_files) == 1 and len(norm_items) > 1:
                title = f"{distinct_files[0]} (All Chapters)"
            elif len(norm_items) == 1:
                title = norm_items[0][0]
            else:
                title = f"{norm_items[0][0]} + {len(norm_items) - 1} more"
            first_file = norm_items[0][2] if norm_items else None
            self.create_new_tab(title=title, text=combined_text, file=first_file)

    def _on_close_current_tab_action(self, *args):
        """Closes the currently active tab."""
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page'):
            page = self.tab_view.get_selected_page()
            if page:
                self.tab_view.close_page(page)

    def _get_text_for_page(self, page):
        """Extracts all text from a given TabPage."""
        if not page:
            return ""
        sw = page.get_child()
        if not sw or not hasattr(sw, 'get_child'):
            return ""
        tv = sw.get_child()
        if not tv or not hasattr(tv, 'get_buffer'):
            return ""
        buf = tv.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def _on_close_page(self, tab_view, page):
        """Intercepts tab close and prompts user to export text or audio if tab contains content."""
        def finish_close():
            reader = getattr(page, '_reader', None)
            if reader:
                if hasattr(reader, 'stop_audio'):
                    try:
                        reader.stop_audio()
                    except Exception:
                        pass
                if getattr(reader, 'temp_path', None) and os.path.exists(reader.temp_path):
                    try:
                        os.unlink(reader.temp_path)
                    except Exception:
                        pass
            if getattr(self, 'reader', None) is reader:
                self.reader = None
            if getattr(self, '_active_tab_page', None) is page:
                self._active_tab_page = None
            page._reader = None
            page._is_playing = False
            page._is_paused = False
            tab_view.close_page_finish(page, True)
            self._ensure_at_least_one_tab()

        text = self._get_text_for_page(page)

        # If tab is empty, close immediately without prompting
        if not text.strip():
            finish_close()
            return True

        # Stop playback if currently playing on this tab
        if self.is_playing and tab_view.get_selected_page() == page:
            self.stop_playback()

        # Prompt user with AlertDialog
        dialog = Adw.AlertDialog(
            heading=_("Export Tab Before Closing?"),
            body=_("Do you wish to export the text file or the audio file before closing \"{title}\"?").format(title=page.get_title())
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("discard", _("Close Without Exporting"))
        dialog.add_response("export_text", _("Export Text"))
        dialog.add_response("export_audio", _("Export Audio"))

        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("export_audio", Adw.ResponseAppearance.SUGGESTED)

        def on_choose(dlg, result):
            try:
                response = dlg.choose_finish(result)
            except Exception:
                tab_view.close_page_finish(page, False)
                return

            if response == "export_text":
                self._export_text_for_page(
                    page,
                    on_complete=finish_close
                )
            elif response == "export_audio":
                self._export_audio_for_page(
                    page,
                    on_complete=finish_close
                )
            elif response == "discard":
                finish_close()
            else: # "cancel"
                tab_view.close_page_finish(page, False)

        dialog.choose(self, None, on_choose)
        return True

    def _export_text_for_page(self, page, on_complete=None):
        """Prompts user to save the text of a specific page to a file."""
        text = self._get_text_for_page(page)
        if not text.strip():
            if on_complete:
                on_complete()
            return

        native = Gtk.FileDialog()
        initial_name = f"{page.get_title()}.txt" if page.get_title() and not page.get_title().endswith(".txt") else "text.txt"
        initial_name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', '', initial_name)
        if not initial_name.endswith(".txt"):
            initial_name += ".txt"
        native.set_initial_name(initial_name)

        def on_save_response(dialog, result):
            try:
                file = dialog.save_finish(result)
            except Exception:
                file = None

            if file is not None:
                bytes_data = GLib.Bytes.new(text.encode('utf-8'))
                def on_done(f, res):
                    try:
                        f.replace_contents_finish(res)
                    except Exception as e:
                        print(f"Error saving text: {e}")
                    if on_complete:
                        GLib.idle_add(on_complete)

                file.replace_contents_bytes_async(
                    bytes_data,
                    None,
                    False,
                    Gio.FileCreateFlags.NONE,
                    None,
                    on_done
                )

        native.save(self, None, on_save_response)

    def _export_audio_for_page(self, page, on_complete=None):
        """Prompts user to save the synthesized audio of a specific page to a file."""
        text_to_save = self._get_text_for_page(page)
        if not text_to_save.strip():
            self._show_error(_("No text to save!"))
            return

        native = Gtk.FileDialog()
        native.set_title(_("Save Audio File"))
        initial_name = self._generate_default_audio_filename(text_to_save)
        native.set_initial_name(initial_name)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        mp3_filter = Gtk.FileFilter()
        mp3_filter.set_name(_("MP3 Audio — 64 kbps Mono, Voice/Podcast Optimized (*.mp3)"))
        mp3_filter.add_pattern("*.mp3")
        mp3_filter.add_mime_type("audio/mpeg")
        filters.append(mp3_filter)

        wav_filter = Gtk.FileFilter()
        wav_filter.set_name(_("WAV Audio — Lossless Uncompressed PCM (*.wav)"))
        wav_filter.add_pattern("*.wav")
        wav_filter.add_mime_type("audio/wav")
        filters.append(wav_filter)

        native.set_filters(filters)
        native.set_default_filter(mp3_filter)

        def on_response(dialog, result):
            try:
                file = dialog.save_finish(result)
            except Exception:
                return

            if file is None:
                return

            engine = 'piper'
            selected_voice = self._get_selected_voice_name()
            pitch = self._get_pitch_for_voice(selected_voice)
            speed = self.speed_chooser.get_value()
            lang_code = self.lang_code

            target_reader = getattr(page, '_reader', None) or (getattr(self, 'reader', None))
            has_matching_audio = (
                target_reader is not None
                and getattr(target_reader, 'temp_path', None)
                and os.path.exists(target_reader.temp_path)
                and getattr(target_reader, 'original_text', None) == text_to_save
                and getattr(target_reader, 'selected_voice', None) == selected_voice
                and abs(getattr(target_reader, 'pitch', 0) - pitch) < 1e-4
                and abs(getattr(target_reader, 'speed', 0) - speed) < 1e-4
                and getattr(target_reader, 'lang_code', None) == lang_code
            )

            if has_matching_audio:
                try:
                    target_reader.save_audio_file(file)
                    page._exported_audio_text = text_to_save
                    if on_complete:
                        GLib.idle_add(on_complete)
                except Exception as e:
                    self._show_error(f"{_('Error saving audio file')}: {e}")
                return

            def on_synthesized(temp_path):
                try:
                    self.reader.save_audio_file(file)
                    page._exported_audio_text = text_to_save
                    if on_complete:
                        GLib.idle_add(on_complete)
                except Exception as e:
                    self._show_error(f"{_('Error saving audio file')}: {e}")

            self.reader = Reader(
                text_to_save,
                engine,
                lang_code,
                selected_voice,
                pitch,
                speed,
                window=self,
                play_audio=False,
                on_complete=on_synthesized
            )
            page._reader = self.reader

        native.save(self, None, on_response)

    # Dialog for saving an audio file is defined
    def save_audio_dialog(self, *args):
        """Prompts whether to export All Tabs or Current Tab if multiple tabs exist, otherwise exports current tab."""
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_n_pages') and self.tab_view.get_n_pages() > 1:
            dialog = Adw.AlertDialog(
                heading=_("Export Audio"),
                body=_("Do you wish to export all tabs or just the current tab you are viewing?")
            )
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("current", _("Current Tab"))
            dialog.add_response("all", _("All Tabs"))

            dialog.set_response_appearance("current", Adw.ResponseAppearance.DEFAULT)
            dialog.set_response_appearance("all", Adw.ResponseAppearance.SUGGESTED)

            def on_choose(dlg, result):
                try:
                    choice = dlg.choose_finish(result)
                except Exception:
                    return

                if choice == "current":
                    self._save_single_audio_dialog()
                elif choice == "all":
                    self._export_all_tabs_audio_dialog()

            dialog.choose(self, None, on_choose)
        else:
            self._save_single_audio_dialog()

    def _save_single_audio_dialog(self, *args):
        """Dialog for saving audio file of the current tab."""
        text_to_save = self._get_text_for_saving()
        if not text_to_save.strip():
            self._show_error(_("No text to save!"))
            return

        native = Gtk.FileDialog()
        native.set_title(_("Save Audio File"))
        initial_name = self._generate_default_audio_filename(text_to_save)
        native.set_initial_name(initial_name)

        # Configure file filters for MP3 and WAV with quality explanations
        filters = Gio.ListStore.new(Gtk.FileFilter)

        mp3_filter = Gtk.FileFilter()
        mp3_filter.set_name(_("MP3 Audio — 64 kbps Mono, Voice/Podcast Optimized (*.mp3)"))
        mp3_filter.add_pattern("*.mp3")
        mp3_filter.add_mime_type("audio/mpeg")
        filters.append(mp3_filter)

        wav_filter = Gtk.FileFilter()
        wav_filter.set_name(_("WAV Audio — Lossless Uncompressed PCM (*.wav)"))
        wav_filter.add_pattern("*.wav")
        wav_filter.add_mime_type("audio/wav")
        filters.append(wav_filter)

        native.set_filters(filters)
        native.set_default_filter(mp3_filter)

        native.save(self, None, self.on_save_audio_response)

    def _export_all_tabs_audio_dialog(self, pages_to_export=None, on_complete=None):
        """Allows user to select a folder, then sequentially synthesizes and exports audio for all tabs."""
        if pages_to_export is None:
            pages_to_export = []
            for i in range(self.tab_view.get_n_pages()):
                page = self.tab_view.get_nth_page(i)
                text = self._get_text_for_page(page)
                if text.strip():
                    pages_to_export.append((page, text))

        if not pages_to_export:
            self._show_error(_("No text in any open tab to export!"))
            return

        folder_dialog = Gtk.FileDialog()
        folder_dialog.set_title(_("Select Destination Folder for All Tabs"))

        def on_folder_selected(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
            except Exception:
                folder = None

            if folder is None:
                return

            folder_path = folder.get_path()
            if not folder_path or not os.path.isdir(folder_path):
                self._show_error(_("Invalid destination directory."))
                return

            self._batch_export_tabs_audio(pages_to_export, folder_path, on_complete=on_complete)

        folder_dialog.select_folder(self, None, on_folder_selected)

    def _batch_export_tabs_audio(self, pages_to_export, folder_path, on_complete=None):
        """Sequentially synthesizes and saves audio for multiple tabs into folder_path."""
        self._batch_export_cancelled = False
        total = len(pages_to_export)
        engine = 'piper'
        selected_voice = self._get_selected_voice_name()
        pitch = self._get_pitch_for_voice(selected_voice)
        speed = self.speed_chooser.get_value()
        lang_code = self.lang_code

        if self.is_playing:
            self.stop_playback()

        def export_next(index):
            if getattr(self, '_batch_export_cancelled', False):
                self._batch_export_status = None
                self.hide_wait_dialog()
                self.set_sensitive(True)
                return

            if index >= total:
                self._batch_export_status = None
                self.hide_wait_dialog()
                self.set_sensitive(True)
                if on_complete:
                    GLib.idle_add(on_complete)
                return

            status_msg = _("Generating file {current} of {total}").format(
                current=index + 1,
                total=total
            )
            self._batch_export_status = status_msg

            page, text = pages_to_export[index]
            filename = self._generate_default_audio_filename(text)
            dest_file_path = os.path.join(folder_path, filename)
            base, ext = os.path.splitext(dest_file_path)
            c = 1
            while os.path.exists(dest_file_path):
                dest_file_path = f"{base}_{c}{ext}"
                c += 1

            dest_gio_file = Gio.File.new_for_path(dest_file_path)

            self.show_wait_dialog(batch_text=status_msg)
            if hasattr(self, 'progress_label') and self.progress_label:
                self.progress_label.set_text(status_msg)

            def on_synthesized(temp_path):
                if getattr(self, '_batch_export_cancelled', False):
                    return
                try:
                    if hasattr(self, 'progress_label') and self.progress_label:
                        self.progress_label.set_text(_("Saving audio..."))
                    self.reader.save_audio_file(dest_gio_file)
                    page._exported_audio_text = text
                except Exception as e:
                    print(f"Error saving batch audio for tab {index+1}: {e}")
                if not getattr(self, '_batch_export_cancelled', False):
                    GLib.idle_add(export_next, index + 1)

            self.reader = Reader(
                text,
                engine,
                lang_code,
                selected_voice,
                pitch,
                speed,
                window=self,
                play_audio=False,
                on_complete=on_synthesized,
                hide_dialog_on_complete=False
            )
            page._reader = self.reader

        export_next(0)

    ## ================================================================##
    # Preset Demos
    def on_load_demo_action(self, action, param):
        """Action handler when user selects a preset demo from the menu."""
        demo_key = param.get_string() if param else ""
        demo_data = DEMOS.get(demo_key)
        if not demo_data:
            return

        buffer = self.main_text_view.get_buffer()
        start, end = buffer.get_bounds()
        current_text = buffer.get_text(start, end, False).strip()

        if current_text:
            self._show_overwrite_warning(demo_data)
        else:
            self._apply_and_play_demo(demo_data)

    def _show_overwrite_warning(self, demo_data):
        """Warns the user if the input field is not empty before overwriting with the demo."""
        dialog = Adw.AlertDialog(
            heading=_("Overwrite Current Text?"),
            body=_("Loading this preset demo will replace your current text and adjust voice settings. Do you wish to continue?"),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("overwrite", _("Overwrite"))
        dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dlg, result):
            try:
                response = dlg.choose_finish(result)
            except Exception:
                return
            if response == "overwrite":
                self._apply_and_play_demo(demo_data)

        dialog.choose(self, None, on_response)

    def _apply_and_play_demo(self, demo_data):
        """Loads demo text, selects language and voice, sets pitch and speed, and starts playback."""
        # 1. Stop any currently active playback
        if self.is_playing:
            self.stop_playback()

        # 2. Clear active word highlights
        self._clear_highlight()

        # 3. Set demo text into buffer and move cursor to start
        buffer = self.main_text_view.get_buffer()
        buffer.set_text(ensure_paragraph_gaps(demo_data["text"]))
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page'):
            page = self.tab_view.get_selected_page()
            if page:
                page.set_title(demo_data.get("title", _("Demo")))
                page.set_tooltip(demo_data.get("title", _("Demo")))

        # 4. Set language in dropdown (triggers synchronous update of current_voices & voice_chooser)
        target_lang = demo_data["language"]
        lang_model = self.lang_chooser.get_model()
        if lang_model:
            for i in range(lang_model.get_n_items()):
                if lang_model.get_string(i) == target_lang:
                    if self.lang_chooser.get_selected() != i:
                        self.lang_chooser.set_selected(i)
                    else:
                        self._update_voice_chooser(target_lang)
                    break

        # 5. Set voice in voice_chooser matching exact voice_id or raw voice name
        target_voice_id = demo_data["voice_id"]
        target_raw = demo_data.get("raw_voice_name", "").lower()
        if hasattr(self, "current_voices") and self.current_voices:
            matched_idx = None
            for i, v in enumerate(self.current_voices):
                if v.get("id") == target_voice_id:
                    matched_idx = i
                    break
            if matched_idx is None:
                for i, v in enumerate(self.current_voices):
                    if v.get("raw_voice_name", "").lower() == target_raw:
                        matched_idx = i
                        break
            if matched_idx is not None:
                self.voice_chooser.set_selected(matched_idx)

        # 6. Apply pitch and speed settings
        if hasattr(self, 'adjustment_1') and self.adjustment_1:
            self.adjustment_1.set_value(demo_data["pitch"])
        if hasattr(self, 'adjustment_2') and self.adjustment_2:
            self.adjustment_2.set_value(demo_data["speed"])
        if hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'set_value'):
            self.speed_chooser.set_value(demo_data["speed"])

        # 7. Automatically start playback
        self.read_text(self.read_button)

    ## ================================================================##
    # Text Cleanup Tools
    def on_remove_round_brackets_action(self, *args):
        """Action handler to remove () round brackets and their contents."""
        self._prompt_and_apply_bracket_tool("round")

    def on_remove_square_brackets_action(self, *args):
        """Action handler to remove [] square brackets and their contents."""
        self._prompt_and_apply_bracket_tool("square")

    def on_remove_pipe_brackets_action(self, *args):
        """Action handler to remove | pipe brackets and their contents."""
        self._prompt_and_apply_bracket_tool("pipe")

    def on_remove_hashes_action(self, *args):
        """Action handler to remove # hash symbols from text."""
        self._prompt_and_apply_bracket_tool("hash")

    def on_remove_stars_action(self, *args):
        """Action handler to remove * star (asterisk) symbols from text."""
        self._prompt_and_apply_bracket_tool("star")

    def on_remove_all_tags_action(self, *args):
        """Action handler to remove all tags (brackets, pipes, hashes, stars) from text."""
        self._prompt_and_apply_bracket_tool("all")

    def unwrap_text(self):
        """Unwraps/reflows text in the active tab (selected text or entire buffer)."""
        tv = self.main_text_view
        if not tv:
            return
        buffer = tv.get_buffer()
        if not buffer:
            return

        bounds = buffer.get_selection_bounds()
        buffer.begin_user_action()
        try:
            if bounds:
                start_iter, end_iter = bounds
                selected_text = buffer.get_text(start_iter, end_iter, True)
                if selected_text:
                    reflowed = unwrap_text(selected_text)
                    buffer.delete(start_iter, end_iter)
                    buffer.insert(start_iter, reflowed)
            else:
                start_all = buffer.get_start_iter()
                end_all = buffer.get_end_iter()
                full_text = buffer.get_text(start_all, end_all, True)
                if full_text:
                    reflowed = unwrap_text(full_text)
                    buffer.delete(start_all, end_all)
                    buffer.insert(start_all, reflowed)
        finally:
            buffer.end_user_action()

    def on_unwrap_text_action(self, *args):
        """Action handler to unwrap / reflow text."""
        self.unwrap_text()

    def _get_wikipedia_logo_paintable(self):
        """Loads the Wikipedia globe logo paintable from gresource or local icons path."""
        try:
            return Gdk.Texture.new_from_resource("/im/zackarious/ReadAloud/images/wikipedia-logo.png")
        except Exception:
            pass
        local_path = os.path.join(os.path.dirname(__file__), "icons", "wikipedia-logo.png")
        if os.path.exists(local_path):
            try:
                return Gdk.Texture.new_from_filename(local_path)
            except Exception:
                pass
        return None

    def on_import_wikipedia_action(self, *args):
        """Action handler to prompt for Wikipedia article topic or URL and import as tabs."""
        self.set_auto_remove_tags(True)
        dialog = Adw.AlertDialog(
            heading=_("Import from Wikipedia"),
            body=_("Enter a Wikipedia article topic or full URL. Each article will be imported into a tab with all tags stripped for speech synthesis:")
        )
        dialog.set_content_width(920)
        dialog.set_prefer_wide_layout(True)
        if hasattr(self, 'get_width') and self.get_width() < 960:
            try:
                self.set_default_size(max(self.get_width(), 960), max(self.get_height(), 680))
            except Exception:
                pass

        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        main_hbox.set_margin_top(4)
        main_hbox.set_margin_bottom(4)
        main_hbox.set_margin_start(16)
        main_hbox.set_margin_end(16)

        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left_col.set_size_request(390, -1)
        left_col.set_hexpand(False)

        # Wikipedia Globe Logo
        logo_texture = self._get_wikipedia_logo_paintable()
        if logo_texture:
            logo_picture = Gtk.Picture.new_for_paintable(logo_texture)
            logo_picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            logo_picture.set_can_shrink(True)
            logo_picture.set_size_request(72, 72)
            logo_picture.set_halign(Gtk.Align.CENTER)
            logo_picture.set_margin_bottom(2)
            left_col.append(logo_picture)

        # Expand / Condense Trending Topics Toggle Button (Open by default)
        toggle_trending_btn = Gtk.Button(label=_("Hide Trending Topics  ◀"))
        toggle_trending_btn.add_css_class("pill")
        toggle_trending_btn.add_css_class("trending-toggle-btn")
        toggle_trending_btn.set_tooltip_text(_("Explore the top 25 trending articles on Wikipedia with preview images"))
        toggle_trending_btn.set_halign(Gtk.Align.CENTER)
        left_col.append(toggle_trending_btn)

        # Search Entry with Autocomplete Dropdown
        search_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        search_vbox.set_hexpand(True)

        entry = Gtk.Entry()
        entry.set_placeholder_text(_("Search Wikipedia or enter article URL…"))
        entry.set_hexpand(True)
        search_vbox.append(entry)

        sugg_revealer = Gtk.Revealer()
        sugg_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        sugg_revealer.set_reveal_child(False)

        sugg_frame = Gtk.Frame()
        sugg_frame.set_margin_top(4)
        sugg_frame.add_css_class("card")

        sugg_scrolled = Gtk.ScrolledWindow()
        sugg_scrolled.set_propagate_natural_height(True)
        sugg_scrolled.set_min_content_height(140)
        sugg_scrolled.set_max_content_height(170)
        sugg_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        sugg_listbox = Gtk.ListBox()
        sugg_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        sugg_listbox.add_css_class("rich-list")

        sugg_scrolled.set_child(sugg_listbox)
        sugg_frame.set_child(sugg_scrolled)
        sugg_revealer.set_child(sugg_frame)
        search_vbox.append(sugg_revealer)

        left_col.append(search_vbox)

        # Debounced suggestions fetching
        search_timer_id = [None]

        def cancel_search_timer():
            if search_timer_id[0] is not None:
                try:
                    GLib.source_remove(search_timer_id[0])
                except Exception:
                    pass
                search_timer_id[0] = None

        def clear_suggestions():
            child = sugg_listbox.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                sugg_listbox.remove(child)
                child = nxt

        def apply_suggestions(query, suggestions):
            if entry.get_text().strip() != query.strip():
                return
            clear_suggestions()
            if not suggestions:
                sugg_revealer.set_reveal_child(False)
                return

            for sugg in suggestions:
                row = Gtk.ListBoxRow()
                row._wiki_title = sugg.title
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row_box.set_margin_start(8)
                row_box.set_margin_end(8)
                row_box.set_margin_top(4)
                row_box.set_margin_bottom(4)

                thumb_box = Gtk.Box()
                thumb_box.set_size_request(40, 32)
                thumb_box.set_valign(Gtk.Align.CENTER)
                thumb_box.set_halign(Gtk.Align.CENTER)

                icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
                icon.set_pixel_size(24)
                thumb_box.append(icon)
                row_box.append(thumb_box)

                if sugg.thumbnail_url:
                    def load_thumb(t_url, container, fallback_icon):
                        def thumb_worker():
                            t_bytes = fetch_thumbnail_bytes(t_url)
                            if t_bytes:
                                def apply_texture():
                                    try:
                                        glib_b = GLib.Bytes.new(t_bytes)
                                        tex = Gdk.Texture.new_from_bytes(glib_b)
                                        pic = Gtk.Picture.new_for_paintable(tex)
                                        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                                        pic.set_can_shrink(True)
                                        pic.set_size_request(40, 32)
                                        container.remove(fallback_icon)
                                        container.append(pic)
                                    except Exception:
                                        pass
                                GLib.idle_add(apply_texture)
                        threading.Thread(target=thumb_worker, daemon=True).start()
                    load_thumb(sugg.thumbnail_url, thumb_box, icon)

                text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                text_col.set_hexpand(True)
                title_lbl = Gtk.Label(label=sugg.title)
                title_lbl.set_halign(Gtk.Align.START)
                title_lbl.add_css_class("heading")
                text_col.append(title_lbl)

                if sugg.description:
                    desc_lbl = Gtk.Label(label=sugg.description)
                    desc_lbl.set_halign(Gtk.Align.START)
                    desc_lbl.add_css_class("dim-label")
                    desc_lbl.add_css_class("caption")
                    desc_lbl.set_ellipsize(3)
                    text_col.append(desc_lbl)

                row_box.append(text_col)
                row.set_child(row_box)
                sugg_listbox.append(row)

            sugg_revealer.set_reveal_child(True)
            GLib.idle_add(lambda: sugg_scrolled.get_vadjustment().set_value(0))

        def trigger_suggestions_fetch(query):
            lang = getattr(self, 'lang_code', 'en') or 'en'
            def worker():
                try:
                    suggs = fetch_wikipedia_suggestions(query, lang_code=lang, limit=5)
                except Exception:
                    suggs = []
                GLib.idle_add(apply_suggestions, query, suggs)
            threading.Thread(target=worker, daemon=True).start()

        def on_entry_changed(ent):
            q = ent.get_text().strip()
            cancel_search_timer()
            if not q or len(q) < 2 or q.startswith("http://") or q.startswith("https://"):
                sugg_revealer.set_reveal_child(False)
                clear_suggestions()
                return

            def on_timer():
                search_timer_id[0] = None
                trigger_suggestions_fetch(q)
                return False

            search_timer_id[0] = GLib.timeout_add(250, on_timer)

        entry.connect("changed", on_entry_changed)

        def on_row_activated(lbox, row):
            if hasattr(row, '_wiki_title') and row._wiki_title:
                cancel_search_timer()
                entry.set_text(row._wiki_title)
                sugg_revealer.set_reveal_child(False)
                entry.grab_focus()

        sugg_listbox.connect("row-activated", on_row_activated)

        key_ctrl = Gtk.EventControllerKey()
        def on_key_pressed(controller, keyval, keycode, state):
            if keyval == Gdk.KEY_Down:
                if sugg_revealer.get_reveal_child():
                    first_row = sugg_listbox.get_row_at_index(0)
                    if first_row:
                        sugg_listbox.select_row(first_row)
                        first_row.grab_focus()
                        return True
            elif keyval == Gdk.KEY_Escape:
                if sugg_revealer.get_reveal_child():
                    sugg_revealer.set_reveal_child(False)
                    return True
            return False
        key_ctrl.connect("key-pressed", on_key_pressed)
        entry.add_controller(key_ctrl)

        list_key_ctrl = Gtk.EventControllerKey()
        def on_list_key_pressed(controller, keyval, keycode, state):
            if keyval == Gdk.KEY_Escape:
                sugg_revealer.set_reveal_child(False)
                entry.grab_focus()
                return True
            return False
        list_key_ctrl.connect("key-pressed", on_list_key_pressed)
        sugg_listbox.add_controller(list_key_ctrl)

        chk_related = Gtk.CheckButton(label=_("Import related internal articles as separate tabs"))
        chk_related.set_active(False)
        left_col.append(chk_related)

        limit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        limit_box.set_margin_start(24)
        limit_label = Gtk.Label(label=_("Max related articles:"))
        limit_spin = Gtk.SpinButton.new_with_range(1, 10, 1)
        limit_spin.set_value(3)
        limit_box.append(limit_label)
        limit_box.append(limit_spin)
        limit_box.set_sensitive(False)
        left_col.append(limit_box)

        def on_related_toggled(chk):
            limit_box.set_sensitive(chk.get_active())
        chk_related.connect("toggled", on_related_toggled)

        # Donation Callout Card
        donate_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        donate_card.add_css_class("card")
        donate_card.set_margin_top(10)
        donate_card.set_margin_bottom(2)
        donate_card.set_margin_start(2)
        donate_card.set_margin_end(2)

        donate_label = Gtk.Label()
        donate_label.set_use_markup(True)
        donate_label.set_wrap(True)
        donate_label.set_max_width_chars(38)
        donate_label.set_justify(Gtk.Justification.CENTER)
        donate_label.set_markup(
            _("<span size=\"small\">Wikipedia is a non-profit resource maintained by the Wikimedia Foundation.\n"
              "Please consider supporting this great cause to keep knowledge free:</span>")
        )
        donate_card.append(donate_label)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://donate.wikimedia.org/",
            _("💖 Donate to the Wikimedia Foundation")
        )
        link_btn.set_halign(Gtk.Align.CENTER)
        donate_card.append(link_btn)

        left_col.append(donate_card)
        main_hbox.append(left_col)

        # Right Pane: Top 25 Trending Topics (Expandable / Condensable)
        trending_revealer = Gtk.Revealer()
        trending_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        trending_revealer.set_reveal_child(True)

        right_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        v_sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        right_container.append(v_sep)

        trending_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        trending_vbox.set_size_request(450, -1)
        right_container.append(trending_vbox)
        trending_revealer.set_child(right_container)
        main_hbox.append(trending_revealer)

        # Trending Header (Title, Subtitle, Refresh, Collapse)
        trending_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        trending_title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        trending_title_box.set_hexpand(True)

        trending_title_lbl = Gtk.Label(label=_("Trending on Wikipedia (Top 25)"))
        trending_title_lbl.add_css_class("heading")
        trending_title_lbl.set_halign(Gtk.Align.START)

        trending_sub_lbl = Gtk.Label(label=_("Most Popular Articles of the Week"))
        trending_sub_lbl.add_css_class("caption")
        trending_sub_lbl.add_css_class("dim-label")
        trending_sub_lbl.set_halign(Gtk.Align.START)
        trending_sub_lbl.set_ellipsize(3)

        trending_title_box.append(trending_title_lbl)
        trending_title_box.append(trending_sub_lbl)
        trending_header.append(trending_title_box)

        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.add_css_class("flat")
        refresh_btn.add_css_class("circular")
        refresh_btn.set_tooltip_text(_("Refresh Trending Topics"))
        trending_header.append(refresh_btn)

        collapse_btn = Gtk.Button.new_from_icon_name("pan-end-symbolic")
        collapse_btn.add_css_class("flat")
        collapse_btn.add_css_class("circular")
        collapse_btn.set_tooltip_text(_("Condense Right Pane"))
        trending_header.append(collapse_btn)

        trending_vbox.append(trending_header)

        # Content Stack: Loading, Error, List
        trending_stack = Gtk.Stack()
        trending_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # View 1: Loading View
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.set_size_request(-1, 380)
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        loading_lbl = Gtk.Label(label=_("Scraping Top 25 Trending Topics from Wikipedia…"))
        loading_lbl.add_css_class("dim-label")
        loading_box.append(spinner)
        loading_box.append(loading_lbl)
        trending_stack.add_named(loading_box, "loading")

        # View 2: Error View
        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        error_box.set_valign(Gtk.Align.CENTER)
        error_box.set_size_request(-1, 380)
        error_lbl = Gtk.Label(label=_("Could not load Top 25 Report."))
        error_lbl.add_css_class("dim-label")
        retry_btn = Gtk.Button(label=_("Retry"))
        retry_btn.add_css_class("pill")
        retry_btn.set_halign(Gtk.Align.CENTER)
        error_box.append(error_lbl)
        error_box.append(retry_btn)
        trending_stack.add_named(error_box, "error")

        # View 3: List View
        trending_scrolled = Gtk.ScrolledWindow()
        trending_scrolled.set_propagate_natural_height(True)
        trending_scrolled.set_min_content_height(380)
        trending_scrolled.set_max_content_height(460)
        trending_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        trending_listbox = Gtk.ListBox()
        trending_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        trending_listbox.add_css_class("rich-list")
        trending_listbox.add_css_class("trending-pane-card")
        trending_scrolled.set_child(trending_listbox)
        trending_stack.add_named(trending_scrolled, "list")

        trending_vbox.append(trending_stack)

        def clear_trending_list():
            child = trending_listbox.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                trending_listbox.remove(child)
                child = nxt

        def populate_trending(report_title, items):
            if report_title:
                trending_sub_lbl.set_text(report_title)
            clear_trending_list()
            if not items:
                error_lbl.set_text(_("No trending topics found in Top 25 Report."))
                trending_stack.set_visible_child_name("error")
                return

            for topic in items:
                row = Gtk.ListBoxRow()
                row._wiki_topic = topic
                row._wiki_title = topic.title

                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row_box.add_css_class("trending-row")

                # Rank Badge
                rank_lbl = Gtk.Label(label=f"#{topic.rank}")
                rank_lbl.add_css_class("trending-rank-badge")
                rank_lbl.set_valign(Gtk.Align.CENTER)
                row_box.append(rank_lbl)

                # Thumbnail Image Container
                thumb_box = Gtk.Box()
                thumb_box.set_size_request(60, 48)
                thumb_box.set_valign(Gtk.Align.CENTER)
                thumb_box.set_halign(Gtk.Align.CENTER)
                thumb_box.add_css_class("trending-thumb")

                fallback_icon = Gtk.Image.new_from_icon_name("text-x-generic-symbolic")
                fallback_icon.set_pixel_size(24)
                fallback_icon.set_valign(Gtk.Align.CENTER)
                fallback_icon.set_halign(Gtk.Align.CENTER)
                thumb_box.append(fallback_icon)
                row_box.append(thumb_box)

                if topic.image_url:
                    def load_trending_thumb(t_url, container, fallback):
                        def thumb_worker():
                            t_bytes = fetch_thumbnail_bytes(t_url)
                            if t_bytes:
                                def apply_thumb():
                                    try:
                                        glib_b = GLib.Bytes.new(t_bytes)
                                        tex = Gdk.Texture.new_from_bytes(glib_b)
                                        pic = Gtk.Picture.new_for_paintable(tex)
                                        pic.set_content_fit(Gtk.ContentFit.COVER)
                                        pic.set_can_shrink(True)
                                        pic.set_size_request(60, 48)
                                        container.remove(fallback)
                                        container.append(pic)
                                    except Exception:
                                        pass
                                GLib.idle_add(apply_thumb)
                        threading.Thread(target=thumb_worker, daemon=True).start()
                    load_trending_thumb(topic.image_url, thumb_box, fallback_icon)

                # Text Column: Title, Views, Notes
                text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                text_col.set_hexpand(True)
                text_col.set_valign(Gtk.Align.CENTER)

                t_title_lbl = Gtk.Label(label=topic.title)
                t_title_lbl.set_halign(Gtk.Align.START)
                t_title_lbl.add_css_class("heading")
                t_title_lbl.set_ellipsize(3)
                text_col.append(t_title_lbl)

                views_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
                views_box.set_halign(Gtk.Align.START)
                views_box.set_valign(Gtk.Align.CENTER)
                views_box.add_css_class("dim-label")

                eye_icon = Gtk.Image.new_from_icon_name("im.zackarious.ReadAloud.eye-symbolic")
                eye_icon.set_pixel_size(14)
                eye_icon.set_valign(Gtk.Align.CENTER)
                views_box.append(eye_icon)

                views_lbl = Gtk.Label(label=f"{topic.views} views")
                views_lbl.set_halign(Gtk.Align.START)
                views_lbl.add_css_class("caption")
                views_box.append(views_lbl)

                text_col.append(views_box)

                if topic.notes:
                    notes_lbl = Gtk.Label(label=topic.notes)
                    notes_lbl.set_halign(Gtk.Align.START)
                    notes_lbl.add_css_class("caption")
                    notes_lbl.set_max_width_chars(32)
                    notes_lbl.set_wrap(True)
                    notes_lbl.set_lines(2)
                    notes_lbl.set_ellipsize(3)
                    text_col.append(notes_lbl)

                row_box.append(text_col)

                # Quick Direct Import Button (📥 inbox tray icon)
                quick_import_btn = Gtk.Button()
                import_icon = Gtk.Image.new_from_icon_name("im.zackarious.ReadAloud.import-symbolic")
                import_icon.set_pixel_size(18)
                import_icon.set_valign(Gtk.Align.CENTER)
                import_icon.set_halign(Gtk.Align.CENTER)
                quick_import_btn.set_child(import_icon)
                quick_import_btn.add_css_class("flat")
                quick_import_btn.add_css_class("circular")
                quick_import_btn.add_css_class("trending-import-btn")
                quick_import_btn.set_valign(Gtk.Align.CENTER)
                quick_import_btn.set_tooltip_text(_("Import this trending article directly into a new tab (📥)"))

                def on_quick_import_clicked(btn, t_name=topic.title):
                    dialog.force_close()
                    fetch_rel = chk_related.get_active()
                    max_rel = int(limit_spin.get_value()) if fetch_rel else 0
                    self._start_wikipedia_import(t_name, fetch_rel, max_rel)

                quick_import_btn.connect("clicked", on_quick_import_clicked)
                row_box.append(quick_import_btn)

                row.set_child(row_box)
                trending_listbox.append(row)

            trending_stack.set_visible_child_name("list")
            GLib.idle_add(lambda: trending_scrolled.get_vadjustment().set_value(0))

        is_trending_loaded = [False]

        def load_trending(force=False):
            trending_stack.set_visible_child_name("loading")
            def worker():
                try:
                    rep_title, items = fetch_wikipedia_top_25(force_refresh=force)
                    is_trending_loaded[0] = True
                    GLib.idle_add(populate_trending, rep_title, items)
                except Exception as e:
                    def show_err():
                        error_lbl.set_text(str(e))
                        trending_stack.set_visible_child_name("error")
                    GLib.idle_add(show_err)
            threading.Thread(target=worker, daemon=True).start()

        def on_trending_row_activated(lbox, row):
            if hasattr(row, '_wiki_title') and row._wiki_title:
                entry.set_text(row._wiki_title)
                entry.grab_focus()

        trending_listbox.connect("row-activated", on_trending_row_activated)

        condensed_width = [450]

        def toggle_trending(expand=None):
            current = trending_revealer.get_reveal_child()
            target = not current if expand is None else expand
            if target:
                if not trending_revealer.get_reveal_child():
                    condensed_width[0] = 450
                dialog.set_content_width(920)
                dialog.set_prefer_wide_layout(True)
                trending_revealer.set_reveal_child(True)
                toggle_trending_btn.set_label(_("Hide Trending Topics  ◀"))
                if hasattr(self, 'get_width') and self.get_width() < 960:
                    try:
                        self.set_default_size(max(self.get_width(), 960), max(self.get_height(), 680))
                    except Exception:
                        pass
                if not is_trending_loaded[0]:
                    load_trending(force=False)
            else:
                trending_revealer.set_reveal_child(False)
                dialog.set_content_width(condensed_width[0])
                toggle_trending_btn.set_label(_("Trending Topics (Top 25)  ▶"))

        toggle_trending_btn.connect("clicked", lambda _: toggle_trending())
        collapse_btn.connect("clicked", lambda _: toggle_trending(False))
        refresh_btn.connect("clicked", lambda _: load_trending(force=True))
        retry_btn.connect("clicked", lambda _: load_trending(force=True))

        # Automatically start loading trending topics on dialog launch
        load_trending(force=False)

        dialog.set_extra_child(main_hbox)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("import", _("Import"))
        dialog.set_response_appearance("import", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("import")
        dialog.set_close_response("cancel")

        dialog._entry = entry
        dialog._sugg_revealer = sugg_revealer
        dialog._sugg_listbox = sugg_listbox
        dialog._apply_suggestions = apply_suggestions
        dialog._trending_revealer = trending_revealer
        dialog._toggle_trending_btn = toggle_trending_btn
        dialog._trending_listbox = trending_listbox
        dialog._trending_stack = trending_stack
        dialog._load_trending = load_trending
        dialog._toggle_trending = toggle_trending
        dialog._populate_trending = populate_trending

        # When enter is pressed in entry, trigger the import response
        def on_entry_activate(*_):
            topic_text = entry.get_text().strip()
            if not topic_text:
                return
            dialog.emit("response", "import")
            dialog.force_close()

        entry.connect("activate", on_entry_activate)

        def on_response(dlg, response):
            cancel_search_timer()
            if response == "import":
                topic_text = entry.get_text().strip()
                if not topic_text:
                    return
                fetch_related = chk_related.get_active()
                max_related = int(limit_spin.get_value()) if fetch_related else 0
                self._start_wikipedia_import(topic_text, fetch_related, max_related)

        dialog.connect("response", on_response)
        dialog.present(self)
        entry.grab_focus()
        return dialog

    def _start_wikipedia_import(self, topic_text, fetch_related, max_related):
        """Fetches Wikipedia article(s) in a background thread, strips all tags, and loads into tabs."""
        clean_topic = topic_text.split("/wiki/")[-1].split("#")[0].replace("_", " ") if "/wiki/" in topic_text else topic_text
        progress_dialog = Adw.AlertDialog(
            heading=_("Importing from Wikipedia"),
            body=_("Connecting to Wikipedia for '{topic}'…").format(topic=clean_topic)
        )
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        spinner_box.set_halign(Gtk.Align.CENTER)
        logo_texture = self._get_wikipedia_logo_paintable()
        if logo_texture:
            small_logo = Gtk.Picture.new_for_paintable(logo_texture)
            small_logo.set_content_fit(Gtk.ContentFit.CONTAIN)
            small_logo.set_can_shrink(True)
            small_logo.set_size_request(48, 48)
            small_logo.set_halign(Gtk.Align.CENTER)
            spinner_box.append(small_logo)
        spinner_box.append(spinner)
        progress_dialog.set_extra_child(spinner_box)

        progress_dialog.add_response("cancel", _("Cancel"))
        progress_dialog.set_close_response("cancel")

        is_cancelled = False
        programmatic_close = False

        def on_progress_response(dlg, resp):
            nonlocal is_cancelled
            if not programmatic_close:
                is_cancelled = True

        progress_dialog.connect("response", on_progress_response)
        progress_dialog.present(self)

        def worker():
            try:
                def progress_cb(status_msg, cur_idx, total_cnt):
                    if not is_cancelled:
                        GLib.idle_add(progress_dialog.set_body, status_msg)

                articles = fetch_wikipedia_articles(
                    topic_text,
                    fetch_related=fetch_related,
                    max_related=max_related,
                    progress_callback=progress_cb,
                    is_cancelled=lambda: is_cancelled
                )

                def on_finish_success():
                    nonlocal programmatic_close
                    if is_cancelled:
                        return
                    programmatic_close = True
                    try:
                        progress_dialog.force_close()
                    except Exception:
                        pass
                    if not articles:
                        self._show_error(_("No Wikipedia articles could be imported."))
                        return
                    self._populate_wikipedia_tabs(articles)

                GLib.idle_add(on_finish_success)

            except Exception as err:
                err_msg = str(err)

                def on_finish_error():
                    nonlocal programmatic_close
                    if is_cancelled:
                        return
                    programmatic_close = True
                    try:
                        progress_dialog.force_close()
                    except Exception:
                        pass
                    self._show_error(err_msg)

                GLib.idle_add(on_finish_error)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def _populate_wikipedia_tabs(self, articles):
        """Populates tabs with scraped Wikipedia articles, stripping all tags."""
        if not articles:
            return

        cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
        tv = self._get_text_view_for_page(cur_page) if cur_page else None
        buf = tv.get_buffer() if tv else None
        is_empty = False
        if buf:
            start, end = buf.get_bounds()
            is_empty = len(buf.get_text(start, end, True).strip()) == 0

        is_untitled = cur_page and (cur_page.get_title() == _("Untitled Document") or cur_page.get_title().startswith(_("Untitled")))

        if is_untitled and is_empty:
            first = articles[0]
            clean_first = clean_all_tags(first.text)
            buf.set_text(ensure_paragraph_gaps(clean_first))
            start = buf.get_start_iter()
            buf.place_cursor(start)
            cur_page.set_title(first.title)
            cur_page.set_tooltip(first.title)

            for art in articles[1:]:
                clean_text = clean_all_tags(art.text)
                self.create_new_tab(title=art.title, text=clean_text)
        else:
            for art in articles:
                clean_text = clean_all_tags(art.text)
                self.create_new_tab(title=art.title, text=clean_text)

        self._update_drop_placeholder_visibility()

    def _prompt_and_apply_bracket_tool(self, bracket_type):
        """Prompts the user whether to apply the text cleanup tool to the current tab or all tabs."""
        if not hasattr(self, 'tab_view') or not hasattr(self.tab_view, 'get_n_pages') or self.tab_view.get_n_pages() <= 1:
            self._apply_bracket_tool_to_current_tab(bracket_type)
            return

        if bracket_type == "round":
            heading = _("Remove ( ) Brackets")
        elif bracket_type == "square":
            heading = _("Remove [ ] Brackets")
        elif bracket_type == "pipe":
            heading = _("Remove | Pipes")
        elif bracket_type == "hash":
            heading = _("Remove # Hashes")
        elif bracket_type == "star":
            heading = _("Remove * Stars (Asterisks)")
        elif bracket_type == "all":
            heading = _("Remove All")
        else:
            heading = _("Text Cleanup")
        body = _("Do you wish to apply this tool to all tabs or just the current tab?")

        dialog = Adw.AlertDialog(
            heading=heading,
            body=body,
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("current", _("Current Tab"))
        dialog.add_response("all", _("All Tabs"))

        dialog.set_response_appearance("current", Adw.ResponseAppearance.DEFAULT)
        dialog.set_response_appearance("all", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("current")
        dialog.set_close_response("cancel")

        def on_response(dlg, result):
            try:
                choice = dlg.choose_finish(result)
            except Exception:
                return

            if choice == "current":
                self._apply_bracket_tool_to_current_tab(bracket_type)
            elif choice == "all":
                self._apply_bracket_tool_to_all_tabs(bracket_type)

        dialog.choose(self, None, on_response)

    def _apply_bracket_tool_to_view(self, text_view, bracket_type):
        """Applies the selected bracket or hash removal transformation to the given text view."""
        if not text_view:
            return
        buffer = text_view.get_buffer()
        if not buffer:
            return
        start, end = buffer.get_bounds()
        current_text = buffer.get_text(start, end, True)
        if not current_text:
            return

        if bracket_type == "round":
            new_text = clean_round_brackets(current_text)
        elif bracket_type == "square":
            new_text = clean_square_brackets(current_text)
        elif bracket_type == "pipe":
            new_text = clean_pipe_brackets(current_text)
        elif bracket_type == "hash":
            new_text = clean_hash_symbols(current_text)
        elif bracket_type == "star":
            new_text = clean_star_symbols(current_text)
        elif bracket_type == "all":
            new_text = clean_all_tags(current_text)
        else:
            return

        if new_text != current_text:
            if self.is_playing:
                self.stop_playback()
            buffer.begin_user_action()
            s, e = buffer.get_bounds()
            buffer.delete(s, e)
            buffer.insert(buffer.get_start_iter(), new_text)
            buffer.end_user_action()

    def _apply_bracket_tool_to_current_tab(self, bracket_type):
        """Applies the bracket removal tool to the currently active tab."""
        self._apply_bracket_tool_to_view(self.main_text_view, bracket_type)

    def _apply_bracket_tool_to_all_tabs(self, bracket_type):
        """Applies the bracket removal tool across all open tabs."""
        if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_n_pages'):
            for i in range(self.tab_view.get_n_pages()):
                page = self.tab_view.get_nth_page(i)
                sw = page.get_child()
                if sw and hasattr(sw, 'get_child'):
                    tv = sw.get_child()
                    self._apply_bracket_tool_to_view(tv, bracket_type)
        else:
            self._apply_bracket_tool_to_current_tab(bracket_type)

    # Defines what happens when a file is selected/not selected
    def on_open_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except Exception:
            return
        # If the user selected a file...
        if file is not None:
            # ... open it
            self.open_file(file)

    # Defines what happens when a text file is selected/not selected
    def on_save_text_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
        except Exception:
            return
        if file is not None:
            self.save_text(file)

    # Defines what happens when an audio file is selected/not selected
    def on_save_audio_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
        except Exception:
            return

        if file is None:
            return

        text_to_save = self._get_text_for_saving()
        if not text_to_save.strip():
            self._show_error(_("No text to save!"))
            return

        engine = 'piper'
        selected_voice = self._get_selected_voice_name()
        pitch = self._get_pitch_for_voice(selected_voice)
        speed = self.speed_chooser.get_value()
        lang_code = self.lang_code

        current_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
        target_reader = getattr(current_page, '_reader', None) or (getattr(self, 'reader', None))

        # Check if currently cached reader already matches current text & parameters
        has_matching_audio = (
            target_reader is not None
            and getattr(target_reader, 'temp_path', None)
            and os.path.exists(target_reader.temp_path)
            and getattr(target_reader, 'original_text', None) == text_to_save
            and getattr(target_reader, 'selected_voice', None) == selected_voice
            and abs(getattr(target_reader, 'pitch', 0) - pitch) < 1e-4
            and abs(getattr(target_reader, 'speed', 0) - speed) < 1e-4
            and getattr(target_reader, 'lang_code', None) == lang_code
        )

        if has_matching_audio:
            try:
                target_reader.save_audio_file(file)
                if current_page:
                    current_page._exported_audio_text = text_to_save
            except Exception as e:
                self._show_error(f"{_('Error saving audio file')}: {e}")
        else:
            if self.is_playing:
                self.stop_playback()

            def on_synthesized(temp_path):
                try:
                    self.reader.save_audio_file(file)
                    if current_page:
                        current_page._exported_audio_text = text_to_save
                except Exception as e:
                    self._show_error(f"{_('Error saving audio file')}: {e}")

            self.reader = Reader(
                text_to_save,
                engine,
                lang_code,
                selected_voice,
                pitch,
                speed,
                window=self,
                play_audio=False,
                on_complete=on_synthesized
            )
            if current_page:
                current_page._reader = self.reader

    # Speed selection management
    def _get_current_speed(self):
        """Returns the current speech speed float based on selected voice and speed mode."""
        voice_id = self._get_selected_voice_name() if hasattr(self, '_get_selected_voice_name') else ""
        selected_idx = self.speed_chooser.get_selected() if hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_selected') else 0
        options = getattr(self, 'SPEED_OPTIONS', SPEED_CHOICES)
        default_idx = options.index("Normal") if "Normal" in options else 0
        if selected_idx < 0 or selected_idx >= len(options):
            selected_idx = default_idx
        speed_mode = options[selected_idx]
        return get_speed_for_voice(voice_id, speed_mode)

    def _set_speed_value(self, val):
        """Sets the speed dropdown selection from an index (0, 1, 2), string name, or float speed value."""
        if not hasattr(self, 'speed_chooser') or not hasattr(self.speed_chooser, 'set_selected'):
            return
        options = getattr(self, 'SPEED_OPTIONS', SPEED_CHOICES)
        if isinstance(val, int) and 0 <= val < len(options):
            self.speed_chooser.set_selected(val)
            return
        if isinstance(val, str):
            for i, opt in enumerate(options):
                if opt.lower() == val.strip().lower():
                    self.speed_chooser.set_selected(i)
                    return
        if isinstance(val, (int, float)):
            voice_id = self._get_selected_voice_name() if hasattr(self, '_get_selected_voice_name') else ""
            speeds = [get_speed_for_voice(voice_id, opt) for opt in options]
            best_idx = 0
            best_diff = abs(speeds[0] - float(val))
            for i in range(1, len(speeds)):
                diff = abs(speeds[i] - float(val))
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            self.speed_chooser.set_selected(best_idx)

    def _on_speed_chooser_selected(self, dropdown, _param):
        """Called when user changes speed choice in dropdown."""
        if hasattr(self, 'adjustment_2') and isinstance(self.adjustment_2, Gtk.Adjustment):
            self.adjustment_2.set_value(self._get_current_speed())

    # Defines what happens when speed is changed
    def on_adjustment_value_changed(self, adjustment):
        value = adjustment.get_value()
        if hasattr(self, 'label_2') and self.label_2:
            self.label_2.set_text(f"× {value:.1f}")

    # The content of the text file is opened asynchronously so as not to block the application
    def open_file(self, file):
        file.load_contents_async(None, self.open_file_complete)

    # Is called when reading is finished or an error occurred
    def open_file_complete(self, file, result):
        try:
            contents = file.load_contents_finish(result)  # contains boolean variable, the read text, etc.
        except Exception as e:
            self._show_error(f"{_('Unable to open file')}: {e}")
            return

        if not contents[0]:
            path = file.peek_path()
            self._show_error(f"{_('Unable to open file')} {path}: {contents[1]}")
            return

        filename = file.get_basename() or ""
        file_stem, ext = os.path.splitext(filename.lower())

        if ext in ('.pdf', '.epub'):
            try:
                chapters = load_document_chapters(file, filename=filename, raw_bytes=contents[1])
            except Exception as e:
                self._show_error(f"{_('Unable to load document')}: {e}")
                return

            if not chapters:
                self._show_error(f"{_('No text could be extracted from')} {filename}")
                return

            if self.is_playing:
                self.stop_playback()

            cur_page = self.tab_view.get_selected_page() if (hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page')) else None
            cur_text = self._get_text_for_page(cur_page) if cur_page else ""

            if cur_page and not cur_text.strip() and (cur_page.get_title() == _("Untitled Document") or cur_page.get_title().startswith(_("Untitled"))):
                first_title, first_text = chapters[0]
                first_clean = clean_all_tags(first_text) if self.auto_remove_tags else first_text
                buffer = self.main_text_view.get_buffer()
                buffer.set_text(ensure_paragraph_gaps(first_clean))
                start = buffer.get_start_iter()
                buffer.place_cursor(start)
                cur_page.set_title(first_title)
                cur_page.set_tooltip(first_title)
                cur_page._file = file

                for ch_title, ch_text in chapters[1:]:
                    self.create_new_tab(title=ch_title, text=ch_text, file=file)
            else:
                for ch_title, ch_text in chapters:
                    self.create_new_tab(title=ch_title, text=ch_text, file=file)

            self._update_drop_placeholder_visibility()
            return

        # Check if the read content is text
        try:
            text = contents[1].decode('utf-8')
        except UnicodeError:
            try:
                text = contents[1].decode('latin-1')
            except Exception as err:
                self._show_error(f"{_('Unable to load file contents')}: {err}")
                return

        if self.is_playing:
            self.stop_playback()

        cur_page = self.tab_view.get_selected_page() if (hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page')) else None
        cur_text = self._get_text_for_page(cur_page) if cur_page else ""

        # If current tab is empty and untitled, load into it; otherwise open in a new tab
        if cur_page and not cur_text.strip() and (cur_page.get_title() == _("Untitled Document") or cur_page.get_title().startswith(_("Untitled"))):
            clean_loaded_text = clean_all_tags(text) if self.auto_remove_tags else text
            buffer = self.main_text_view.get_buffer()
            buffer.set_text(ensure_paragraph_gaps(clean_loaded_text))
            start = buffer.get_start_iter()
            buffer.place_cursor(start)
            cur_page.set_title(filename)
            cur_page.set_tooltip(filename)
            cur_page._file = file
        else:
            self.create_new_tab(title=filename, text=text, file=file)

    def save_text(self, file):
        if not self.main_text_view:
            return
        buffer = self.main_text_view.get_buffer()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        bytes_data = GLib.Bytes.new(text.encode('utf-8'))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(bytes_data,
                                          None,
                                          False,
                                          Gio.FileCreateFlags.NONE,
                                          None,
                                          self.save_text_complete)

    def save_text_complete(self, file, result):
        try:
            res = file.replace_contents_finish(result)
        except Exception as e:
            self._show_error(f"{_('Unable to save file')}: {e}")
            return

        info = file.query_info("standard::display-name",
                               Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()
        if not res:
            self._show_error(f"{_('Unable to save')} {display_name}")
        else:
            if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page'):
                cur_page = self.tab_view.get_selected_page()
                if cur_page:
                    cur_page.set_title(display_name)
                    cur_page.set_tooltip(display_name)
                    cur_page._file = file

    # Play the text
    def read_text(self, button=None):
        if not self.main_text_view:
            return

        if button is None:
            button = getattr(self, 'read_button', None)

        if self.is_playing:
            if self.is_paused:
                self.toggle_pause()
                return
            self.stop_playback(button)
            return

        buffer = self.main_text_view.get_buffer()

        # Check if there is an active text selection
        selection = buffer.get_selection_bounds()
        if selection:
            start_iter, end_iter = selection
            start_char_offset = start_iter.get_offset()
            text = buffer.get_text(start_iter, end_iter, False)
        else:
            # Determine cursor location or resume mark
            mark = buffer.get_mark("pause_resume_mark")
            insert_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(insert_mark)

            # Snap to start of word if cursor is placed inside a word
            if cursor_iter.inside_word() and not cursor_iter.starts_word():
                cursor_iter.backward_word_start()

            # If there is an active pause_resume_mark and cursor has not been moved elsewhere
            if mark:
                mark_iter = buffer.get_iter_at_mark(mark)
                if cursor_iter.get_offset() == 0 or cursor_iter.get_offset() == mark_iter.get_offset():
                    cursor_iter = mark_iter

            end_iter = buffer.get_end_iter()
            text_from_cursor = buffer.get_text(cursor_iter, end_iter, False)

            # If cursor is at the end or remaining text is empty/whitespace, fall back to entire text
            if not text_from_cursor.strip():
                start_iter = buffer.get_start_iter()
                start_char_offset = 0
                text = buffer.get_text(start_iter, end_iter, False)
            else:
                start_iter = cursor_iter
                start_char_offset = start_iter.get_offset()
                text = text_from_cursor

        # Intercept empty text and show a friendly error
        if not text.strip():
            self._show_error(_("No text to read!"))
            return

        engine = 'piper'
        selected_voice = self._get_selected_voice_name()
        pitch = self._get_pitch_for_voice(selected_voice)
        speed = self.speed_chooser.get_value()

        self.start_playback(button, text, engine, self.lang_code, selected_voice, pitch, speed, start_char_offset=start_char_offset)


    def toggle_pause(self, button=None):
        """Toggles between paused and playing states, handling voice/speech setting changes on resume."""
        if not self.is_playing or not hasattr(self, 'reader') or not self.reader:
            return

        if self.is_paused:
            current_voice = self._get_selected_voice_name()
            current_lang = self.lang_code
            current_pitch = self._get_pitch_for_voice(current_voice)
            current_speed = self.speed_chooser.get_value()

            reader_voice = getattr(self.reader, 'selected_voice', None)
            reader_lang = getattr(self.reader, 'lang_code', None)
            reader_pitch = getattr(self.reader, 'pitch', current_pitch)
            reader_speed = getattr(self.reader, 'speed', current_speed)

            voice_changed = (reader_voice is not None and current_voice.strip().lower() != reader_voice.strip().lower())
            lang_changed = (reader_lang is not None and current_lang != reader_lang)
            pitch_changed = (abs(reader_pitch - current_pitch) > 1e-4)
            speed_changed = (abs(reader_speed - current_speed) > 1e-4)

            if voice_changed or lang_changed or pitch_changed or speed_changed:
                self._resume_with_new_settings(
                    current_voice,
                    current_lang,
                    current_pitch,
                    current_speed
                )
                return

            if self.reader.resume_audio():
                self.is_paused = False
                cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
                if cur_page:
                    cur_page._is_paused = False
                self._set_button_icon(self.pause_button, "media-playback-pause-symbolic", 25)
                self.pause_button.set_tooltip_text(_("Pause"))
                if getattr(self, '_highlight_timeout_id', None) is None:
                    self._highlight_timeout_id = GLib.timeout_add(30, self._update_highlight)
                self._notify_bubble_playback_state()
            else:
                self._resume_with_new_settings(
                    current_voice,
                    current_lang,
                    current_pitch,
                    current_speed
                )
                return
        else:
            if self.reader.pause_audio():
                self.is_paused = True
                cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
                if cur_page:
                    cur_page._is_paused = True
                self._set_button_icon(self.pause_button, "media-playback-start-symbolic", 25)
                self.pause_button.set_tooltip_text(_("Resume"))

                # Record paused text position using a TextMark so text edits or shifts are tracked
                char_offset = self._get_current_playback_char_offset()
                buffer = self.main_text_view.get_buffer()
                total_chars = buffer.get_char_count()
                clamped_offset = max(0, min(char_offset, total_chars))
                iter_at_pause = buffer.get_iter_at_offset(clamped_offset)
                mark = buffer.get_mark("pause_resume_mark")
                if mark:
                    buffer.move_mark(mark, iter_at_pause)
                else:
                    buffer.create_mark("pause_resume_mark", iter_at_pause, left_gravity=False)
                buffer.place_cursor(iter_at_pause)

                self._notify_bubble_playback_state()

    def _get_current_playback_char_offset(self):
        """Calculates the character offset in the main text buffer where playback is currently located."""
        word_timings = getattr(self.reader, 'word_timings', [])

        # 1. Query GStreamer's exact paused timestamp
        if hasattr(self.reader, 'get_playback_position') and word_timings:
            pos = self.reader.get_playback_position()
            if isinstance(pos, (int, float)) and pos >= 0:
                for w in word_timings:
                    if w['start_time'] <= pos <= w['end_time']:
                        return w['start_char']
                for w in word_timings:
                    if w['start_time'] >= pos:
                        return w['start_char']
                if word_timings:
                    return word_timings[-1]['start_char']

        # 2. Check active highlighted word index
        if self._current_highlight_index is not None and 0 <= self._current_highlight_index < len(word_timings):
            return word_timings[self._current_highlight_index]['start_char']

        # 3. Fallback: start offset of the current reader session
        return getattr(self.reader, 'start_char_offset', 0)

    def _resume_with_new_settings(self, current_voice, current_lang, current_pitch, current_speed):
        """Resumes playback from the paused position using updated voice and speech settings."""
        buffer = self.main_text_view.get_buffer()
        total_chars = buffer.get_char_count()

        # Check for pause_resume_mark first
        mark = buffer.get_mark("pause_resume_mark")
        if mark:
            resume_char_offset = buffer.get_iter_at_mark(mark).get_offset()
            buffer.delete_mark(mark)
        else:
            resume_char_offset = self._get_current_playback_char_offset()

        # Original reading bounds
        orig_start = getattr(self.reader, 'start_char_offset', 0)
        orig_text = getattr(self.reader, 'original_text', '')
        orig_len = len(orig_text)

        if orig_len > 0:
            end_char_offset = min(orig_start + orig_len, total_chars)
        else:
            end_char_offset = total_chars

        resume_char_offset = max(0, min(resume_char_offset, total_chars))
        end_char_offset = max(resume_char_offset, min(end_char_offset, total_chars))

        start_iter = buffer.get_iter_at_offset(resume_char_offset)
        end_iter = buffer.get_iter_at_offset(end_char_offset)
        remaining_text = buffer.get_text(start_iter, end_iter, False)

        if not remaining_text.strip():
            self.stop_playback()
            return

        # Stop previous audio pipeline and clear highlight timer
        if hasattr(self, 'reader') and self.reader:
            self.reader.stop_audio()

        if getattr(self, '_highlight_timeout_id', None) is not None:
            GLib.source_remove(self._highlight_timeout_id)
            self._highlight_timeout_id = None

        # Highlight the resume word immediately for visual continuity
        first_word = remaining_text.split(None, 1)[0] if remaining_text.split() else remaining_text
        self._highlight_word(resume_char_offset, resume_char_offset + len(first_word))

        # Start playback of remaining text with new settings
        self.is_playing = False
        self.is_paused = False
        self.start_playback(
            self.read_button,
            remaining_text,
            'piper',
            current_lang,
            current_voice,
            current_pitch,
            current_speed,
            start_char_offset=resume_char_offset
        )

    def start_playback(self, button, text, engine, lang_code, selected_voice, pitch, speed, start_char_offset=0):
        """Starts playback and updates UI"""
        if not self.is_playing:
            # Lock text view so user edits do not shift character offsets during playback
            if hasattr(self, 'main_text_view') and self.main_text_view:
                self.main_text_view.set_editable(False)

            lang = lang_code or self.lang_code
            current_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
            cached_reader = getattr(current_page, '_reader', None) if current_page else getattr(self, 'reader', None)
            if not cached_reader:
                cached_reader = getattr(self, 'reader', None)

            has_matching_audio = (
                cached_reader is not None
                and getattr(cached_reader, 'temp_path', None)
                and os.path.exists(cached_reader.temp_path)
                and getattr(cached_reader, 'original_text', None) == text
                and getattr(cached_reader, 'start_char_offset', 0) == start_char_offset
                and getattr(cached_reader, 'selected_voice', None) == selected_voice
                and abs(getattr(cached_reader, 'pitch', 0) - pitch) < 1e-4
                and abs(getattr(cached_reader, 'speed', 0) - speed) < 1e-4
                and getattr(cached_reader, 'lang_code', None) == lang
            )

            if has_matching_audio and hasattr(cached_reader, 'play_cached_audio') and cached_reader.play_cached_audio():
                self.reader = cached_reader
                self.reader.window = self
            else:
                self.reader = Reader(text, engine, lang, selected_voice, pitch, speed, window=self, start_char_offset=start_char_offset)

            if current_page:
                current_page._reader = self.reader
                current_page._is_playing = True
                current_page._is_paused = False

            self.is_playing = True
            self.is_paused = False
            self._current_highlight_index = None
            if self._highlight_timeout_id is None:
                self._highlight_timeout_id = GLib.timeout_add(30, self._update_highlight)

            self._set_button_icon(button, "media-playback-stop-symbolic", 25)
            button.set_tooltip_text(_("Stop"))
            self.pause_button.set_sensitive(True)
            self._set_button_icon(self.pause_button, "media-playback-pause-symbolic", 25)
            self.pause_button.set_tooltip_text(_("Pause"))
            self._update_seek_buttons_visibility()
            self._notify_bubble_playback_state()

    def stop_playback(self, button=None):
        """Stops playback and updates UI"""
        if button is None:
            button = self.read_button

        # Re-enable text editing
        if hasattr(self, 'main_text_view') and self.main_text_view:
            self.main_text_view.set_editable(True)
            buffer = self.main_text_view.get_buffer()
            mark = buffer.get_mark("pause_resume_mark")
            if mark:
                buffer.delete_mark(mark)

        self._clear_highlight()
        if hasattr(self, 'reader') and self.reader:
            self.reader.stop_audio()
        self.is_playing = False
        self.is_paused = False
        cur_page = self.tab_view.get_selected_page() if hasattr(self, 'tab_view') and hasattr(self.tab_view, 'get_selected_page') else None
        if cur_page:
            cur_page._is_playing = False
            cur_page._is_paused = False
            cur_page._highlight_index = None
        self._set_button_icon(button, "media-playback-start-symbolic", 25)
        button.set_tooltip_text(_("Read Text"))
        self.pause_button.set_sensitive(False)
        self._set_button_icon(self.pause_button, "media-playback-pause-symbolic", 25)
        self.pause_button.set_tooltip_text(_("Pause"))
        self._update_seek_buttons_visibility()
        self._notify_bubble_playback_state()

    def rewind_15s(self, button=None):
        """Rewinds audio playback by 15 seconds."""
        return self.seek_playback(-15)

    def forward_15s(self, button=None):
        """Forwards audio playback by 15 seconds."""
        return self.seek_playback(15)

    def _update_playback_toolbar_visibility(self):
        """Shows popup playback toolbar and hides fixed read button during playback; reverses when stopped."""
        is_playing = bool(getattr(self, 'is_playing', False))

        if hasattr(self, 'playback_toolbar_revealer') and hasattr(self.playback_toolbar_revealer, 'set_reveal_child'):
            self.playback_toolbar_revealer.set_reveal_child(is_playing)

        # In fixed toolbar, hide read_button during playback to save space, show when idle
        if hasattr(self, 'read_button') and hasattr(self.read_button, 'set_visible'):
            self.read_button.set_visible(not is_playing)

        # Ensure pause button sensitivity in popup toolbar
        if hasattr(self, 'pause_button') and hasattr(self.pause_button, 'set_sensitive'):
            self.pause_button.set_sensitive(is_playing)

        # Ensure individual controls reflect playback state (for direct widget access & headless tests)
        if hasattr(self, 'rewind_button') and hasattr(self.rewind_button, 'set_visible'):
            self.rewind_button.set_visible(is_playing)
        if hasattr(self, 'forward_button') and hasattr(self.forward_button, 'set_visible'):
            self.forward_button.set_visible(is_playing)
        if hasattr(self, 'stop_button') and hasattr(self.stop_button, 'set_visible'):
            self.stop_button.set_visible(is_playing)

    def _update_seek_buttons_visibility(self):
        """Backward-compatible alias for _update_playback_toolbar_visibility."""
        self._update_playback_toolbar_visibility()

    def seek_playback(self, seconds_delta: float) -> bool:
        """Seeks playback relatively by seconds_delta (+15s forward, -15s backward). If paused, scrolls to position and resumes."""
        if not self.is_playing or not hasattr(self, 'reader') or not self.reader:
            return False
        if hasattr(self.reader, 'seek'):
            was_paused = self.is_paused
            success = self.reader.seek(seconds_delta)
            if success:
                # Update text highlight position immediately and scroll to it
                if hasattr(self, '_update_highlight'):
                    try:
                        self._update_highlight(force=True)
                    except TypeError:
                        self._update_highlight()
                # If paused, update pause_resume_mark to match new sought position
                if hasattr(self, 'main_text_view') and self.main_text_view:
                    char_offset = self._get_current_playback_char_offset()
                    buffer = self.main_text_view.get_buffer()
                    total_chars = buffer.get_char_count()
                    clamped_offset = max(0, min(char_offset, total_chars))
                    iter_at_pause = buffer.get_iter_at_offset(clamped_offset)
                    mark = buffer.get_mark("pause_resume_mark")
                    if mark:
                        buffer.move_mark(mark, iter_at_pause)
                    else:
                        buffer.create_mark("pause_resume_mark", iter_at_pause, left_gravity=False)
                # If paused, resume playback
                if was_paused and hasattr(self, 'toggle_pause'):
                    self.toggle_pause()
            return success
        return False

    def _notify_bubble_playback_state(self):
        """Notifies the Quick Listener bubble of current playback state."""
        bubble = getattr(self, 'bubble', None)
        if not bubble:
            try:
                app = self.get_application()
                if app and hasattr(app, 'bubble'):
                    bubble = app.bubble
            except Exception:
                pass
        if bubble and hasattr(bubble, 'update_playback_state'):
            try:
                bubble.update_playback_state(self.is_playing, self.is_paused)
            except Exception:
                pass

    def _update_highlight(self, force: bool = False):
        """Timer callback that checks playback position and updates the highlighted word."""
        if not self.is_playing:
            self._clear_highlight()
            return False

        if self.is_paused and not force:
            return True

        if not hasattr(self, 'reader') or not self.reader or not hasattr(self.reader, 'get_playback_position'):
            return True

        pos = self.reader.get_playback_position()
        if not isinstance(pos, (int, float)) or pos < 0:
            return True

        word_timings = getattr(self.reader, 'word_timings', None)
        if not word_timings:
            return True

        # Fast path check around last active index
        active_idx = None
        cur = self._current_highlight_index if self._current_highlight_index is not None else 0
        if 0 <= cur < len(word_timings) and word_timings[cur]['start_time'] <= pos <= word_timings[cur]['end_time']:
            active_idx = cur
        elif 0 <= cur + 1 < len(word_timings) and word_timings[cur + 1]['start_time'] <= pos <= word_timings[cur + 1]['end_time']:
            active_idx = cur + 1
        elif pos <= word_timings[0]['start_time']:
            active_idx = 0
        elif pos >= word_timings[-1]['end_time']:
            active_idx = len(word_timings) - 1
        else:
            # Binary search
            low = 0
            high = len(word_timings) - 1
            while low <= high:
                mid = (low + high) // 2
                if word_timings[mid]['start_time'] <= pos <= word_timings[mid]['end_time']:
                    active_idx = mid
                    break
                elif pos < word_timings[mid]['start_time']:
                    high = mid - 1
                else:
                    low = mid + 1

        if active_idx is not None and (force or active_idx != self._current_highlight_index):
            self._current_highlight_index = active_idx
            w = word_timings[active_idx]
            self._highlight_word(w['start_char'], w['end_char'], force_scroll=force)

        return True

    def _highlight_word(self, start_char, end_char, force_scroll=False):
        """Applies word highlight tag to the specified character range and scrolls into view."""
        buffer = self.main_text_view.get_buffer()
        max_len = buffer.get_char_count()
        start_char = max(0, min(start_char, max_len))
        end_char = max(start_char, min(end_char, max_len))

        # Clear existing highlight
        start_bound, end_bound = buffer.get_bounds()
        buffer.remove_tag_by_name("current_word_highlight", start_bound, end_bound)

        # Apply new highlight
        start_iter = buffer.get_iter_at_offset(start_char)
        end_iter = buffer.get_iter_at_offset(end_char)
        buffer.apply_tag_by_name("current_word_highlight", start_iter, end_iter)
        if hasattr(self.main_text_view, "set_highlight_range"):
            self.main_text_view.set_highlight_range(start_char, end_char)

        # Auto-scroll so active word always stays in the middle of the screen (50% vertically)
        parent = self.main_text_view.get_parent() if hasattr(self.main_text_view, "get_parent") else None
        vadj = parent.get_vadjustment() if parent and hasattr(parent, "get_vadjustment") else None
        page_size = vadj.get_page_size() if vadj else 0

        if page_size > 0:
            desired_bottom_margin = max(350, int(page_size * 0.5))
            if hasattr(self.main_text_view, "get_bottom_margin") and hasattr(self.main_text_view, "set_bottom_margin"):
                if self.main_text_view.get_bottom_margin() != desired_bottom_margin:
                    self.main_text_view.set_bottom_margin(desired_bottom_margin)

        loc = self.main_text_view.get_iter_location(start_iter)
        line_idx = start_iter.get_line()
        last_y = getattr(self, "_last_scrolled_line_y", None)
        last_idx = getattr(self, "_last_scrolled_line_idx", None)

        # Only scroll when active word transitions to a different visual line or paragraph,
        # or when forced/off-screen. This completely eliminates jumping/flickering between words on the same line.
        line_changed = (
            (last_y is None)
            or (last_idx is None)
            or (line_idx != last_idx)
            or (abs(loc.y - last_y) >= 4)
            or force_scroll
        )
        if not line_changed and vadj and page_size > 0:
            val = vadj.get_value()
            if loc.y < val or (loc.y + loc.height) > (val + page_size):
                line_changed = True

        if line_changed:
            self._last_scrolled_line_y = loc.y
            self._last_scrolled_line_idx = line_idx
            if hasattr(self.main_text_view, "scroll_to_iter"):
                self.main_text_view.scroll_to_iter(start_iter, 0.0, True, 0.0, 0.5)

    def _clear_highlight(self):
        """Clears any active word highlight and removes the timer."""
        if hasattr(self, 'main_text_view') and self.main_text_view:
            buffer = self.main_text_view.get_buffer()
            start_bound, end_bound = buffer.get_bounds()
            buffer.remove_tag_by_name("current_word_highlight", start_bound, end_bound)
            if hasattr(self.main_text_view, "set_highlight_range"):
                self.main_text_view.set_highlight_range(None, None)

        self._current_highlight_index = None
        self._last_scrolled_line_y = None
        self._last_scrolled_line_idx = None
        if getattr(self, '_highlight_timeout_id', None) is not None:
            GLib.source_remove(self._highlight_timeout_id)
            self._highlight_timeout_id = None

    @property
    def auto_remove_tags(self) -> bool:
        if hasattr(self, '_auto_remove_tags_action') and self._auto_remove_tags_action:
            state = self._auto_remove_tags_action.get_state()
            if state:
                return state.get_boolean()
        return getattr(self, '_auto_remove_tags', True)

    @auto_remove_tags.setter
    def auto_remove_tags(self, value: bool):
        self.set_auto_remove_tags(value)

    def set_auto_remove_tags(self, active: bool):
        self._auto_remove_tags = bool(active)
        if hasattr(self, '_auto_remove_tags_action') and self._auto_remove_tags_action:
            self._auto_remove_tags_action.set_state(GLib.Variant.new_boolean(bool(active)))

    def _on_auto_remove_tags_change_state(self, action, value):
        action.set_state(value)
        self._auto_remove_tags = value.get_boolean()
        if self._auto_remove_tags and self.main_text_view:
            buf = self.main_text_view.get_buffer()
            if buf and self.main_text_view.get_editable():
                start, end = buf.get_bounds()
                current_text = buf.get_text(start, end, True)
                clean_text = clean_all_tags(current_text)
                if clean_text != current_text:
                    buf.begin_user_action()
                    buf.set_text(clean_text)
                    buf.end_user_action()

    def show_font_zoom_popup(self):
        pass

    def hide_font_zoom_popup(self, *args, **kwargs):
        pass

    def dismiss_font_zoom_popup(self):
        pass

    def is_font_zoom_popup_showing(self):
        return True

    def set_text_zoom(self, percentage: int):
        """Applies dynamic font scale to the text view only (between 70% and 1000%)"""
        self.text_zoom_level = max(70, min(int(percentage), 1000))
        css = f".zoomable-text text, .zoomable-text {{ font-size: {self.text_zoom_level}%; }}".encode("utf-8")
        self.text_zoom_provider.load_from_data(css)
        if hasattr(self, 'font_zoom_label') and self.font_zoom_label:
            self.font_zoom_label.set_label(f"{self.text_zoom_level}%")

    def zoom_in(self):
        """Increases text font size by 20%"""
        self.set_text_zoom(self.text_zoom_level + 20)

    def zoom_out(self):
        """Decreases text font size by 20%"""
        self.set_text_zoom(self.text_zoom_level - 20)

    def zoom_reset(self):
        """Resets text font size to default 130%"""
        self.set_text_zoom(130)

    def play_audio(self):
        """Play/Pause toggle action (Ctrl + P). Starts playback or resumes if paused. If playing and not paused, pauses."""
        if self.is_playing:
            self.toggle_pause()
        else:
            self.read_text(self.read_button)

    def increase_speed(self, step=0.1):
        """Increases speaking speed (Ctrl + Up), stepping through Normal -> Fast -> Super Fast."""
        if hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_selected') and hasattr(self.speed_chooser, 'set_selected'):
            curr = self.speed_chooser.get_selected()
            options = getattr(self, 'SPEED_OPTIONS', SPEED_CHOICES)
            if curr < len(options) - 1:
                self.speed_chooser.set_selected(curr + 1)
            elif curr < 0:
                self.speed_chooser.set_selected(0)
        elif hasattr(self, 'adjustment_2') and isinstance(self.adjustment_2, Gtk.Adjustment):
            upper = self.adjustment_2.get_upper() if hasattr(self.adjustment_2, 'get_upper') else 2.0
            new_val = min(round(self.adjustment_2.get_value() + (step or 0.1), 1), upper)
            self.adjustment_2.set_value(new_val)
        elif hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_value') and hasattr(self.speed_chooser, 'set_value'):
            new_val = min(round(self.speed_chooser.get_value() + (step or 0.1), 1), 2.0)
            self.speed_chooser.set_value(new_val)

    def decrease_speed(self, step=0.1):
        """Decreases speaking speed (Ctrl + Down), stepping down through Super Fast -> Fast -> Normal."""
        if hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_selected') and hasattr(self.speed_chooser, 'set_selected'):
            curr = self.speed_chooser.get_selected()
            if curr > 0:
                self.speed_chooser.set_selected(curr - 1)
        elif hasattr(self, 'adjustment_2') and isinstance(self.adjustment_2, Gtk.Adjustment):
            lower = self.adjustment_2.get_lower() if hasattr(self.adjustment_2, 'get_lower') else 0.1
            new_val = max(round(self.adjustment_2.get_value() - (step or 0.1), 1), lower)
            self.adjustment_2.set_value(new_val)
        elif hasattr(self, 'speed_chooser') and hasattr(self.speed_chooser, 'get_value') and hasattr(self.speed_chooser, 'set_value'):
            new_val = max(round(self.speed_chooser.get_value() - (step or 0.1), 1), 0.1)
            self.speed_chooser.set_value(new_val)

    def _update_window_controls_tooltips(self, *args):
        """Sets tooltips on the header bar's minimize, maximize, and close window controls."""
        if not hasattr(self, 'header_bar') or not self.header_bar:
            return

        is_max = self.is_maximized() if hasattr(self, 'is_maximized') else False

        def walk(widget):
            if isinstance(widget, Gtk.WindowControls):
                child = widget.get_first_child()
                while child:
                    classes = child.get_css_classes()
                    if "minimize" in classes:
                        self._btn_minimize = child
                        child.set_tooltip_text(_("Minimize"))
                    elif "maximize" in classes:
                        self._btn_maximize = child
                        child.set_tooltip_text(_("Restore") if is_max else _("Maximize"))
                    elif "close" in classes:
                        self._btn_close = child
                        child.set_tooltip_text(_("Close"))
                    child = child.get_next_sibling()
            c = widget.get_first_child()
            while c:
                walk(c)
                c = c.get_next_sibling()

        walk(self.header_bar)

    def minimize_window(self, *args):
        """Minimizes the main application window."""
        self.minimize()

    def toggle_maximize_window(self, *args):
        """Toggles between maximized and unmaximized states for the main application window."""
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()
        self._update_window_controls_tooltips()

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handles keyboard shortcuts including Ctrl + / - / 0 for zoom, Ctrl + P for play,
        Ctrl + E for export audio, Ctrl + Up / Down for speed, F5 for play/pause, F11 for maximize, and Escape for stop."""
        if state & Gdk.ModifierType.CONTROL_MASK:
            if keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
                self.zoom_in()
                return True
            elif keyval in (Gdk.KEY_minus, Gdk.KEY_underscore, Gdk.KEY_KP_Subtract):
                self.zoom_out()
                return True
            elif keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
                self.zoom_reset()
                return True
            elif keyval in (Gdk.KEY_t, Gdk.KEY_T):
                self.create_new_tab()
                return True
            elif keyval in (Gdk.KEY_w, Gdk.KEY_W):
                self._on_close_current_tab_action()
                return True
            elif keyval in (Gdk.KEY_p, Gdk.KEY_P):
                self.play_audio()
                return True
            elif keyval in (Gdk.KEY_e, Gdk.KEY_E):
                self.save_audio_dialog()
                return True
            elif keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
                self.increase_speed()
                return True
            elif keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                self.decrease_speed()
                return True
            elif keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
                if self.is_playing:
                    self.rewind_15s()
                    return True
            elif keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
                if self.is_playing:
                    self.forward_15s()
                    return True
        elif keyval == Gdk.KEY_F5:
            if self.is_playing:
                self.toggle_pause()
            else:
                self.read_text(self.read_button)
            return True
        elif keyval == Gdk.KEY_F11:
            self.toggle_maximize_window()
            return True
        elif keyval == Gdk.KEY_Escape:
            if self.is_playing:
                self.stop_playback(self.read_button)
                return True
        return False

    def _on_scroll(self, controller, dx, dy):
        """Handles Ctrl + Mouse Scroll Wheel zooming on the text view"""
        state = controller.get_current_event_state()
        if state & Gdk.ModifierType.CONTROL_MASK:
            if dy < 0:
                self.zoom_in()
                return True
            elif dy > 0:
                self.zoom_out()
                return True
        return False
