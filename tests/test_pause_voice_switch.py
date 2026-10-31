import unittest
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib

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

class TestPauseVoiceSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def test_offset_calculation(self):
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window._current_highlight_index = 2

        class MockReader:
            def __init__(self):
                self.selected_voice = "Alan"
                self.lang_code = "en"
                self.pitch = 1.0
                self.speed = 1.0
                self.original_text = "The quick brown fox jumps"
                self.start_char_offset = 0
                self.word_timings = [
                    {'start_time': 0.0, 'end_time': 0.3, 'start_char': 0, 'end_char': 3, 'word': 'The'},
                    {'start_time': 0.3, 'end_time': 0.6, 'start_char': 4, 'end_char': 9, 'word': 'quick'},
                    {'start_time': 0.6, 'end_time': 1.0, 'start_char': 10, 'end_char': 15, 'word': 'brown'},
                    {'start_time': 1.0, 'end_time': 1.4, 'start_char': 16, 'end_char': 19, 'word': 'fox'},
                    {'start_time': 1.4, 'end_time': 1.9, 'start_char': 20, 'end_char': 25, 'word': 'jumps'},
                ]

            def get_playback_position(self):
                return 0.7

            def pause_audio(self):
                return True

            def resume_audio(self):
                return True

            def stop_audio(self):
                pass

        window.reader = MockReader()

        # Test _get_current_playback_char_offset
        offset = window._get_current_playback_char_offset()
        # Word at index 2 or position 0.7 is 'brown' (start_char: 10)
        self.assertEqual(offset, 10)

    def test_voice_changed_detection(self):
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = True
        window.lang_code = "en"

        class MockReader:
            selected_voice = "Alan"
            lang_code = "en"
            pitch = 1.0
            speed = 1.0
            def resume_audio(self):
                return True

        window.reader = MockReader()

        window._get_selected_voice_name = lambda: "Cori"
        window.pitch_chooser = type('Chooser', (), {'get_value': lambda self: 1.0})()
        window.speed_chooser = type('Chooser', (), {'get_value': lambda self: 1.0})()

        resumed_with_new = []
        window._resume_with_new_settings = lambda v, l, p, s: resumed_with_new.append((v, l, p, s))

        window.toggle_pause()

        self.assertEqual(len(resumed_with_new), 1)
        self.assertEqual(resumed_with_new[0][0], "Cori")

    def test_unchanged_voice_resumes_directly(self):
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = True
        window.lang_code = "en"

        resumed = []
        class MockReader:
            selected_voice = "Alan"
            lang_code = "en"
            pitch = 1.0
            speed = 1.0
            def resume_audio(self):
                resumed.append(True)
                return True

        window.reader = MockReader()

        window._get_selected_voice_name = lambda: "Alan"
        window.pitch_chooser = type('Chooser', (), {'get_value': lambda self: 1.0})()
        window.speed_chooser = type('Chooser', (), {'get_value': lambda self: 1.0})()
        window.pause_button = type('Button', (), {
            'set_icon_name': lambda self, name: None,
            'set_tooltip_text': lambda self, text: None
        })()

        resumed_with_new = []
        window._resume_with_new_settings = lambda v, l, p, s: resumed_with_new.append((v, l, p, s))

        window.toggle_pause()

        self.assertEqual(len(resumed_with_new), 0)
        self.assertEqual(len(resumed), 1)
        self.assertFalse(window.is_paused)

    def test_resume_with_new_settings_execution(self):
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = True
        window._highlight_timeout_id = None
        window._current_highlight_index = 2

        # Create real GtkTextView and Buffer
        text_view = Gtk.TextView()
        buffer = text_view.get_buffer()
        sample_text = "The quick brown fox jumps over the lazy dog."
        buffer.set_text(sample_text)
        window.main_text_view = text_view

        stopped_calls = []
        class MockReader:
            selected_voice = "Alan"
            lang_code = "en"
            pitch = 1.0
            speed = 1.0
            original_text = sample_text
            start_char_offset = 0
            word_timings = [
                {'start_time': 0.0, 'end_time': 0.3, 'start_char': 0, 'end_char': 3, 'word': 'The'},
                {'start_time': 0.3, 'end_time': 0.6, 'start_char': 4, 'end_char': 9, 'word': 'quick'},
                {'start_time': 0.6, 'end_time': 1.0, 'start_char': 10, 'end_char': 15, 'word': 'brown'},
                {'start_time': 1.0, 'end_time': 1.4, 'start_char': 16, 'end_char': 19, 'word': 'fox'},
            ]
            def get_playback_position(self):
                return 0.8
            def stop_audio(self):
                stopped_calls.append(True)

        window.reader = MockReader()
        window.read_button = type('Button', (), {
            'set_icon_name': lambda self, name: None,
            'set_tooltip_text': lambda self, text: None
        })()

        highlighted = []
        window._highlight_word = lambda s, e: highlighted.append((s, e))

        playback_started = []
        window.start_playback = lambda btn, txt, eng, lang, voice, pitch, spd, start_char_offset=0: playback_started.append({
            'text': txt,
            'voice': voice,
            'offset': start_char_offset
        })

        # Run _resume_with_new_settings with new voice 'Cori'
        window._resume_with_new_settings("Cori", "en", 1.0, 1.0)

        # 1. Old audio should be stopped
        self.assertEqual(len(stopped_calls), 1)

        # 2. Highlight word should be called for 'brown' (offset 10 to 15)
        self.assertEqual(len(highlighted), 1)
        self.assertEqual(highlighted[0], (10, 15))

        # 3. start_playback should be called with remaining text starting at 'brown...'
        self.assertEqual(len(playback_started), 1)
        self.assertEqual(playback_started[0]['voice'], "Cori")
        self.assertEqual(playback_started[0]['offset'], 10)
        self.assertEqual(playback_started[0]['text'], "brown fox jumps over the lazy dog.")

    def test_pause_during_synthesis_sets_is_paused(self):
        """When the user clicks Pause before the pipeline is created (during synthesis),
        pause_audio() must return True and is_paused must be set to True on the window."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = False

        class MockReader:
            """Simulates a reader mid-synthesis: no pipeline yet."""
            selected_voice = "Alan"
            lang_code = "en"
            pitch = 1.0
            speed = 1.0
            _current_pipeline = None  # Still synthesising
            _is_paused = False

            def pause_audio(self):
                # Use the real Reader logic: set _is_paused, return True even without pipeline
                self._is_paused = True
                if self._current_pipeline:
                    return True
                return True  # No pipeline yet — intent recorded

            def resume_audio(self):
                self._is_paused = False
                return False

        reader = MockReader()
        window.reader = reader

        window._get_selected_voice_name = lambda: "Alan"
        window.pitch_chooser = type('C', (), {'get_value': lambda self: 1.0})()
        window.speed_chooser = type('C', (), {'get_value': lambda self: 1.0})()
        window.pause_button = type('B', (), {
            'set_icon_name': lambda self, n: None,
            'set_tooltip_text': lambda self, t: None,
        })()
        buffer = Gtk.TextView().get_buffer()
        buffer.set_text("some text")
        window.main_text_view = Gtk.TextView()
        window.main_text_view.get_buffer().set_text("some text")
        window._highlight_timeout_id = None
        window._get_current_playback_char_offset = lambda: 0
        window._resume_with_new_settings = lambda v, l, p, s: None

        window.toggle_pause()

        # Reader intent was recorded
        self.assertTrue(reader._is_paused)
        # Window must see is_paused = True
        self.assertTrue(window.is_paused)

    def test_stop_audio_resets_flags(self):
        """stop_audio() must set _stopped=True and _is_paused=False."""
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)

        from src.reader import Reader
        r = Reader.__new__(Reader)
        r._current_pipeline = None
        r._is_paused = True
        r._stopped = False

        r.stop_audio()

        self.assertTrue(r._stopped)
        self.assertFalse(r._is_paused)

    def test_voice_change_detected_after_pause_during_synthesis(self):
        """Voice change must be detected and _resume_with_new_settings called even when
        the user clicked Pause before the pipeline was created (during synthesis)."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = True   # Was set correctly via the fixed pause_audio()
        window.lang_code = "en"

        class MockReader:
            selected_voice = "Alan"
            lang_code = "en"
            pitch = 1.0
            speed = 1.0
            _current_pipeline = None  # No pipeline: was paused during synthesis
            def resume_audio(self):
                return False

        window.reader = MockReader()
        window._get_selected_voice_name = lambda: "Cori"  # User switched voice
        window.pitch_chooser = type('C', (), {'get_value': lambda self: 1.0})()
        window.speed_chooser = type('C', (), {'get_value': lambda self: 1.0})()

        resumed_with_new = []
        window._resume_with_new_settings = lambda v, l, p, s: resumed_with_new.append((v, l, p, s))

        window.toggle_pause()

        self.assertEqual(len(resumed_with_new), 1, "Expected _resume_with_new_settings to be called")
        self.assertEqual(resumed_with_new[0][0], "Cori")

    def test_seek_playback(self):
        """Verify window.seek_playback calls reader.seek and updates highlight."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = False
        window._update_highlight = lambda: None

        class MockReader:
            def __init__(self):
                self.seek_args = []
            def seek(self, delta):
                self.seek_args.append(delta)
                return True

        window.reader = MockReader()

        res = window.seek_playback(15)
        self.assertTrue(res)
        self.assertEqual(window.reader.seek_args, [15])

        res = window.seek_playback(-15)
        self.assertTrue(res)
        self.assertEqual(window.reader.seek_args, [15, -15])

        # When not playing, seek is rejected
        window.is_playing = False
        self.assertFalse(window.seek_playback(15))

    def test_seek_playback_when_paused_resumes(self):
        """Verify seeking when paused scrolls to correct position and resumes playback."""
        window = ReadAloudWindow.__new__(ReadAloudWindow)
        window.is_playing = True
        window.is_paused = True
        highlight_calls = []
        window._update_highlight = lambda force=False: highlight_calls.append(force)
        resumed = []
        window.toggle_pause = lambda: resumed.append(True)

        class MockReader:
            def __init__(self):
                self.seek_args = []
            def seek(self, delta):
                self.seek_args.append(delta)
                return True

        window.reader = MockReader()

        res = window.seek_playback(-15)
        self.assertTrue(res)
        self.assertEqual(window.reader.seek_args, [-15])
        self.assertEqual(highlight_calls, [True])
        self.assertEqual(len(resumed), 1, "Expected playback to be resumed via toggle_pause when seeked while paused")

    def test_audio_player_and_reader_seek_interface(self):
        """Verify seek methods exist and safely handle uninitialized pipelines."""
        from src.audio_backend import BaseAudioPlayer, SoundDeviceAudioPlayer, GStreamerAudioPlayer
        from src.reader import Reader

        base = BaseAudioPlayer()
        self.assertFalse(base.seek(15))

        sd = SoundDeviceAudioPlayer()
        self.assertFalse(sd.seek(15))

        gst = GStreamerAudioPlayer()
        self.assertFalse(gst.seek(15))

        r = Reader.__new__(Reader)
        r._current_pipeline = None
        self.assertFalse(r.seek(15))


if __name__ == '__main__':
    unittest.main()
