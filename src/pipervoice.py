import os
from pathlib import Path
from gi.repository import GLib
from .paths import get_model_search_paths

class VoiceManager:
    def __init__(self, parent=None):
        self.parent = parent

    def get_installed_voices(self, lang_code):
        """Safely returns installed voices for a language without shell commands."""
        voices = []
        search_paths = get_model_search_paths()

        for base_path in search_paths:
            if base_path.is_dir():
                for filepath in base_path.iterdir():
                    # Check if the file starts with the language code (e.g., 'en' or 'en_GB')
                    if filepath.name.startswith(lang_code) and filepath.name.endswith(".onnx"):
                        base_name = filepath.name.replace(".onnx", "")
                        parts = base_name.split("-")
                        if len(parts) >= 3:
                            voices.append({
                                'id': base_name,
                                'name': parts[1].capitalize(),
                                'path': str(filepath)
                            })
        return voices
