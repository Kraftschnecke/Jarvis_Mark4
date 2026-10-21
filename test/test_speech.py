"""Sprachausgabe ueber OpenAI (speech.py): Stimme, Anfrage, Fehler. Ohne Netzwerk."""

import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def stub_if_missing(name, **attrs):
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module


stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)

import config
import speech
from settings_manager import SettingsManager

# Die Auswahl in den Einstellungen und die Stimmen hier sind dieselbe Liste
assert set(speech.VOICES) == set(SettingsManager.CHOICES[("voice", "voice")])
assert SettingsManager.DEFAULT_SETTINGS["voice"]["voice"] == speech.DEFAULT_VOICE
assert speech.DEFAULT_VOICE in speech.VOICES
assert sum(1 for k in speech.VOICES if "(male)" in k) == 3
assert sum(1 for k in speech.VOICES if "(female)" in k) == 3
assert all(label.endswith(("(male)", "(female)")) for label in speech.VOICES)


class FakeSpeech:
    def __init__(self, result=b"ID3-audio", error=None):
        self.calls = []
        self.result = result
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return types.SimpleNamespace(content=self.result)


def client_with(fake):
    return types.SimpleNamespace(audio=types.SimpleNamespace(speech=fake))


# 1) Normale Anfrage: richtige Stimme, Modell aus config, Anweisung, mp3
fake = FakeSpeech()
audio = speech.synthesize(client_with(fake), "Guten Tag, Sir.", "Nova (female)")
assert audio == b"ID3-audio"
call = fake.calls[0]
assert call["voice"] == "nova" and call["input"] == "Guten Tag, Sir."
assert call["model"] == config.TTS_MODEL
assert call["response_format"] == "mp3"
assert "German or English" in call["instructions"] and "butler" in call["instructions"]
assert call["timeout"] == speech.REQUEST_TIMEOUT

# Jede Stimme der Liste fuehrt zur passenden API-Stimme
for label, api_name in speech.VOICES.items():
    fake = FakeSpeech()
    speech.synthesize(client_with(fake), "x", label)
    assert fake.calls[0]["voice"] == api_name, label

# Unbekannte Stimme (kaputte Einstellung): Standardstimme statt Fehler oder Fremdwert
for bad in ("Darth (male)", "", None, 5, "onyx; DROP TABLE"):
    fake = FakeSpeech()
    speech.synthesize(client_with(fake), "x", bad)
    assert fake.calls[0]["voice"] == speech.VOICES[speech.DEFAULT_VOICE], bad

# 2) Text: bereinigt und begrenzt; leer oder kein Text ist ein Fehler
fake = FakeSpeech()
speech.synthesize(client_with(fake), "  Zeile\neins\t\x00 zwei  ", "Onyx (male)")
assert fake.calls[0]["input"] == "Zeile eins zwei", fake.calls[0]["input"]
speech.synthesize(client_with(fake), "x" * 5000, "Onyx (male)")
assert len(fake.calls[1]["input"]) == speech.MAX_TEXT_CHARS

for bad in ("", "   ", "\n\t", None, 5, ["Hallo"], {"a": 1}, b"bytes"):
    fake = FakeSpeech()
    try:
        speech.synthesize(client_with(fake), bad, "Onyx (male)")
        raise AssertionError(f"haette abgelehnt werden muessen: {bad!r}")
    except speech.SpeechError:
        pass
    assert fake.calls == [], "bei ungueltigem Text darf nichts an OpenAI gehen"

# 3) Fehler der Anfrage: kurze Meldung, keine Details (Schluessel, Adressen) nach aussen
secret = RuntimeError("401 Incorrect API key sk-geheim123 at https://api.openai.com/v1/audio/speech")
try:
    speech.synthesize(client_with(FakeSpeech(error=secret)), "Hallo", "Onyx (male)")
    raise AssertionError("Fehler muss durchgereicht werden")
except speech.SpeechError as error:
    assert "sk-geheim123" not in str(error) and "openai.com" not in str(error), str(error)
    assert "RuntimeError" in str(error)

# 4) Unbrauchbare Antworten
for bad in (b"", None, "text statt bytes", 123, b"x" * (speech.MAX_AUDIO_BYTES + 1)):
    try:
        speech.synthesize(client_with(FakeSpeech(result=bad)), "Hallo", "Onyx (male)")
        raise AssertionError(f"haette abgelehnt werden muessen: {type(bad)}")
    except speech.SpeechError:
        pass
assert speech.synthesize(client_with(FakeSpeech(result=bytearray(b"abc"))), "x", "Onyx (male)") == b"abc"

# 5) Ohne Client
try:
    speech.synthesize(None, "Hallo", "Onyx (male)")
    raise AssertionError("ohne Client muss es ein Fehler sein")
except speech.SpeechError:
    pass

print("ALL TESTS PASSED")
