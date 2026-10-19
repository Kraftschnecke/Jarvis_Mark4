import os
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


stub_if_missing("openai", OpenAI=object)
stub_if_missing("psycopg")
stub_if_missing("psutil")
stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
stub_if_missing("requests")
try:
    import pycaw.pycaw  # noqa: F401
except ImportError:
    sys.modules["pycaw"] = types.ModuleType("pycaw")
    inner = types.ModuleType("pycaw.pycaw")
    inner.AudioUtilities = None
    inner.IAudioEndpointVolume = None
    sys.modules["pycaw.pycaw"] = inner

project_stub = types.ModuleType("project")
for name in (
    "search_projects", "get_conversations", "create_conversation",
    "load_conversation_messages", "save_message", "get_conversation",
    "rename_conversation", "create_project", "reset_conversation",
    "delete_conversation", "get_projects", "rename_project", "delete_project"
):
    setattr(project_stub, name, lambda *a, **k: None)
sys.modules["project"] = project_stub

# Muss VOR dem ersten Import von config gesetzt sein
os.environ["JARVIS_TIMING"] = "On"

import ai_log
import config
from jarvis import Jarvis

lines = []
ai_log.emit = lines.append


class FakeUsage:
    input_tokens = 120
    output_tokens = 15


class FakeResponse:
    usage = FakeUsage()
    output_text = "ok"


class FakeResponses:
    def __init__(self):
        self.calls = []
        self.fail = False

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if self.fail:
            raise RuntimeError("Netzwerk weg")

        return FakeResponse() if kwargs.get("model") != "ohne-usage" else types.SimpleNamespace()


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()
        self.other = "unveraendert"


# Funktionen, die wie command.detect_command / brain.ask_jarvis aufrufen
def detect_command(client):
    return client.responses.create(model="m", input="x")


def ask_jarvis(client, model="m"):
    return client.responses.create(model=model, input="y")


# 1) Ohne wrap() ist alles aus: nichts wird gemessen, nichts ausgegeben
ai_log.start_message("Hallo")
ai_log.record_call("egal", 1.0)
ai_log.finish_message()
assert lines == []

# 2) Einstellung aus der .env: "On" schaltet ein
assert config.TIMING_ENABLED is True

# 3) wrap(): Aufrufe werden gezaehlt, benannt und mit Tokens gemeldet
fake = FakeClient()
client = ai_log.wrap(fake)
assert client.other == "unveraendert"  # alles andere geht durch

ai_log.start_message("Wie spaet ist es?")
first = detect_command(client)
second = ask_jarvis(client, model="ohne-usage")
ai_log.finish_message()

assert isinstance(first, FakeResponse)  # Ergebnis kommt unveraendert zurueck
assert len(fake.responses.calls) == 2
text = "\n".join(lines)
assert '"Wie spaet ist es?"' in text and "2 KI-Aufrufe" in text, text
assert "detect_command" in text and "ask_jarvis" in text, text
assert "Tokens ein/aus: 120/15" in text, text
assert "Tokens ein/aus: ?/?" in text, text  # Antwort ohne usage
assert "FEHLER" not in text

# 4) Fehlgeschlagener Aufruf: wird gemeldet und der Fehler bleibt erhalten
lines.clear()
fake.responses.fail = True
ai_log.start_message("kaputt")
try:
    detect_command(client)
    raise AssertionError("Fehler wurde verschluckt")
except RuntimeError as error:
    assert "Netzwerk weg" in str(error)
ai_log.finish_message()
assert "1 KI-Aufrufe" in lines[0] and "FEHLER" in "\n".join(lines), lines
fake.responses.fail = False

# 5) Aufrufe ausserhalb einer Nachricht stuerzen nicht ab und zaehlen nirgends
lines.clear()
detect_command(client)
ai_log.finish_message()
assert lines == []

# 6) Lange Nachrichten werden gekuerzt, Zeilenumbrueche zu Leerzeichen
lines.clear()
ai_log.start_message("a\nb " + "x" * 200)
ai_log.finish_message()
assert lines[0].startswith('[TIMING] "a b ') and "..." in lines[0] and "0 KI-Aufrufe" in lines[0], lines

# 7) Jarvis.process_message klammert jede Nachricht, auch wenn sie scheitert
lines.clear()
j = object.__new__(Jarvis)
j.pending_project_confirmation = None


def boom(message):
    detect_command(client)
    raise ValueError("kaputt")


j._process_message = boom
result = j.process_message("Test")
assert result["status"] == "response" and "ValueError" in result["content"]
assert len(lines) >= 1 and "1 KI-Aufrufe" in lines[0], lines
assert len([l for l in lines if "Test" in l and "KI-Aufrufe" in l]) == 1  # genau eine Zusammenfassung

j._process_message = lambda message: {"status": "response", "content": "ok"}
lines.clear()
j.process_message("Zweite")
assert len(lines) == 1 and "0 KI-Aufrufe" in lines[0] and "Zweite" in lines[0], lines

print("ALL TESTS PASSED")
