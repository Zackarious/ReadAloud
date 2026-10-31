# bubble.py
#
# Copyright 2026 zackarious
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

import os
import math
from pathlib import Path
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, Gio, GLib, Graphene, GObject
import cairo
import gettext
_ = gettext.gettext

_REWIND_15_SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<svg height="24px" viewBox="0 0 24 24" width="24px" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M 12 5 V 1 L 7 6 l 5 5 V 7 c 3.31 0 6 2.69 6 6 s -2.69 6 -6 6 s -6 -2.69 -6 -6 H 4 c 0 4.42 3.58 8 8 8 s 8 -3.58 8 -8 s -3.58 -8 -8 -8 z '
    'M 8.5 11.2 L 7.4 11.9 L 7.4 10.6 L 8.8 9.6 L 9.8 9.6 L 9.8 16.4 L 8.5 16.4 Z '
    'M 11.5 9.6 L 14.7 9.6 L 14.7 10.8 L 12.7 10.8 L 12.4 12.2 C 12.7 12.0 13.2 11.9 13.7 11.9 C 14.8 11.9 15.6 12.7 15.6 14.1 C 15.6 15.5 14.6 16.4 13.3 16.4 C 12.2 16.4 11.4 15.8 11.1 14.8 L 12.3 14.4 C 12.5 15.0 12.8 15.3 13.3 15.3 C 13.9 15.3 14.3 14.8 14.3 14.1 C 14.3 13.4 13.9 12.9 13.3 12.9 C 12.9 12.9 12.5 13.2 12.4 13.5 L 11.2 13.2 Z" '
    'fill="#fee14d" style="fill:#fee14d;fill-opacity:1;" />'
    '</svg>'
)

_FORWARD_15_SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<svg height="24px" viewBox="0 0 24 24" width="24px" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M 12 5 V 1 l 5 5 -5 5 V 7 c -3.31 0 -6 2.69 -6 6 s 2.69 6 6 6 6 -2.69 6 -6 h 2 c 0 4.42 -3.58 8 -8 8 s -8 -3.58 -8 -8 3.58 -8 8 -8 z '
    'M 8.5 11.2 L 7.4 11.9 L 7.4 10.6 L 8.8 9.6 L 9.8 9.6 L 9.8 16.4 L 8.5 16.4 Z '
    'M 11.5 9.6 L 14.7 9.6 L 14.7 10.8 L 12.7 10.8 L 12.4 12.2 C 12.7 12.0 13.2 11.9 13.7 11.9 C 14.8 11.9 15.6 12.7 15.6 14.1 C 15.6 15.5 14.6 16.4 13.3 16.4 C 12.2 16.4 11.4 15.8 11.1 14.8 L 12.3 14.4 C 12.5 15.0 12.8 15.3 13.3 15.3 C 13.9 15.3 14.3 14.8 14.3 14.1 C 14.3 13.4 13.9 12.9 13.3 12.9 C 12.9 12.9 12.5 13.2 12.4 13.5 L 11.2 13.2 Z" '
    'fill="#fee14d" style="fill:#fee14d;fill-opacity:1;" />'
    '</svg>'
)

_STOP_SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<svg height="24px" viewBox="0 0 24 24" width="24px" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M 7.5 5 h 9 a 2.5 2.5 0 0 1 2.5 2.5 v 9 a 2.5 2.5 0 0 1 -2.5 2.5 h -9 a 2.5 2.5 0 0 1 -2.5 -2.5 v -9 a 2.5 2.5 0 0 1 2.5 -2.5 z" '
    'fill="#fee14d" style="fill:#fee14d;fill-opacity:1;" />'
    '</svg>'
)

BUBBLE_CSS = """
window.listener-bubble-window,
window.listener-bubble-window.background,
.listener-bubble-window {
    background-color: transparent;
    background: none;
    box-shadow: none;
    border: none;
}

.listener-bubble-box {
    min-width: 216px;
    min-height: 216px;
    background-color: transparent;
    background: none;
    box-shadow: none;
    border: none;
    border-radius: 0;
}

.listener-bubble-box.expanded,
.listener-bubble-box.expanded:hover {
    min-width: 216px;
    min-height: 216px;
    background-color: transparent;
    background: none;
    border: none;
    border-radius: 0;
    box-shadow: none;
}

.listener-bubble-box:not(.expanded):hover {
    background-color: transparent;
    border: none;
    box-shadow: none;
}

.listener-bubble-box.reading {
    background-color: #000000;
    border: 2.5px solid #ffffff;
    box-shadow: none;
}

.listener-bubble-box.paused {
    background-color: #000000;
    border: 2.5px solid #ffffff;
    box-shadow: none;
}

.listener-bubble-box.error {
    background: #451010;
    border: 2.5px solid #e01b24;
    box-shadow: none;
}

.listener-bubble-sub-button {
    min-width: 54px;
    min-height: 54px;
    border-radius: 50%;
    background: transparent;
    transition: background-color 150ms ease-in-out, transform 150ms ease-in-out;
}

.listener-bubble-sub-button.hovered {
    background-color: rgba(255, 255, 255, 0.18);
    transform: scale(1.08);
}

.listener-bubble-sub-button.active {
    background-color: rgba(255, 255, 255, 0.30);
    transform: scale(0.92);
}

.listener-bubble-icon,
.listener-bubble-box image,
.listener-bubble-box .listener-bubble-icon,
.listener-bubble-sub-icon {
    color: #fee14d;
    transition: transform 180ms ease-in-out, opacity 180ms ease-in-out;
}

.listener-bubble-icon.icon-flip {
    transform: scale(0.75) rotateY(180deg);
}

.listener-bubble-sub-icon.icon-bounce {
    transform: scale(0.85);
}
"""


class MiddleRowBox(Gtk.Box):
    """Middle horizontal row holding Rewind (left), Center (Pause/Play/Speaker), and Forward (right)."""
    __gtype_name__ = "MiddleRowBox"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0.0
        self.rewind_box = None
        self.center_box = None
        self.forward_box = None

    def do_snapshot(self, snapshot):
        parent = self.get_parent()
        p = getattr(self, "progress", None)
        if p is None or (parent and hasattr(parent, "progress")):
            p = getattr(parent, "progress", 1.0)

        # When expanded or fully progressed, snapshot all visible children directly
        if p >= 0.995 or (parent and parent.has_css_class("expanded") and p >= 0.99):
            child = self.get_first_child()
            while child:
                if child.get_visible():
                    self.snapshot_child(child, snapshot)
                child = child.get_next_sibling()
            return

        ep = p * p * (3.0 - 2.0 * p)

        child = self.get_first_child()
        while child:
            if not child.get_visible():
                child = child.get_next_sibling()
                continue
            dx = 0.0
            dy = 0.0
            op = 1.0
            if child == self.rewind_box:
                dx = (1.0 - ep) * 72.0
                op = ep
            elif child == self.forward_box:
                dx = -(1.0 - ep) * 72.0
                op = ep
            elif child == self.center_box:
                dx = 0.0
                op = 1.0

            if op > 0.005:
                snapshot.save()
                if op < 0.995:
                    snapshot.push_opacity(op)
                if abs(dx) > 0.1 or abs(dy) > 0.1:
                    pt = Graphene.Point()
                    pt.init(dx, dy)
                    snapshot.translate(pt)
                self.snapshot_child(child, snapshot)
                if op < 0.995:
                    snapshot.pop()
                snapshot.restore()

            child = child.get_next_sibling()


class PlusBubbleBox(Gtk.Box):
    """Custom container that renders a plus-style cross background with outward animation."""
    __gtype_name__ = "PlusBubbleBox"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0.0
        self.export_box = None
        self.middle_box = None
        self.stop_box = None

    def do_snapshot(self, snapshot):
        w = max(self.get_width(), 216)
        h = max(self.get_height(), 216)
        p = getattr(self, "progress", 0.0)
        ep = p * p * (3.0 - 2.0 * p)

        bounds = Graphene.Rect()
        bounds.init(0, 0, w, h)
        cr = snapshot.append_cairo(bounds)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        cx, cy = 108.0, 108.0
        r = 36.0

        if self.has_css_class("expanded") or p > 0.001:
            arm = 72.0 * ep

            # Trace outer perimeter of the plus shape (outer border only, no inner borders)
            cr.new_sub_path()
            if arm < 0.5:
                cr.arc(cx, cy, r, 0, 2 * math.pi)
                cr.close_path()
            else:
                # Top arm semicircle
                cr.arc(cx, cy - arm, r, math.pi, 0)
                # Right edge of top arm down to top-right inner corner
                cr.line_to(cx + r, cy - r)
                # Top edge of right arm to right semicircle start
                cr.line_to(cx + arm, cy - r)
                # Right arm semicircle
                cr.arc(cx + arm, cy, r, -math.pi / 2.0, math.pi / 2.0)
                # Bottom edge of right arm to bottom-right inner corner
                cr.line_to(cx + r, cy + r)
                # Right edge of bottom arm to bottom semicircle start
                cr.line_to(cx + r, cy + arm)
                # Bottom arm semicircle
                cr.arc(cx, cy + arm, r, 0, math.pi)
                # Left edge of bottom arm to bottom-left inner corner
                cr.line_to(cx - r, cy + r)
                # Bottom edge of left arm to left semicircle start
                cr.line_to(cx - arm, cy + r)
                # Left arm semicircle
                cr.arc(cx - arm, cy, r, math.pi / 2.0, 3.0 * math.pi / 2.0)
                # Top edge of left arm to top-left inner corner
                cr.line_to(cx - r, cy - r)
                # Left edge of top arm up to top semicircle start
                cr.line_to(cx - r, cy - arm)
                cr.close_path()

            # Fill with solid black
            cr.set_source_rgb(0, 0, 0)
            cr.fill_preserve()

            # Stroke outer perimeter with solid white border (2.5px) - NO inner lines
            cr.set_source_rgb(1, 1, 1)
            cr.set_line_width(2.5)
            cr.stroke()
        else:
            # Compact circular bubble centered at (108, 108) with radius 36
            cr.new_sub_path()
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.close_path()
            if getattr(self, "_is_compact_hovered", False):
                cr.set_source_rgb(0.067, 0.067, 0.067)
            else:
                cr.set_source_rgb(0, 0, 0)
            cr.fill_preserve()
            cr.set_source_rgb(1, 1, 1)
            cr.set_line_width(2.5)
            cr.stroke()

        # Snapshot child widgets
        if p >= 0.995 or (self.has_css_class("expanded") and p >= 0.99):
            child = self.get_first_child()
            while child:
                if child.get_visible():
                    self.snapshot_child(child, snapshot)
                child = child.get_next_sibling()
            return

        child = self.get_first_child()
        while child:
            if not child.get_visible():
                child = child.get_next_sibling()
                continue
            dx = 0.0
            dy = 0.0
            op = 1.0
            if child == self.export_box:
                dy = (1.0 - ep) * 72.0
                op = ep
            elif child == self.stop_box:
                dy = -(1.0 - ep) * 72.0
                op = ep
            elif child == self.middle_box:
                self.middle_box.progress = p
                op = 1.0

            if op > 0.005:
                snapshot.save()
                if op < 0.995:
                    snapshot.push_opacity(op)
                if abs(dx) > 0.1 or abs(dy) > 0.1:
                    pt = Graphene.Point()
                    pt.init(dx, dy)
                    snapshot.translate(pt)
                self.snapshot_child(child, snapshot)
                if op < 0.995:
                    snapshot.pop()
                snapshot.restore()

            child = child.get_next_sibling()


_css_initialized = False
_resources_initialized = False

def _ensure_bubble_css():
    global _css_initialized
    if _css_initialized:
        return
    display = Gdk.Display.get_default()
    if display:
        provider = Gtk.CssProvider()
        provider.load_from_data(BUBBLE_CSS.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        _css_initialized = True


def _ensure_bubble_resources():
    """Ensures application gresources and icon theme paths are registered for the bubble."""
    global _resources_initialized
    _ensure_bubble_css()
    if _resources_initialized:
        return

    try:
        from .paths import get_resource_bundle_path
        bundle_path = get_resource_bundle_path()
        if bundle_path and bundle_path.is_file():
            res = Gio.Resource.load(str(bundle_path))
            res._register()
    except Exception:
        pass

    display = Gdk.Display.get_default()
    if display:
        theme = Gtk.IconTheme.get_for_display(display)
        theme.add_resource_path("/im/zackarious/ReadAloud/icons")
        if os.path.isdir("/app/share/icons"):
            theme.add_search_path("/app/share/icons")
        try:
            from .paths import get_app_dir
            icons_dir = get_app_dir() / "data" / "icons"
            if icons_dir.is_dir():
                theme.add_search_path(str(icons_dir))
        except Exception:
            pass
    _resources_initialized = True


def _setup_kwin_keep_above():
    """Configures KWin (KDE Plasma) compositor to keep the listener bubble above all other windows."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        if not bus:
            return
        names_var = bus.call_sync(
            'org.freedesktop.DBus',
            '/org/freedesktop/DBus',
            'org.freedesktop.DBus',
            'ListNames',
            None,
            None,
            Gio.DBusCallFlags.NONE,
            500,
            None
        )
        if not names_var:
            return
        names = names_var.unpack()[0]
        if 'org.kde.KWin' not in names:
            return

        plugin_name = 'readaloud_bubble_keepabove'

        # Check if already loaded in KWin
        try:
            is_loaded_res = bus.call_sync(
                'org.kde.KWin',
                '/Scripting',
                'org.kde.kwin.Scripting',
                'isScriptLoaded',
                GLib.Variant('(s)', (plugin_name,)),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None
            )
            if is_loaded_res and is_loaded_res.unpack()[0]:
                return
        except Exception:
            pass

        script_code = """
function keepBubbleAbove() {
    var windows = workspace.windowList();
    for (var i = 0; i < windows.length; ++i) {
        var w = windows[i];
        if (w && w.caption && w.caption.indexOf('ReadAloud Quick Listener') !== -1) {
            if (!w.keepAbove) {
                w.keepAbove = true;
            }
            w.skipTaskbar = true;
            w.skipPager = true;
        }
    }
}
keepBubbleAbove();
workspace.windowAdded.connect(function(w) {
    keepBubbleAbove();
});
workspace.windowActivated.connect(function(w) {
    keepBubbleAbove();
});
"""
        import os
        script_path = '/tmp/kwin_readaloud_keepabove.js'
        with open(script_path, 'w') as f:
            f.write(script_code)

        # Unload any stale instance if present
        try:
            bus.call_sync(
                'org.kde.KWin',
                '/Scripting',
                'org.kde.kwin.Scripting',
                'unloadScript',
                GLib.Variant('(s)', (plugin_name,)),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None
            )
        except Exception:
            pass

        # Load script into KWin (returns integer script ID)
        params = GLib.Variant('(ss)', (script_path, plugin_name))
        res = bus.call_sync(
            'org.kde.KWin',
            '/Scripting',
            'org.kde.kwin.Scripting',
            'loadScript',
            params,
            None,
            Gio.DBusCallFlags.NONE,
            1000,
            None
        )
        if res:
            script_id = res.unpack()[0]
            # Execute the script on its dedicated DBus object path
            bus.call_sync(
                'org.kde.KWin',
                f'/Scripting/Script{script_id}',
                'org.kde.kwin.Script',
                'run',
                None,
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None
            )
    except Exception:
        pass


def _setup_x11_keep_above(surface):
    """Configures X11/XWayland surface to keep above and act as utility/dock window."""
    try:
        from gi.repository import GdkX11
        if isinstance(surface, GdkX11.X11Surface):
            import ctypes
            from ctypes import c_void_p, c_ulong, c_int, Structure, byref

            x11 = ctypes.CDLL('libX11.so.6')
            xdisplay = surface.get_display().get_xdisplay()
            xid = surface.get_xid()
            root = surface.get_display().get_xrootwindow()

            XA_ATOM = 4
            _NET_WM_STATE = x11.XInternAtom(xdisplay, b"_NET_WM_STATE", False)
            _NET_WM_STATE_ABOVE = x11.XInternAtom(xdisplay, b"_NET_WM_STATE_ABOVE", False)
            _NET_WM_WINDOW_TYPE = x11.XInternAtom(xdisplay, b"_NET_WM_WINDOW_TYPE", False)
            _NET_WM_WINDOW_TYPE_UTILITY = x11.XInternAtom(xdisplay, b"_NET_WM_WINDOW_TYPE_UTILITY", False)

            atoms_type = (c_ulong * 1)(_NET_WM_WINDOW_TYPE_UTILITY)
            x11.XChangeProperty(xdisplay, xid, _NET_WM_WINDOW_TYPE, XA_ATOM, 32, 0, atoms_type, 1)

            atoms_state = (c_ulong * 1)(_NET_WM_STATE_ABOVE)
            x11.XChangeProperty(xdisplay, xid, _NET_WM_STATE, XA_ATOM, 32, 0, atoms_state, 1)

            class XClientMessageEvent(Structure):
                _fields_ = [
                    ('type', c_int),
                    ('serial', c_ulong),
                    ('send_event', c_int),
                    ('display', c_void_p),
                    ('window', c_ulong),
                    ('message_type', c_ulong),
                    ('format', c_int),
                    ('data', c_ulong * 5)
                ]

            event = XClientMessageEvent()
            event.type = 33  # ClientMessage
            event.send_event = 1
            event.display = xdisplay
            event.window = xid
            event.message_type = _NET_WM_STATE
            event.format = 32
            event.data[0] = 1  # _NET_WM_STATE_ADD
            event.data[1] = _NET_WM_STATE_ABOVE
            event.data[2] = 0
            event.data[3] = 1
            event.data[4] = 0

            mask = (1 << 20) | (1 << 19)
            x11.XSendEvent(xdisplay, root, False, mask, byref(event))
            x11.XFlush(xdisplay)
    except Exception:
        pass


COLLAPSE_DELAY_MS = 1500  # 1.5 second delay before collapsing controls to prevent aggressive flickering


class ListenerBubbleWindow(Gtk.Window):
    """Floating desktop listener bubble window.
    
    Floats separately in the foreground on top of other windows. Clicking
    the bubble fetches the active highlighted selection from any application
    via the primary clipboard (or standard clipboard fallback), creates a
    new tab in the main ReadAloud window, and begins audio playback.
    """

    def __init__(self, application=None, main_window=None, **kwargs):
        super().__init__(
            application=application,
            title=_("ReadAloud Quick Listener"),
            decorated=False,
            resizable=False,
            **kwargs
        )
        self.main_window = main_window
        if main_window:
            main_window.bubble = self
        self._current_playback_state = "idle"
        self.is_expanded = False
        self._collapse_timer_id = None
        self.add_css_class("listener-bubble-window")
        _ensure_bubble_resources()

        # Non-focusable to ensure it never steals keyboard focus from external apps
        self.set_focusable(False)
        self.set_can_focus(False)
        self.set_icon_name("im.zackarious.ReadAloud")

        self.set_default_size(216, 216)
        self.set_size_request(216, 216)

        # Bubble visual container (vertical box for 3 rows: Top Export, Middle row, Bottom Stop)
        self.bubble_box = PlusBubbleBox(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            homogeneous=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.bubble_box.set_size_request(216, 216)
        self.bubble_box.add_css_class("listener-bubble-box")

        # 1. Top sub-button: Export Audio (copy of export audio CD icon)
        self.export_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.export_box.set_size_request(54, 54)
        self.export_box.add_css_class("listener-bubble-sub-button")
        self.export_box.set_cursor_from_name("pointer")

        self.export_icon = Gtk.Image()
        self.export_icon.set_pixel_size(32)
        self.export_icon.set_halign(Gtk.Align.CENTER)
        self.export_icon.set_valign(Gtk.Align.CENTER)
        self.export_icon.set_hexpand(True)
        self.export_icon.set_vexpand(True)
        self.export_icon.add_css_class("listener-bubble-icon")
        self.export_icon.add_css_class("listener-bubble-sub-icon")
        self._apply_export_icon()
        self.export_box.append(self.export_icon)
        self.export_box.set_visible(False)
        self.bubble_box.append(self.export_box)

        # 2. Middle row: Rewind (left), Center (Pause/Play), Forward (right)
        self.middle_box = MiddleRowBox(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0,
            homogeneous=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.middle_box.set_size_request(216, 72)

        # Left sub-button: Rewind 15 seconds (yellow icon)
        self.rewind_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.rewind_box.set_size_request(54, 54)
        self.rewind_box.add_css_class("listener-bubble-sub-button")
        self.rewind_box.set_cursor_from_name("pointer")

        self.rewind_icon = Gtk.Image()
        self.rewind_icon.set_pixel_size(32)
        self.rewind_icon.set_halign(Gtk.Align.CENTER)
        self.rewind_icon.set_valign(Gtk.Align.CENTER)
        self.rewind_icon.set_hexpand(True)
        self.rewind_icon.set_vexpand(True)
        self.rewind_icon.add_css_class("listener-bubble-icon")
        self.rewind_icon.add_css_class("listener-bubble-sub-icon")
        self._apply_rewind_icon()
        self.rewind_box.append(self.rewind_icon)
        self.rewind_box.set_visible(False)
        self.middle_box.append(self.rewind_box)

        # Center sub-button: Speaker / Pause / Play (yellow icon)
        self.center_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.center_box.set_size_request(54, 54)
        self.center_box.add_css_class("listener-bubble-sub-button")
        self.center_box.set_cursor_from_name("pointer")

        self.icon_image = Gtk.Image()
        self.icon_image.set_pixel_size(45)
        self.icon_image.set_halign(Gtk.Align.CENTER)
        self.icon_image.set_valign(Gtk.Align.CENTER)
        self.icon_image.set_hexpand(True)
        self.icon_image.set_vexpand(True)
        self.icon_image.add_css_class("listener-bubble-icon")
        self._apply_speaker_icon()
        self.center_box.append(self.icon_image)
        self.middle_box.append(self.center_box)

        # Right sub-button: Fast forward 15 seconds (yellow icon)
        self.forward_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.forward_box.set_size_request(54, 54)
        self.forward_box.add_css_class("listener-bubble-sub-button")
        self.forward_box.set_cursor_from_name("pointer")

        self.forward_icon = Gtk.Image()
        self.forward_icon.set_pixel_size(32)
        self.forward_icon.set_halign(Gtk.Align.CENTER)
        self.forward_icon.set_valign(Gtk.Align.CENTER)
        self.forward_icon.set_hexpand(True)
        self.forward_icon.set_vexpand(True)
        self.forward_icon.add_css_class("listener-bubble-icon")
        self.forward_icon.add_css_class("listener-bubble-sub-icon")
        self._apply_forward_icon()
        self.forward_box.append(self.forward_icon)
        self.forward_box.set_visible(False)
        self.middle_box.append(self.forward_box)

        self.bubble_box.append(self.middle_box)

        # 3. Bottom sub-button: Stop playback (yellow square icon)
        self.stop_box = Gtk.Box(
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=True
        )
        self.stop_box.set_size_request(54, 54)
        self.stop_box.add_css_class("listener-bubble-sub-button")
        self.stop_box.set_cursor_from_name("pointer")

        self.stop_icon = Gtk.Image()
        self.stop_icon.set_pixel_size(32)
        self.stop_icon.set_halign(Gtk.Align.CENTER)
        self.stop_icon.set_valign(Gtk.Align.CENTER)
        self.stop_icon.set_hexpand(True)
        self.stop_icon.set_vexpand(True)
        self.stop_icon.add_css_class("listener-bubble-icon")
        self.stop_icon.add_css_class("listener-bubble-sub-icon")
        self._apply_stop_icon()
        self.stop_box.append(self.stop_icon)
        self.stop_box.set_visible(False)
        self.bubble_box.append(self.stop_box)

        # Link child references to custom snapshotting containers
        self.bubble_box.export_box = self.export_box
        self.bubble_box.middle_box = self.middle_box
        self.bubble_box.stop_box = self.stop_box
        self.middle_box.rewind_box = self.rewind_box
        self.middle_box.center_box = self.center_box
        self.middle_box.forward_box = self.forward_box
        self._anim_tick_id = None
        self._anim_start_time = None
        self._anim_target = 0.0

        self.set_child(self.bubble_box)
        self.set_tooltip_text(
            _("ReadAloud Quick Listener\n• Click to read highlighted text\n• Drag to move anywhere\n• Right-click for options")
        )

        # Setup drag gesture vs click
        self._drag_gesture = Gtk.GestureDrag.new()
        self._drag_gesture.set_button(0)  # Accept both left and right clicks
        self._is_dragging = False
        self._start_x = 0
        self._start_y = 0

        self._drag_gesture.connect("drag-begin", self._on_drag_begin)
        self._drag_gesture.connect("drag-update", self._on_drag_update)
        self._drag_gesture.connect("drag-end", self._on_drag_end)
        self.bubble_box.add_controller(self._drag_gesture)

        # Setup motion controller for hover expansion
        self._motion_controller = Gtk.EventControllerMotion.new()
        self._motion_controller.connect("enter", self._on_motion_enter)
        self._motion_controller.connect("motion", self._on_motion_move)
        self._motion_controller.connect("leave", self._on_motion_leave)
        self.bubble_box.add_controller(self._motion_controller)

        # Setup context menu actions and popover
        self._setup_context_menu()

        # Connect realize and map signals to configure always-on-top hints
        self.connect("realize", self._on_realize)
        self.connect("map", self._on_map)

        # Periodic foreground assurance timer
        self._keep_timer_id = GLib.timeout_add_seconds(2, self._periodic_keep_above)

    def _apply_speaker_icon(self):
        """Sets the bubble icon to the program speaker icon in yellow."""
        icon_name = "im.zackarious.ReadAloud"
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) if Gdk.Display.get_default() else None

        if theme and theme.has_icon(icon_name):
            self.icon_image.set_from_icon_name(icon_name)
        else:
            try:
                from .paths import get_app_dir
                icon_file = get_app_dir() / "data" / "icons" / "hicolor" / "scalable" / "apps" / f"{icon_name}.svg"
            except Exception:
                icon_file = Path("data/icons/hicolor/scalable/apps") / f"{icon_name}.svg"

            if icon_file.is_file():
                self.icon_image.set_from_file(str(icon_file))
            elif theme and theme.has_icon("im.zackarious.ReadAloud-symbolic"):
                self.icon_image.set_from_icon_name("im.zackarious.ReadAloud-symbolic")
            else:
                self.icon_image.set_from_icon_name("audio-volume-high-symbolic")
        self.icon_image.set_pixel_size(45)

    def _apply_pause_icon(self):
        """Sets the bubble icon to the pause playback icon in yellow."""
        self.icon_image.set_from_icon_name("media-playback-pause-symbolic")
        self.icon_image.set_pixel_size(32 if getattr(self, "is_expanded", False) else 45)

    def _apply_play_icon(self):
        """Sets the bubble icon to the resume playback icon in yellow."""
        self.icon_image.set_from_icon_name("media-playback-start-symbolic")
        self.icon_image.set_pixel_size(32 if getattr(self, "is_expanded", False) else 45)

    def _apply_rewind_icon(self):
        """Sets the rewind 15s icon in yellow with robust multi-tier fallback."""
        icon_name = "im.zackarious.ReadAloud.rewind-15-symbolic"
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) if Gdk.Display.get_default() else None

        if theme and theme.has_icon(icon_name):
            self.rewind_icon.set_from_icon_name(icon_name)
        else:
            loaded = False
            for path_cand in [
                Path(__file__).resolve().parent / "icons" / f"{icon_name}.svg",
                Path("data/icons/hicolor/scalable/actions") / f"{icon_name}.svg",
            ]:
                if path_cand.is_file():
                    self.rewind_icon.set_from_file(str(path_cand))
                    loaded = True
                    break
            if not loaded:
                try:
                    tex = Gdk.Texture.new_from_bytes(GLib.Bytes.new(_REWIND_15_SVG.encode("utf-8")))
                    self.rewind_icon.set_from_paintable(tex)
                except Exception:
                    self.rewind_icon.set_from_icon_name("media-seek-backward-symbolic")
        self.rewind_icon.set_pixel_size(32)

    def _apply_forward_icon(self):
        """Sets the fast forward 15s icon in yellow with robust multi-tier fallback."""
        icon_name = "im.zackarious.ReadAloud.forward-15-symbolic"
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) if Gdk.Display.get_default() else None

        if theme and theme.has_icon(icon_name):
            self.forward_icon.set_from_icon_name(icon_name)
        else:
            loaded = False
            for path_cand in [
                Path(__file__).resolve().parent / "icons" / f"{icon_name}.svg",
                Path("data/icons/hicolor/scalable/actions") / f"{icon_name}.svg",
            ]:
                if path_cand.is_file():
                    self.forward_icon.set_from_file(str(path_cand))
                    loaded = True
                    break
            if not loaded:
                try:
                    tex = Gdk.Texture.new_from_bytes(GLib.Bytes.new(_FORWARD_15_SVG.encode("utf-8")))
                    self.forward_icon.set_from_paintable(tex)
                except Exception:
                    self.forward_icon.set_from_icon_name("media-seek-forward-symbolic")
        self.forward_icon.set_pixel_size(32)

    def _apply_stop_icon(self):
        """Sets the stop icon in yellow with robust multi-tier fallback."""
        icon_name = "im.zackarious.ReadAloud.stop-symbolic"
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) if Gdk.Display.get_default() else None

        if theme and theme.has_icon(icon_name):
            self.stop_icon.set_from_icon_name(icon_name)
        else:
            loaded = False
            for path_cand in [
                Path(__file__).resolve().parent / "icons" / f"{icon_name}.svg",
                Path("data/icons/hicolor/scalable/actions") / f"{icon_name}.svg",
            ]:
                if path_cand.is_file():
                    self.stop_icon.set_from_file(str(path_cand))
                    loaded = True
                    break
            if not loaded:
                try:
                    tex = Gdk.Texture.new_from_bytes(GLib.Bytes.new(_STOP_SVG.encode("utf-8")))
                    self.stop_icon.set_from_paintable(tex)
                except Exception:
                    self.stop_icon.set_from_icon_name("media-playback-stop-symbolic")
        self.stop_icon.set_pixel_size(32)

    def _apply_export_icon(self):
        """Sets the export audio CD icon with robust multi-tier fallback."""
        icon_name = "im.zackarious.ReadAloud.cd"
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default()) if Gdk.Display.get_default() else None

        if theme and theme.has_icon(icon_name):
            self.export_icon.set_from_icon_name(icon_name)
        else:
            loaded = False
            for path_cand in [
                Path(__file__).resolve().parent / "icons" / f"{icon_name}.svg",
                Path("data/icons/hicolor/scalable/actions") / f"{icon_name}.svg",
            ]:
                if path_cand.is_file():
                    self.export_icon.set_from_file(str(path_cand))
                    loaded = True
                    break
            if not loaded:
                self.export_icon.set_from_icon_name("document-save-symbolic")
        self.export_icon.set_pixel_size(32)

    def update_playback_state(self, is_playing, is_paused):
        """Updates the bubble icon, state, and tooltip based on playback state."""
        if is_playing:
            new_state = "paused" if is_paused else "playing"
        else:
            new_state = "idle"

        if getattr(self, '_current_playback_state', None) == new_state:
            return

        self._current_playback_state = new_state

        if new_state == "playing":
            self._apply_pause_icon()
        elif new_state == "paused":
            self._apply_play_icon()
        else:
            self._apply_speaker_icon()
            self._collapse_controls()

        if not getattr(self, 'is_expanded', False):
            self._update_standard_tooltip()

        # Trigger visual flip transition on center icon
        if hasattr(self, 'icon_image') and self.icon_image:
            self.icon_image.add_css_class("icon-flip")
            GLib.timeout_add(150, lambda: self.icon_image.remove_css_class("icon-flip") or False)

    def _update_standard_tooltip(self):
        """Sets standard tooltip text when the bubble is in compact mode."""
        if self._current_playback_state == "playing":
            self.set_tooltip_text(
                _("ReadAloud Quick Listener\n• Click to pause playback\n• Drag to move anywhere\n• Right-click for options")
            )
        elif self._current_playback_state == "paused":
            self.set_tooltip_text(
                _("ReadAloud Quick Listener\n• Click to resume playback\n• Drag to move anywhere\n• Right-click for options")
            )
        else:
            self.set_tooltip_text(
                _("ReadAloud Quick Listener\n• Click to read highlighted text\n• Drag to move anywhere\n• Right-click for options")
            )

    def _setup_context_menu(self):
        """Creates the right-click context menu."""
        self.action_group = Gio.SimpleActionGroup()

        read_action = Gio.SimpleAction.new("read", None)
        read_action.connect("activate", lambda *_: self._on_bubble_clicked())
        self.action_group.add_action(read_action)

        rewind_action = Gio.SimpleAction.new("rewind", None)
        rewind_action.connect("activate", lambda *_: self.rewind_15s())
        self.action_group.add_action(rewind_action)

        stop_action = Gio.SimpleAction.new("stop", None)
        stop_action.connect("activate", lambda *_: self.stop_playback())
        self.action_group.add_action(stop_action)

        forward_action = Gio.SimpleAction.new("forward", None)
        forward_action.connect("activate", lambda *_: self.forward_15s())
        self.action_group.add_action(forward_action)

        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", lambda *_: self.export_audio())
        self.action_group.add_action(export_action)

        show_action = Gio.SimpleAction.new("show-main", None)
        show_action.connect("activate", lambda *_: self._show_main_window())
        self.action_group.add_action(show_action)

        hide_action = Gio.SimpleAction.new("hide", None)
        hide_action.connect("activate", lambda *_: self.set_visible(False))
        self.action_group.add_action(hide_action)

        self.insert_action_group("bubble", self.action_group)

        self._menu = Gio.Menu()
        self._update_menu_items()

        self._popover = Gtk.PopoverMenu.new_from_model(self._menu)
        self._popover.set_parent(self.bubble_box)
        self._popover.set_has_arrow(True)

    def _update_menu_items(self):
        """Updates context menu items based on playback state."""
        self._menu.remove_all()
        if self.main_window and getattr(self.main_window, 'is_playing', False) is True:
            if getattr(self.main_window, 'is_paused', False) is True:
                self._menu.append(_("Resume Playback"), "bubble.read")
            else:
                self._menu.append(_("Pause Playback"), "bubble.read")
            self._menu.append(_("Rewind 15s"), "bubble.rewind")
            self._menu.append(_("Stop Playback"), "bubble.stop")
            self._menu.append(_("Fast Forward 15s"), "bubble.forward")
            self._menu.append(_("Export Audio"), "bubble.export")
        else:
            self._menu.append(_("Read Highlighted Text"), "bubble.read")
            self._menu.append(_("Export Audio"), "bubble.export")
        self._menu.append(_("Open ReadAloud"), "bubble.show-main")
        self._menu.append(_("Hide Bubble"), "bubble.hide")

    def get_action_group(self, prefix):
        """Returns the Gio action group with the specified prefix."""
        if prefix == "bubble":
            return getattr(self, "action_group", None)
        return None

    def _show_context_menu(self):
        """Displays the right-click popover menu."""
        if hasattr(self, '_popover') and self._popover:
            self._update_menu_items()
            self._popover.popup()

    def _show_main_window(self):
        """Presents the main application window."""
        if self.main_window:
            self.main_window.present()

    def _on_realize(self, widget):
        """Configure platform-specific surface hints when the window is realized."""
        surface = self.get_surface()
        if surface:
            _setup_x11_keep_above(surface)
        _setup_kwin_keep_above()
        self._update_input_region()

    def _on_map(self, widget):
        """Ensure window remains on top when mapped to display."""
        surface = self.get_surface()
        if surface:
            _setup_x11_keep_above(surface)
        _setup_kwin_keep_above()
        self._update_input_region()

    def _update_input_region(self):
        """Updates surface input region so pointer events only register within the visible bubble or plus shape.
        
        Corner cutouts and transparent outer areas pass all clicks and gestures through
        to underlying windows.
        """
        surface = self.get_surface()
        if not surface or not hasattr(surface, "set_input_region"):
            return
        try:
            if getattr(self, "is_expanded", False):
                # Plus cross shape: vertical arm [72, 0, 72, 216] + horizontal arm [0, 72, 216, 72]
                reg = cairo.Region(cairo.RectangleInt(72, 0, 72, 216))
                reg.union(cairo.RectangleInt(0, 72, 216, 72))
                surface.set_input_region(reg)
            else:
                # Compact circle bounding box: [72, 72, 72, 72] centered at (108, 108)
                reg = cairo.Region(cairo.RectangleInt(72, 72, 72, 72))
                surface.set_input_region(reg)
        except Exception:
            pass

    def _periodic_keep_above(self):
        """Periodically ensures the bubble stays raised in the foreground when main window is not active."""
        if self.main_window and hasattr(self.main_window, 'is_playing'):
            self.update_playback_state(
                getattr(self.main_window, 'is_playing', False) is True,
                getattr(self.main_window, 'is_paused', False) is True
            )
        if self.is_visible() and not self._is_dragging:
            # If the user is actively working/typing in the main ReadAloud window,
            # do not present the bubble as calling present() resets active text selection.
            if self.main_window and hasattr(self.main_window, 'is_active') and self.main_window.is_active():
                return True
            self.present()
        return True

    def _on_drag_begin(self, gesture, start_x, start_y):
        self._is_dragging = False
        self._start_x = start_x
        self._start_y = start_y
        self.bubble_box.add_css_class("bubble-active")

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if math.hypot(offset_x, offset_y) > 8:
            if not self._is_dragging:
                self._is_dragging = True
                surface = self.get_surface()
                if surface and isinstance(surface, Gdk.Toplevel):
                    device = gesture.get_device()
                    btn = gesture.get_current_button()
                    event = gesture.get_current_event()
                    timestamp = event.get_time() if event else Gdk.CURRENT_TIME
                    try:
                        surface.begin_move(device, btn, self._start_x, self._start_y, timestamp)
                    except Exception:
                        pass

    def _on_motion_enter(self, controller, x, y):
        """Triggered when pointer enters the bubble container."""
        if hasattr(self, '_collapse_timer_id') and self._collapse_timer_id:
            GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = None

        if self._current_playback_state in ("playing", "paused"):
            if self._is_point_in_plus(x, y):
                self._expand_controls()
                self._update_hover_sub_buttons(x, y)
        else:
            if self._is_point_in_plus(x, y):
                self.bubble_box._is_compact_hovered = True
                self.bubble_box.queue_draw()

    def _on_motion_move(self, controller, x, y):
        """Triggered when pointer moves across the bubble container."""
        if hasattr(self, '_collapse_timer_id') and self._collapse_timer_id:
            GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = None

        if self._current_playback_state in ("playing", "paused") and not self.is_expanded:
            if self._is_point_in_plus(x, y):
                self._expand_controls()

        if self.is_expanded:
            if self._is_point_in_plus(x, y):
                self._update_hover_sub_buttons(x, y)
            else:
                self._clear_sub_button_hovers()
                if not getattr(self, '_collapse_timer_id', None):
                    self._collapse_timer_id = GLib.timeout_add(COLLAPSE_DELAY_MS, self._delayed_collapse)
        else:
            in_circle = self._is_point_in_plus(x, y)
            if getattr(self.bubble_box, "_is_compact_hovered", False) != in_circle:
                self.bubble_box._is_compact_hovered = in_circle
                self.bubble_box.queue_draw()

    def _on_motion_leave(self, controller):
        """Triggered when pointer leaves the bubble container."""
        self._clear_sub_button_hovers()
        if getattr(self.bubble_box, "_is_compact_hovered", False):
            self.bubble_box._is_compact_hovered = False
            self.bubble_box.queue_draw()
        if self.is_expanded and not self._is_dragging:
            if hasattr(self, '_collapse_timer_id') and self._collapse_timer_id:
                GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = GLib.timeout_add(COLLAPSE_DELAY_MS, self._delayed_collapse)

    def _delayed_collapse(self):
        """Callback to collapse controls after leave timeout."""
        self._collapse_timer_id = None
        if not self._is_dragging:
            self._collapse_controls()
        return False

    def _is_point_in_plus(self, x, y):
        """Checks whether coordinates (x, y) fall within the plus shape (excluding corner cutouts)."""
        if not getattr(self, 'is_expanded', False):
            return math.hypot(x - 108, y - 108) <= 36
        # Vertical arm: x in [72, 144], y in [0, 216]
        if 72 <= x <= 144 and 0 <= y <= 216:
            return True
        # Horizontal arm: x in [0, 216], y in [72, 144]
        if 0 <= x <= 216 and 72 <= y <= 144:
            return True
        return False

    def _get_button_at_pos(self, x, y):
        """Returns the identifier ('export', 'rewind', 'center', 'forward', 'stop') closest to (x, y)."""
        distances = {
            'export': math.hypot(x - 108, y - 36),
            'rewind': math.hypot(x - 36, y - 108),
            'center': math.hypot(x - 108, y - 108),
            'forward': math.hypot(x - 180, y - 108),
            'stop': math.hypot(x - 108, y - 180)
        }
        return min(distances, key=distances.get)

    def _update_hover_sub_buttons(self, x, y):
        """Updates hover highlights and tooltips based on pointer coordinates in 216x216 cross layout."""
        if not self.is_expanded:
            return

        self._clear_sub_button_hovers()
        target = self._get_button_at_pos(x, y)

        if target == 'export':
            self.export_box.add_css_class("hovered")
            self.set_tooltip_text(_("Export Audio (current tab or all tabs)"))
        elif target == 'rewind':
            self.rewind_box.add_css_class("hovered")
            self.set_tooltip_text(_("Rewind 15 seconds"))
        elif target == 'center':
            self.center_box.add_css_class("hovered")
            if self._current_playback_state == "playing":
                self.set_tooltip_text(_("Pause playback"))
            elif self._current_playback_state == "paused":
                self.set_tooltip_text(_("Resume playback"))
            else:
                self.set_tooltip_text(_("Read highlighted text"))
        elif target == 'forward':
            self.forward_box.add_css_class("hovered")
            self.set_tooltip_text(_("Fast forward 15 seconds"))
        elif target == 'stop':
            self.stop_box.add_css_class("hovered")
            self.set_tooltip_text(_("Stop playback"))

    def _clear_sub_button_hovers(self):
        """Removes hover CSS classes from all sub-buttons."""
        if hasattr(self, 'export_box'):
            self.export_box.remove_css_class("hovered")
        if hasattr(self, 'rewind_box'):
            self.rewind_box.remove_css_class("hovered")
        if hasattr(self, 'center_box'):
            self.center_box.remove_css_class("hovered")
        if hasattr(self, 'stop_box'):
            self.stop_box.remove_css_class("hovered")
        if hasattr(self, 'forward_box'):
            self.forward_box.remove_css_class("hovered")

    def _start_expansion_animation(self):
        """Starts the smooth 260ms outward animation forming the plus shape from center."""
        self._anim_target = 1.0
        self._anim_duration_ms = 260.0
        self._anim_start_time = None
        self._anim_start_progress = getattr(self.bubble_box, "progress", 0.0)
        if getattr(self, "_anim_tick_id", None) is None:
            self._anim_tick_id = self.bubble_box.add_tick_callback(self._on_anim_tick)

    def _start_collapse_animation(self):
        """Starts the smooth 200ms inward animation retracting the plus arms back into center."""
        self._anim_target = 0.0
        self._anim_duration_ms = 200.0
        self._anim_start_time = None
        self._anim_start_progress = getattr(self.bubble_box, "progress", 1.0)
        if getattr(self, "_anim_tick_id", None) is None:
            self._anim_tick_id = self.bubble_box.add_tick_callback(self._on_anim_tick)

    def _on_anim_tick(self, widget, frame_clock):
        """Frame clock tick callback driving the outward/inward plus shape progression."""
        now_ms = frame_clock.get_frame_time() / 1000.0
        if self._anim_start_time is None:
            self._anim_start_time = now_ms

        elapsed = now_ms - self._anim_start_time
        frac = min(1.0, elapsed / max(1.0, self._anim_duration_ms))

        new_progress = self._anim_start_progress + (self._anim_target - self._anim_start_progress) * frac
        self.bubble_box.progress = new_progress
        if hasattr(self, "middle_box") and self.middle_box:
            self.middle_box.progress = new_progress
            self.middle_box.queue_draw()
        self.bubble_box.queue_draw()

        if frac >= 1.0:
            self.bubble_box.progress = self._anim_target
            if hasattr(self, "middle_box") and self.middle_box:
                self.middle_box.progress = self._anim_target
                self.middle_box.queue_draw()
            self.bubble_box.queue_draw()
            self._anim_tick_id = None
            if self._anim_target == 0.0:
                self._finish_collapse()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _expand_controls(self):
        """Stretches the Quick Listener into a 5-button plus cross to reveal export, rewind, stop, and forward."""
        if self.is_expanded:
            return
        self.is_expanded = True
        self.export_box.set_visible(True)
        self.rewind_box.set_visible(True)
        self.stop_box.set_visible(True)
        self.forward_box.set_visible(True)
        self.icon_image.set_pixel_size(32)
        self.rewind_icon.set_pixel_size(32)
        self.stop_icon.set_pixel_size(32)
        self.forward_icon.set_pixel_size(32)
        self.export_icon.set_pixel_size(32)
        self.bubble_box.add_css_class("expanded")
        self.bubble_box.set_size_request(216, 216)
        self.set_size_request(216, 216)
        self.set_default_size(216, 216)
        self._update_input_region()

        surface = self.get_surface()
        frame_clock = self.bubble_box.get_frame_clock() if hasattr(self.bubble_box, "get_frame_clock") else None
        if surface and frame_clock:
            self.bubble_box.progress = 0.0
            if hasattr(self, "middle_box") and self.middle_box:
                self.middle_box.progress = 0.0
                self.middle_box.queue_draw()
            self._start_expansion_animation()
        else:
            self.bubble_box.progress = 1.0
            if hasattr(self, "middle_box") and self.middle_box:
                self.middle_box.progress = 1.0
                self.middle_box.queue_draw()
        self.bubble_box.queue_draw()

    def _collapse_controls(self):
        """Collapses the Quick Listener back to its compact circular profile."""
        if not self.is_expanded:
            return
        self.is_expanded = False
        self._clear_sub_button_hovers()

        surface = self.get_surface()
        frame_clock = self.bubble_box.get_frame_clock() if hasattr(self.bubble_box, "get_frame_clock") else None
        if surface and frame_clock:
            self._start_collapse_animation()
        else:
            self._finish_collapse()
        self._update_standard_tooltip()

    def _finish_collapse(self):
        """Finalizes hiding child buttons and resets size after collapse animation."""
        self.bubble_box.progress = 0.0
        if hasattr(self, "middle_box") and self.middle_box:
            self.middle_box.progress = 0.0
            self.middle_box.queue_draw()
        self.export_box.set_visible(False)
        self.rewind_box.set_visible(False)
        self.stop_box.set_visible(False)
        self.forward_box.set_visible(False)
        self.icon_image.set_pixel_size(45)
        self.bubble_box.remove_css_class("expanded")
        self.bubble_box.set_size_request(216, 216)
        self.set_size_request(216, 216)
        self.set_default_size(216, 216)
        self._update_input_region()
        self.bubble_box.queue_draw()

    def export_audio(self):
        """Exports audio for current tab or prompts for all tabs via main window."""
        if hasattr(self, 'export_icon') and self.export_icon:
            self.export_icon.add_css_class("icon-bounce")
            GLib.timeout_add(150, lambda: self.export_icon.remove_css_class("icon-bounce") or False)
        if self.main_window and hasattr(self.main_window, 'save_audio_dialog'):
            self.main_window.save_audio_dialog()

    def rewind_15s(self):
        """Rewinds playback by 15 seconds with tactile bounce animation."""
        if hasattr(self, 'rewind_icon') and self.rewind_icon:
            self.rewind_icon.add_css_class("icon-bounce")
            GLib.timeout_add(150, lambda: self.rewind_icon.remove_css_class("icon-bounce") or False)
        if self.main_window and hasattr(self.main_window, 'seek_playback'):
            self.main_window.seek_playback(-15)

    def forward_15s(self):
        """Fast forwards playback by 15 seconds with tactile bounce animation."""
        if hasattr(self, 'forward_icon') and self.forward_icon:
            self.forward_icon.add_css_class("icon-bounce")
            GLib.timeout_add(150, lambda: self.forward_icon.remove_css_class("icon-bounce") or False)
        if self.main_window and hasattr(self.main_window, 'seek_playback'):
            self.main_window.seek_playback(15)

    def stop_playback(self):
        """Stops playback completely and resets the Quick Listener to the speaker app icon."""
        if hasattr(self, 'stop_icon') and self.stop_icon:
            self.stop_icon.add_css_class("icon-bounce")
            GLib.timeout_add(150, lambda: self.stop_icon.remove_css_class("icon-bounce") or False)
        if self.main_window and hasattr(self.main_window, 'stop_playback'):
            self.main_window.stop_playback()
        else:
            self.update_playback_state(is_playing=False, is_paused=False)

    def _on_drag_end(self, gesture, offset_x, offset_y):
        self.bubble_box.remove_css_class("bubble-active")
        btn = gesture.get_current_button()
        if not self._is_dragging and math.hypot(offset_x, offset_y) <= 8:
            if btn == 1:  # Left click
                if self.is_expanded:
                    if self._is_point_in_plus(self._start_x, self._start_y):
                        target = self._get_button_at_pos(self._start_x, self._start_y)
                        if target == 'export':
                            self.export_audio()
                        elif target == 'rewind':
                            self.rewind_15s()
                        elif target == 'center':
                            self._on_bubble_clicked()
                        elif target == 'forward':
                            self.forward_15s()
                        elif target == 'stop':
                            self.stop_playback()
                else:
                    if self._is_point_in_plus(self._start_x, self._start_y):
                        self._on_bubble_clicked()
            elif btn == 3:  # Right click: Context menu
                self._show_context_menu()
        self._is_dragging = False

    def _on_bubble_clicked(self):
        """Handles left-click on the listener bubble.
        
        - If audio is playing and not paused: pauses playback.
        - If audio is paused: resumes playback where it left off.
        - If idle: reads highlighted selection and begins playback.
        """
        if self.main_window and getattr(self.main_window, 'is_playing', False) is True:
            self.main_window.toggle_pause()
        else:
            self.read_highlighted_text()

    def read_highlighted_text(self):
        """Reads highlighted selection from primary clipboard (or regular clipboard fallback)."""
        display = Gdk.Display.get_default()
        if not display:
            self._flash_feedback("empty")
            return

        primary = display.get_primary_clipboard()

        def on_regular_done(clip, res):
            try:
                text = clip.read_text_finish(res)
            except Exception:
                text = None
            self._handle_retrieved_text(text)

        def on_primary_done(clip, res):
            try:
                text = clip.read_text_finish(res)
            except Exception:
                text = None

            if text and text.strip():
                self._handle_retrieved_text(text)
            else:
                # Fallback to standard clipboard
                clipboard = display.get_clipboard()
                if clipboard:
                    clipboard.read_text_async(None, on_regular_done)
                else:
                    self._handle_retrieved_text(None)

        if primary:
            primary.read_text_async(None, on_primary_done)
        else:
            clipboard = display.get_clipboard()
            if clipboard:
                clipboard.read_text_async(None, on_regular_done)
            else:
                self._handle_retrieved_text(None)

    def _handle_retrieved_text(self, text):
        """Processes the retrieved text, creates a new tab in the main window, and begins playback."""
        if not text or not text.strip():
            self._flash_feedback("empty")
            return

        clean_text = text.strip()
        first_line = clean_text.splitlines()[0].strip()
        if len(first_line) > 500:
            first_line = first_line[:500] + "…"
        tab_title = f"{_('Quick Read')}: {first_line}" if first_line else _("Quick Read")

        self._flash_feedback("success")

        if self.main_window:
            self.main_window.load_text_and_play(clean_text, title=tab_title)

    def _flash_feedback(self, status):
        """Provides brief visual feedback on the bubble icon."""
        css_class = "bubble-success" if status == "success" else "bubble-empty"
        self.bubble_box.add_css_class(css_class)
        GLib.timeout_add(800, lambda: self.bubble_box.remove_css_class(css_class) or False)

    def close(self):
        """Cleanly dismisses the bubble window and stops keep-above timers."""
        if hasattr(self, '_anim_tick_id') and self._anim_tick_id:
            try:
                self.bubble_box.remove_tick_callback(self._anim_tick_id)
            except Exception:
                pass
            self._anim_tick_id = None
        if hasattr(self, '_keep_timer_id') and self._keep_timer_id:
            GLib.source_remove(self._keep_timer_id)
            self._keep_timer_id = None
        if hasattr(self, '_collapse_timer_id') and self._collapse_timer_id:
            GLib.source_remove(self._collapse_timer_id)
            self._collapse_timer_id = None
        super().close()
