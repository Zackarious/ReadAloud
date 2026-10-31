# tests/test_paths.py
import unittest
import sys
from pathlib import Path
from src.paths import (
    is_frozen,
    get_app_dir,
    get_executable_dir,
    get_user_data_dir,
    get_model_search_paths,
    get_resource_bundle_path,
)

class TestPaths(unittest.TestCase):
    def test_is_frozen_in_normal_python(self):
        self.assertFalse(is_frozen())

    def test_get_app_dir_returns_valid_path(self):
        app_dir = get_app_dir()
        self.assertIsInstance(app_dir, Path)
        self.assertTrue(app_dir.is_dir())

    def test_get_executable_dir_returns_valid_path(self):
        exe_dir = get_executable_dir()
        self.assertIsInstance(exe_dir, Path)
        self.assertTrue(exe_dir.is_dir())

    def test_get_user_data_dir(self):
        user_dir = get_user_data_dir()
        self.assertIsInstance(user_dir, Path)
        self.assertTrue(len(str(user_dir)) > 0)

    def test_get_model_search_paths(self):
        paths = get_model_search_paths()
        self.assertIsInstance(paths, list)
        self.assertTrue(len(paths) > 0)
        # Verify repository models directory is in search paths
        repo_models = Path(__file__).resolve().parent.parent / "models"
        self.assertIn(repo_models.resolve(), paths)

    def test_windows_mock_paths(self):
        """Simulate Windows frozen bundle environment."""
        orig_frozen = getattr(sys, "frozen", False)
        orig_platform = sys.platform
        orig_executable = sys.executable

        try:
            sys.frozen = True
            sys.platform = "win32"
            sys.executable = r"C:\Program Files\ReadAloud\ReadAloud.exe"

            exe_dir = get_executable_dir()
            self.assertEqual(str(exe_dir), r"C:\Program Files\ReadAloud")

            search_paths = [str(p) for p in get_model_search_paths()]
            self.assertTrue(any("ReadAloud" in p and "models" in p for p in search_paths))
        finally:
            if hasattr(sys, "frozen") and not orig_frozen:
                del sys.frozen
            sys.platform = orig_platform
            sys.executable = orig_executable

if __name__ == "__main__":
    unittest.main()
