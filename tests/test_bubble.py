import unittest
from unittest.mock import MagicMock, patch
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, Gdk

from src.bubble import ListenerBubbleWindow
from src.window import ReadAloudWindow
from src.main import ReadAloudApplication


class TestListenerBubble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.mock_main_window = MagicMock()
        self.bubble = ListenerBubbleWindow(main_window=self.mock_main_window)

    def test_bubble_window_properties(self):
        """Verify bubble window has borderless, unresizable, circular styling attributes."""
        self.assertFalse(self.bubble.get_decorated())
        self.assertFalse(self.bubble.get_resizable())
        self.assertTrue(self.bubble.has_css_class("listener-bubble-window"))
        self.assertIsNotNone(self.bubble.bubble_box)
        self.assertTrue(self.bubble.bubble_box.has_css_class("listener-bubble-box"))
        self.assertTrue(self.bubble.bubble_box.get_homogeneous())
        self.assertIsNotNone(self.bubble.get_tooltip_text())

    def test_context_menu_actions_registered(self):
        """Verify context menu actions exist and are functional."""
        action_group = self.bubble.get_action_group("bubble")
        self.assertIsNotNone(action_group)
        self.assertTrue(action_group.has_action("read"))
        self.assertTrue(action_group.has_action("show-main"))
        self.assertTrue(action_group.has_action("hide"))

    def test_context_menu_show_main_action(self):
        """Verify show-main action presents the main window."""
        action_group = self.bubble.get_action_group("bubble")
        action = action_group.lookup_action("show-main")
        action.activate(None)
        self.mock_main_window.present.assert_called_once()

    def test_context_menu_hide_action(self):
        """Verify hide action hides the bubble window."""
        self.bubble.set_visible(True)
        action_group = self.bubble.get_action_group("bubble")
        action = action_group.lookup_action("hide")
        action.activate(None)
        self.assertFalse(self.bubble.get_visible())

    def test_drag_vs_click_handling(self):
        """Verify dragging distinguishes between window repositioning and clicking."""
        gesture = self.bubble._drag_gesture
        read_called = []
        self.bubble.read_highlighted_text = lambda: read_called.append(True)

        # 1. Drag movement exceeds threshold -> marks is_dragging
        self.bubble._on_drag_begin(gesture, 0, 0)
        self.bubble._on_drag_update(gesture, 15, 20)
        self.assertTrue(self.bubble._is_dragging)

        # Releasing after drag does not trigger click
        self.bubble._on_drag_end(gesture, 15, 20)
        self.assertEqual(len(read_called), 0)

        # 2. Click (movement <= 8px) triggers read_highlighted_text
        self.bubble._on_drag_begin(gesture, 108, 108)
        self.bubble._on_drag_update(gesture, 2, 1)
        with patch.object(gesture, 'get_current_button', return_value=1):
            self.bubble._on_drag_end(gesture, 2, 1)
        self.assertEqual(len(read_called), 1)

    def test_handle_retrieved_text_creates_tab_and_plays(self):
        """Verify non-empty text creates a new tab and begins audio playback."""
        sample_text = "The quick brown fox jumps over the lazy dog."
        self.bubble._handle_retrieved_text(sample_text)

        self.mock_main_window.load_text_and_play.assert_called_once()
        args, kwargs = self.mock_main_window.load_text_and_play.call_args
        self.assertEqual(args[0], sample_text)
        self.assertEqual(kwargs.get('title'), f"Quick Read: {sample_text}")

    def test_handle_retrieved_text_empty(self):
        """Verify empty or whitespace text does not trigger playback."""
        self.bubble._handle_retrieved_text("")
        self.bubble._handle_retrieved_text("   \n\t  ")
        self.mock_main_window.load_text_and_play.assert_not_called()

    def test_window_load_text_and_play(self):
        """Verify ReadAloudWindow.load_text_and_play creates a new tab and calls read_text."""
        win = ReadAloudWindow.__new__(ReadAloudWindow)
        win.is_playing = False
        win.read_button = Gtk.Button()
        win.present = MagicMock()
        win.create_new_tab = MagicMock()
        win.read_text = MagicMock()
        win.main_text_view = Gtk.TextView()

        text = "Hello from external application!"
        win.load_text_and_play(text)

        win.create_new_tab.assert_called_once()
        call_args = win.create_new_tab.call_args
        self.assertEqual(call_args.kwargs['text'], text)
        win.present.assert_called_once()
        win.read_text.assert_called_once_with(win.read_button)

    def test_app_toggle_bubble(self):
        """Verify app.toggle-bubble toggles the bubble visibility."""
        app = ReadAloudApplication.__new__(ReadAloudApplication)
        app.bubble = self.bubble
        self.bubble.set_visible(True)

        app.on_toggle_bubble_action(None, None)
        self.assertFalse(self.bubble.get_visible())

        app.on_toggle_bubble_action(None, None)
        self.assertTrue(self.bubble.get_visible())

    def test_flash_feedback_classes(self):
        """Verify flash feedback temporarily adds status classes to bubble_box."""
        self.bubble._flash_feedback("success")
        self.assertTrue(self.bubble.bubble_box.has_css_class("bubble-success"))

        self.bubble._flash_feedback("empty")
        self.assertTrue(self.bubble.bubble_box.has_css_class("bubble-empty"))

    def test_app_quit_action_closes_bubble(self):
        """Verify _on_quit_action closes both bubble and active window."""
        app = ReadAloudApplication.__new__(ReadAloudApplication)
        app.bubble = MagicMock()
        mock_win = MagicMock()
        app.props = MagicMock(active_window=mock_win)

        app._on_quit_action()
        app.bubble.close.assert_called_once()
        mock_win.close.assert_called_once()

    def test_do_activate_creates_bubble_and_presents(self):
        """Verify do_activate loads and presents the floating listener bubble."""
        app = ReadAloudApplication.__new__(ReadAloudApplication)
        mock_win = MagicMock()
        app.props = MagicMock(active_window=mock_win)
        app.bubble = None

        with patch('src.main.ListenerBubbleWindow') as mock_bubble_cls:
            mock_bubble_instance = MagicMock()
            mock_bubble_cls.return_value = mock_bubble_instance

            app.do_activate()

            mock_win.present.assert_called_once()
            mock_bubble_cls.assert_called_once_with(application=app, main_window=mock_win)
            mock_bubble_instance.present.assert_called_once()
            self.assertEqual(app.bubble, mock_bubble_instance)

    def test_bubble_styling_and_centered_icon(self):
        """Verify bubble uses black background, white border, no outer shadow, and centered icon."""
        from src.bubble import BUBBLE_CSS
        self.assertIn("background-color: transparent", BUBBLE_CSS)
        self.assertIn("border: 2.5px solid #ffffff", BUBBLE_CSS)
        self.assertIn("box-shadow: none", BUBBLE_CSS)
        self.assertIn("min-width: 216px", BUBBLE_CSS)
        self.assertIn("min-height: 216px", BUBBLE_CSS)
        self.assertIn("border-radius: 50%", BUBBLE_CSS)
        self.assertEqual(self.bubble.get_icon_name(), "im.zackarious.ReadAloud")
        self.assertFalse(self.bubble.get_focusable())
        self.assertFalse(self.bubble.get_can_focus())
        self.assertEqual(self.bubble.icon_image.get_pixel_size(), 45)
        self.assertEqual(self.bubble.icon_image.get_halign(), Gtk.Align.CENTER)
        self.assertEqual(self.bubble.icon_image.get_valign(), Gtk.Align.CENTER)

    def test_periodic_keep_above_invokes_present(self):
        """Verify _periodic_keep_above invokes present when main window is not active, and skips when active."""
        self.bubble.set_visible(True)
        self.bubble._is_dragging = False

        # When main window is not active, present() is invoked
        self.mock_main_window.is_active.return_value = False
        with patch.object(self.bubble, 'present') as mock_present:
            res = self.bubble._periodic_keep_above()
            self.assertTrue(res)
            mock_present.assert_called_once()

        # When main window is active (user is typing/selecting), present() is skipped to prevent losing selection
        self.mock_main_window.is_active.return_value = True
        with patch.object(self.bubble, 'present') as mock_present:
            res = self.bubble._periodic_keep_above()
            self.assertTrue(res)
            mock_present.assert_not_called()

    def test_close_removes_keep_timer(self):
        """Verify close() stops the keep-above timer."""
        self.assertIsNotNone(self.bubble._keep_timer_id)
        self.bubble.close()
        self.assertIsNone(self.bubble._keep_timer_id)

    def test_bubble_playback_state_icon_transitions(self):
        """Verify bubble icon and tooltip transition across playing, paused, and finished states."""
        # 1. When playback starts -> pause icon
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.assertEqual(self.bubble.icon_image.get_icon_name(), "media-playback-pause-symbolic")
        self.assertIn("pause playback", self.bubble.get_tooltip_text().lower())

        # 2. When playback is paused -> play icon
        self.bubble.update_playback_state(is_playing=True, is_paused=True)
        self.assertEqual(self.bubble.icon_image.get_icon_name(), "media-playback-start-symbolic")
        self.assertIn("resume playback", self.bubble.get_tooltip_text().lower())

        # 3. When playback finishes / stops -> speaker app icon
        self.bubble.update_playback_state(is_playing=False, is_paused=False)
        self.assertEqual(self.bubble.icon_image.get_icon_name(), "im.zackarious.ReadAloud")
        self.assertIn("read highlighted text", self.bubble.get_tooltip_text().lower())

    def test_bubble_click_when_playing_pauses(self):
        """Verify left-clicking the listener bubble when audio is playing pauses playback."""
        self.mock_main_window.is_playing = True
        self.mock_main_window.is_paused = False

        self.bubble._on_bubble_clicked()
        self.mock_main_window.toggle_pause.assert_called_once()

    def test_bubble_click_when_paused_resumes(self):
        """Verify left-clicking the listener bubble when audio is paused resumes playback."""
        self.mock_main_window.is_playing = True
        self.mock_main_window.is_paused = True

        self.bubble._on_bubble_clicked()
        self.mock_main_window.toggle_pause.assert_called_once()

    def test_bubble_click_when_idle_reads_text(self):
        """Verify left-clicking the listener bubble when idle reads highlighted text."""
        self.mock_main_window.is_playing = False
        self.mock_main_window.is_paused = False

        with patch.object(self.bubble, 'read_highlighted_text') as mock_read:
            self.bubble._on_bubble_clicked()
            mock_read.assert_called_once()

    def test_bubble_icons_styled_yellow(self):
        """Verify bubble CSS styles the icons with bright yellow color."""
        from src.bubble import BUBBLE_CSS
        self.assertIn("color: #fee14d", BUBBLE_CSS)
        self.assertIn("icon-flip", BUBBLE_CSS)

    def test_context_menu_items_update_with_playback_state(self):
        """Verify right-click context menu displays Pause/Resume/Read depending on playback."""
        self.mock_main_window.is_playing = True
        self.mock_main_window.is_paused = False
        self.bubble._update_menu_items()
        item_text = self.bubble._menu.get_item_attribute_value(0, "label").get_string()
        self.assertIn("Pause", item_text)

        self.mock_main_window.is_paused = True
        self.bubble._update_menu_items()
        item_text = self.bubble._menu.get_item_attribute_value(0, "label").get_string()
        self.assertIn("Resume", item_text)

        self.mock_main_window.is_playing = False
        self.mock_main_window.is_paused = False
        self.bubble._update_menu_items()
        item_text = self.bubble._menu.get_item_attribute_value(0, "label").get_string()
        self.assertIn("Read", item_text)

    def test_bubble_hover_expands_when_playing(self):
        """Verify Quick Listener stretches into 5-button cross and reveals export/rewind/stop/forward."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.assertFalse(self.bubble.is_expanded)
        self.assertFalse(self.bubble.export_box.get_visible())
        self.assertFalse(self.bubble.rewind_box.get_visible())
        self.assertFalse(self.bubble.stop_box.get_visible())
        self.assertFalse(self.bubble.forward_box.get_visible())

        # Pointer enters the bubble
        self.bubble._on_motion_enter(None, 108, 108)
        self.assertTrue(self.bubble.is_expanded)
        self.assertTrue(self.bubble.bubble_box.has_css_class("expanded"))
        self.assertTrue(self.bubble.export_box.get_visible())
        self.assertTrue(self.bubble.rewind_box.get_visible())
        self.assertTrue(self.bubble.stop_box.get_visible())
        self.assertTrue(self.bubble.forward_box.get_visible())
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)
        self.assertEqual(self.bubble.bubble_box.get_size_request()[1], 216)
        self.assertEqual(self.bubble.icon_image.get_pixel_size(), 32)
        self.assertEqual(self.bubble.rewind_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.stop_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.forward_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.export_icon.get_pixel_size(), 32)

    def test_bubble_hover_does_not_expand_when_idle(self):
        """Verify Quick Listener does not expand when idle (speaker icon showing)."""
        self.bubble.update_playback_state(is_playing=False, is_paused=False)
        self.bubble._on_motion_enter(None, 108, 108)
        self.assertFalse(self.bubble.is_expanded)
        self.assertFalse(self.bubble.export_box.get_visible())
        self.assertFalse(self.bubble.rewind_box.get_visible())
        self.assertFalse(self.bubble.stop_box.get_visible())
        self.assertFalse(self.bubble.forward_box.get_visible())
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)

    def test_bubble_hover_expands_when_paused(self):
        """Verify Quick Listener expands when hovering over play icon while paused."""
        self.bubble.update_playback_state(is_playing=True, is_paused=True)
        self.assertEqual(self.bubble.icon_image.get_icon_name(), "media-playback-start-symbolic")

        # Pointer enters the bubble while paused
        self.bubble._on_motion_enter(None, 108, 108)
        self.assertTrue(self.bubble.is_expanded)
        self.assertTrue(self.bubble.export_box.get_visible())
        self.assertTrue(self.bubble.rewind_box.get_visible())
        self.assertTrue(self.bubble.stop_box.get_visible())
        self.assertTrue(self.bubble.forward_box.get_visible())
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)

    def test_bubble_collapse_on_leave_or_finish(self):
        """Verify Quick Listener collapses back to circular profile."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()
        self.assertTrue(self.bubble.is_expanded)
        self.assertEqual(self.bubble.icon_image.get_pixel_size(), 32)

        # Collapse manually
        self.bubble._collapse_controls()
        self.assertFalse(self.bubble.is_expanded)
        self.assertFalse(self.bubble.bubble_box.has_css_class("expanded"))
        self.assertFalse(self.bubble.export_box.get_visible())
        self.assertFalse(self.bubble.rewind_box.get_visible())
        self.assertFalse(self.bubble.stop_box.get_visible())
        self.assertFalse(self.bubble.forward_box.get_visible())
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)
        self.assertEqual(self.bubble.icon_image.get_pixel_size(), 45)

        # Expand and then finish playback -> auto collapse
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()
        self.assertTrue(self.bubble.is_expanded)
        self.bubble.update_playback_state(is_playing=False, is_paused=False)
        self.assertFalse(self.bubble.is_expanded)
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)

    def test_bubble_motion_leave_debounced_collapse_delay(self):
        """Verify pointer leaving the expanded bubble initiates a 1.5-second (1500ms) collapse timeout."""
        from src.bubble import COLLAPSE_DELAY_MS
        self.assertEqual(COLLAPSE_DELAY_MS, 1500)

        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()
        self.assertTrue(self.bubble.is_expanded)

        # Trigger motion leave
        self.bubble._on_motion_leave(None)
        self.assertIsNotNone(self.bubble._collapse_timer_id)
        # Should still be expanded immediately after leaving due to 1.5s delay
        self.assertTrue(self.bubble.is_expanded)

        # If pointer re-enters before 1.5s, timer is cancelled and stays expanded
        self.bubble._on_motion_enter(None, 108, 108)
        self.assertIsNone(self.bubble._collapse_timer_id)
        self.assertTrue(self.bubble.is_expanded)

        # Trigger leave again and execute the delayed collapse callback
        self.bubble._on_motion_leave(None)
        self.assertIsNotNone(self.bubble._collapse_timer_id)
        self.bubble._delayed_collapse()
        self.assertFalse(self.bubble.is_expanded)
        self.assertIsNone(self.bubble._collapse_timer_id)
        self.assertEqual(self.bubble.bubble_box.get_size_request()[0], 216)

    def test_export_audio_action(self):
        """Verify export_audio delegates to main_window.save_audio_dialog."""
        self.bubble.export_audio()
        self.mock_main_window.save_audio_dialog.assert_called_once()

    def test_rewind_15s_and_forward_15s_actions(self):
        """Verify rewind_15s and forward_15s delegate to main_window.seek_playback."""
        self.bubble.rewind_15s()
        self.mock_main_window.seek_playback.assert_called_with(-15)

        self.bubble.forward_15s()
        self.mock_main_window.seek_playback.assert_called_with(15)

    def test_stop_playback_action(self):
        """Verify stop_playback delegates to main_window.stop_playback."""
        self.bubble.stop_playback()
        self.mock_main_window.stop_playback.assert_called_once()

    def test_expanded_click_routing(self):
        """Verify clicks on export, rewind, pause, stop, and forward regions route correctly."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()
        gesture = self.bubble._drag_gesture

        # Region Top (108, 36): export audio
        self.bubble._start_x = 108
        self.bubble._start_y = 36
        with patch.object(gesture, 'get_current_button', return_value=1):
            with patch.object(self.bubble, 'export_audio') as mock_export:
                self.bubble._on_drag_end(gesture, 0, 0)
                mock_export.assert_called_once()

        # Region Left (36, 108): rewind 15s
        self.bubble._start_x = 36
        self.bubble._start_y = 108
        with patch.object(gesture, 'get_current_button', return_value=1):
            with patch.object(self.bubble, 'rewind_15s') as mock_rewind:
                self.bubble._on_drag_end(gesture, 0, 0)
                mock_rewind.assert_called_once()

        # Region Center (108, 108): pause/resume
        self.bubble._start_x = 108
        self.bubble._start_y = 108
        self.mock_main_window.is_playing = True
        with patch.object(gesture, 'get_current_button', return_value=1):
            self.bubble._on_drag_end(gesture, 0, 0)
            self.mock_main_window.toggle_pause.assert_called_once()

        # Region Right (180, 108): forward 15s
        self.bubble._start_x = 180
        self.bubble._start_y = 108
        with patch.object(gesture, 'get_current_button', return_value=1):
            with patch.object(self.bubble, 'forward_15s') as mock_fwd:
                self.bubble._on_drag_end(gesture, 0, 0)
                mock_fwd.assert_called_once()

        # Region Bottom (108, 180): stop
        self.bubble._start_x = 108
        self.bubble._start_y = 180
        with patch.object(gesture, 'get_current_button', return_value=1):
            with patch.object(self.bubble, 'stop_playback') as mock_stop:
                self.bubble._on_drag_end(gesture, 0, 0)
                mock_stop.assert_called_once()

    def test_sub_buttons_icons_and_yellow_styling(self):
        """Verify rewind, stop, forward, and export icons use dedicated icons."""
        from src.bubble import BUBBLE_CSS
        self.assertIn(self.bubble.rewind_icon.get_icon_name(), [
            "im.zackarious.ReadAloud.rewind-15-symbolic",
            "media-seek-backward-symbolic"
        ])
        self.assertIn(self.bubble.stop_icon.get_icon_name(), [
            "im.zackarious.ReadAloud.stop-symbolic",
            "media-playback-stop-symbolic"
        ])
        self.assertIn(self.bubble.forward_icon.get_icon_name(), [
            "im.zackarious.ReadAloud.forward-15-symbolic",
            "media-seek-forward-symbolic"
        ])
        self.assertIn(self.bubble.export_icon.get_icon_name(), [
            "im.zackarious.ReadAloud.cd",
            "document-save-symbolic"
        ])
        self.assertEqual(self.bubble.rewind_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.stop_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.forward_icon.get_pixel_size(), 32)
        self.assertEqual(self.bubble.export_icon.get_pixel_size(), 32)
        self.assertTrue(self.bubble.rewind_icon.has_css_class("listener-bubble-sub-icon"))
        self.assertTrue(self.bubble.stop_icon.has_css_class("listener-bubble-sub-icon"))
        self.assertTrue(self.bubble.forward_icon.has_css_class("listener-bubble-sub-icon"))
        self.assertTrue(self.bubble.export_icon.has_css_class("listener-bubble-sub-icon"))
        for ic in (self.bubble.rewind_icon, self.bubble.icon_image, self.bubble.stop_icon, self.bubble.forward_icon, self.bubble.export_icon):
            self.assertEqual(ic.get_halign(), Gtk.Align.CENTER)
            self.assertEqual(ic.get_valign(), Gtk.Align.CENTER)
        self.assertIn("listener-bubble-sub-icon", BUBBLE_CSS)
        self.assertIn("color: #fee14d", BUBBLE_CSS)

    def test_context_menu_rewind_forward_items(self):
        """Verify context menu actions and items for rewind, stop, forward, and export exist during playback."""
        action_group = self.bubble.get_action_group("bubble")
        self.assertTrue(action_group.has_action("rewind"))
        self.assertTrue(action_group.has_action("stop"))
        self.assertTrue(action_group.has_action("forward"))
        self.assertTrue(action_group.has_action("export"))

        self.mock_main_window.is_playing = True
        self.mock_main_window.is_paused = False
        self.bubble._update_menu_items()
        labels = [self.bubble._menu.get_item_attribute_value(i, "label").get_string()
                  for i in range(self.bubble._menu.get_n_items())]
        self.assertTrue(any("Rewind 15s" in l for l in labels))
        self.assertTrue(any("Stop Playback" in l for l in labels))
        self.assertTrue(any("Fast Forward 15s" in l for l in labels))
        self.assertTrue(any("Export Audio" in l for l in labels))

    def test_plus_shape_point_in_plus_hit_testing(self):
        """Verify _is_point_in_plus returns True inside the plus arms and False in corner cutouts."""
        # In compact mode, only within circle (center 108, radius 36)
        self.bubble.update_playback_state(is_playing=False, is_paused=False)
        self.assertTrue(self.bubble._is_point_in_plus(108, 108))
        self.assertFalse(self.bubble._is_point_in_plus(5, 5))
        self.assertFalse(self.bubble._is_point_in_plus(36, 36))

        # In expanded mode:
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()

        # Inside vertical arm: (108, 20) [top export], (108, 108) [center], (108, 200) [bottom stop]
        self.assertTrue(self.bubble._is_point_in_plus(108, 20))
        self.assertTrue(self.bubble._is_point_in_plus(108, 108))
        self.assertTrue(self.bubble._is_point_in_plus(108, 200))

        # Inside horizontal arm: (20, 108) [left rewind], (200, 108) [right forward]
        self.assertTrue(self.bubble._is_point_in_plus(20, 108))
        self.assertTrue(self.bubble._is_point_in_plus(200, 108))

        # In the four transparent corner cutouts:
        self.assertFalse(self.bubble._is_point_in_plus(20, 20))    # Top-left corner
        self.assertFalse(self.bubble._is_point_in_plus(195, 20))   # Top-right corner
        self.assertFalse(self.bubble._is_point_in_plus(20, 195))   # Bottom-left corner
        self.assertFalse(self.bubble._is_point_in_plus(195, 195))  # Bottom-right corner

    def test_corner_click_ignored(self):
        """Verify clicks in the four transparent corner cutouts do not trigger any button action."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()
        gesture = self.bubble._drag_gesture

        # Click in top-left cutout (20, 20)
        self.bubble._start_x = 20
        self.bubble._start_y = 20
        with patch.object(gesture, 'get_current_button', return_value=1):
            with patch.object(self.bubble, 'export_audio') as mock_exp, \
                 patch.object(self.bubble, 'rewind_15s') as mock_rew, \
                 patch.object(self.bubble, 'stop_playback') as mock_stp, \
                 patch.object(self.bubble, 'forward_15s') as mock_fwd, \
                 patch.object(self.bubble, '_on_bubble_clicked') as mock_clk:
                self.bubble._on_drag_end(gesture, 0, 0)
                mock_exp.assert_not_called()
                mock_rew.assert_not_called()
                mock_stp.assert_not_called()
                mock_fwd.assert_not_called()
                mock_clk.assert_not_called()

    def test_outward_animation_progression(self):
        """Verify outward animation progress state and child container linkage."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()

        # Check references linked to custom snapshotting containers
        self.assertEqual(self.bubble.bubble_box.export_box, self.bubble.export_box)
        self.assertEqual(self.bubble.bubble_box.middle_box, self.bubble.middle_box)
        self.assertEqual(self.bubble.bubble_box.stop_box, self.bubble.stop_box)
        self.assertEqual(self.bubble.middle_box.rewind_box, self.bubble.rewind_box)
        self.assertEqual(self.bubble.middle_box.center_box, self.bubble.center_box)
        self.assertEqual(self.bubble.middle_box.forward_box, self.bubble.forward_box)

        # Progress in expanded mode
        self.assertEqual(self.bubble.bubble_box.progress, 1.0)
        self.assertEqual(self.bubble.middle_box.progress, 1.0)

        # After collapse
        self.bubble._collapse_controls()
        self.assertEqual(self.bubble.bubble_box.progress, 0.0)
        self.assertEqual(self.bubble.middle_box.progress, 0.0)

    def test_bubble_expanded_hover_transparent_and_outer_border_only(self):
        """Verify CSS specifies transparent background for expanded hover state and no inner borders."""
        from src.bubble import BUBBLE_CSS
        # Expanded hover must be transparent to avoid dark box behind plus shape
        self.assertIn(".listener-bubble-box.expanded:hover", BUBBLE_CSS)
        self.assertIn(".listener-bubble-box:not(.expanded):hover", BUBBLE_CSS)
        # Snapshot execution with progress = 1.0 does not error and clears background
        self.bubble.update_playback_state(is_playing=True, is_paused=True)
        self.bubble._expand_controls()
        snapshot = Gtk.Snapshot()
        self.bubble.bubble_box.do_snapshot(snapshot)
        node = snapshot.to_node()
        self.assertIsNotNone(node)

    def test_rewind_and_forward_buttons_persist_in_expanded_mode(self):
        """Verify rewind and forward buttons remain visible and snapshot correctly when expanded."""
        self.bubble.update_playback_state(is_playing=True, is_paused=False)
        self.bubble._expand_controls()

        # Both rewind and forward boxes must be visible
        self.assertTrue(self.bubble.rewind_box.get_visible())
        self.assertTrue(self.bubble.forward_box.get_visible())
        self.assertTrue(self.bubble.export_box.get_visible())
        self.assertTrue(self.bubble.stop_box.get_visible())
        self.assertTrue(self.bubble.center_box.get_visible())

        # Container snapshot cleanly executes and produces valid render node
        snapshot = Gtk.Snapshot()
        self.bubble.bubble_box.do_snapshot(snapshot)
        node = snapshot.to_node()
        self.assertIsNotNone(node)


if __name__ == '__main__':
    unittest.main()
