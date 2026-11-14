#!/usr/bin/env python3
"""tests/test_appimage_launcher.py - Unit tests for standalone AppImage launcher logic."""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import functions from build_linux.appimage_launcher
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build_linux"))
import appimage_launcher


class TestAppImageLauncher(unittest.TestCase):
    """Test suite for AppImage launcher slice detection, assembly, and desktop integration."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_valid_assembled_nonexistent(self):
        non_existent = self.temp_path / "nonexistent.AppImage"
        self.assertFalse(appimage_launcher.is_valid_assembled(non_existent))

    def test_is_valid_assembled_small_or_non_executable(self):
        test_file = self.temp_path / "test.AppImage"
        test_file.write_bytes(b"small content")
        self.assertFalse(appimage_launcher.is_valid_assembled(test_file))

        # Even if executable, if size < 1 GB, should return False
        os.chmod(test_file, 0o755)
        self.assertFalse(appimage_launcher.is_valid_assembled(test_file))

    def test_is_valid_assembled_valid(self):
        test_file = self.temp_path / "valid.AppImage"
        test_file.touch()
        os.chmod(test_file, 0o755)
        # Mock stat size to > 1GB and S_IFREG mode
        stat_result = os.stat_result((
            stat.S_IFREG | 0o755,  # st_mode
            12345,                 # st_ino
            0,                     # st_dev
            1,                     # st_nlink
            1000,                  # st_uid
            1000,                  # st_gid
            2_000_000_000,         # st_size (> 1 GB)
            0,                     # st_atime
            0,                     # st_mtime
            0,                     # st_ctime
        ))
        with patch.object(Path, "stat", return_value=stat_result):
            self.assertTrue(appimage_launcher.is_valid_assembled(test_file))

    def test_find_slice(self):
        appimage_dir = self.temp_path / "appimage_dir"
        data_dir = self.temp_path / "data_dir"
        appimage_dir.mkdir()
        data_dir.mkdir()

        slice_name = "ReadAloud-1.8.19-linux-x86_64.AppImage.001"

        # Initially missing
        found = appimage_launcher.find_slice(slice_name, appimage_dir, data_dir)
        self.assertIsNone(found)

        # Create slice in appimage_dir with size > 1MB
        s1 = appimage_dir / slice_name
        s1.write_bytes(b"0" * 2_000_000)

        found = appimage_launcher.find_slice(slice_name, appimage_dir, data_dir)
        self.assertEqual(found, s1)

    def test_assemble_slices(self):
        slice1 = self.temp_path / "part.001"
        slice2 = self.temp_path / "part.002"
        dest = self.temp_path / "assembled.AppImage"

        slice1.write_bytes(b"HEAD_PART_DATA_")
        slice2.write_bytes(b"TAIL_PART_DATA")

        # Disable zenity during test
        with patch("shutil.which", return_value=None):
            success = appimage_launcher.assemble_slices(slice1, slice2, dest)

        self.assertTrue(success)
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_bytes(), b"HEAD_PART_DATA_TAIL_PART_DATA")
        self.assertTrue(os.access(dest, os.X_OK))

    def test_create_desktop_entry(self):
        assembled = self.temp_path / "ReadAloud.AppImage"
        with patch("pathlib.Path.home", return_value=self.temp_path):
            appimage_launcher.create_desktop_entry(assembled)
            desktop_file = self.temp_path / ".local" / "share" / "applications" / "im.zackarious.ReadAloud.desktop"
            self.assertTrue(desktop_file.exists())
            content = desktop_file.read_text(encoding="utf-8")
            self.assertIn("Name=ReadAloud", content)
            self.assertIn(str(assembled), content)
            self.assertIn("Exec=", content)

    def test_get_appimage_dir_from_env(self):
        dummy_appimage = self.temp_path / "subdir" / "ReadAloud.AppImage"
        dummy_appimage.parent.mkdir()
        dummy_appimage.touch()

        with patch.dict(os.environ, {"APPIMAGE": str(dummy_appimage)}):
            resolved_dir = appimage_launcher.get_appimage_dir()
            self.assertEqual(resolved_dir, dummy_appimage.parent)


if __name__ == "__main__":
    unittest.main()
