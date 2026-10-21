import json
from pathlib import Path


class SettingsManager:
    """Central persistent settings store for J.A.R.V.I.S."""

    # Nur Einstellungen, die wirklich etwas bewirken (Entscheidung Step 3.4).
    # Alles andere in einer alten settings.json wird beim Laden verworfen.
    DEFAULT_SETTINGS = {
        "appearance": {
            "theme": "Dark",
            "accent_color": "J.A.R.V.I.S. Blue",
            "font_size": 13,
        },
        "jarvis": {
            "address": "Sir",
        },
        "memory": {
            "enabled": True,
        },
        # Sprache (Step 6): beides standardmaessig aus, wird erst durch dich aktiv
        "voice": {
            "output": False,
            "engine": "OpenAI",
            "voice": "Onyx (male)",
            "speed": "Normal",
            "input": False,
            "input_language": "German",
            "wake_word": False,
        },
        # Seitenleiste rechts (Etappe C): jedes der drei Felder einzeln waehlbar, "Off" blendet es aus
        "widgets": {
            "top": "Clock",
            "middle": "Notes",
            "bottom": "Off",
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

    # Erlaubte Werte, wo nur bestimmte gelten (gleiche Liste wie in server.py)
    CHOICES = {
        ("voice", "speed"): ("Slow", "Normal", "Fast"),
        ("voice", "engine"): ("OpenAI", "Browser"),
        ("voice", "voice"): (
            "Onyx (male)", "Echo (male)", "Ash (male)",
            "Nova (female)", "Shimmer (female)", "Coral (female)",
        ),
        ("voice", "input_language"): ("German", "English"),
        ("widgets", "top"): ("Off", "Clock", "Date", "Calendar"),
        ("widgets", "middle"): ("Off", "Notes", "Goals"),
        ("widgets", "bottom"): ("Off", "Edmonton Oilers", "Adler Mannheim"),
    }

    def _fits(self, category, key, value):
        """Alte Dateien koennen gleiche Namen mit anderer Bedeutung haben
        (Mark 3 hatte voice.speed als Zahl): so ein Wert wird verworfen."""
        default = self.DEFAULT_SETTINGS[category][key]
        if type(value) is not type(default):
            return False
        choices = self.CHOICES.get((category, key))
        return choices is None or value in choices

    def _merge_defaults(self, settings):
        merged = self._copy(self.DEFAULT_SETTINGS)
        if not isinstance(settings, dict):
            return merged
        for category, values in settings.items():
            if category in merged and isinstance(values, dict):
                # Nur Schluessel uebernehmen, die es noch gibt
                for key, value in values.items():
                    if key in merged[category] and self._fits(category, key, value):
                        merged[category][key] = value
        return merged
