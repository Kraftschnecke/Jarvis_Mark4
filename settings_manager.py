import json
from pathlib import Path


class SettingsManager:
    """Central persistent settings store for J.A.R.V.I.S."""

    DEFAULT_SETTINGS = {
        "general": {
            "language": "English",
            "startup_behavior": "Normal startup",
            "confirmations": True,
        },
        "appearance": {
            "theme": "Dark",
            "accent_color": "J.A.R.V.I.S. Blue",
            "font_size": 13,
            "ui_scale": "100 %",
        },
        "jarvis": {
            "name": "J.A.R.V.I.S.",
            "address": "Sir",
            "personality": "Default",
        },
        "voice": {
            "input_device": "Default input",
            "output_device": "Default output",
            "voice": "Default voice",
            "speed": 100,
        },
        "memory": {
            "enabled": True,
        },
    }

    def __init__(self, file_path="settings.json"):
        self.file_path = Path(file_path)
        self.settings = self._load()

    def _load(self):
        if not self.file_path.exists():
            settings = self._copy(self.DEFAULT_SETTINGS)
            self._save(settings)
            return settings

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                settings = json.load(file)
            settings = self._merge_defaults(settings)
            self._save(settings)
            return settings
        except (json.JSONDecodeError, OSError, TypeError):
            settings = self._copy(self.DEFAULT_SETTINGS)
            self._save(settings)
            return settings

    def _save(self, settings=None):
        if settings is None:
            settings = self.settings
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(settings, file, indent=4, ensure_ascii=False)

    def get(self, category, key, default=None):
        return self.settings.get(category, {}).get(key, default)

    def set(self, category, key, value):
        self.settings.setdefault(category, {})[key] = value
        self._save()

    def get_category(self, category):
        return self.settings.get(category, {}).copy()

    def get_all(self):
        return self._copy(self.settings)

    def reset(self):
        self.settings = self._copy(self.DEFAULT_SETTINGS)
        self._save()

    def reset_category(self, category):
        if category in self.DEFAULT_SETTINGS:
            self.settings[category] = self._copy(self.DEFAULT_SETTINGS[category])
            self._save()

    @staticmethod
    def _copy(value):
        return json.loads(json.dumps(value))

    def _merge_defaults(self, settings):
        merged = self._copy(self.DEFAULT_SETTINGS)
        if not isinstance(settings, dict):
            return merged
        for category, values in settings.items():
            if category in merged and isinstance(values, dict):
                merged[category].update(values)
        return merged
