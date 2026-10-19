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

import io
import contextlib

import jarvis as jarvis_module
from router import chat_route
from jarvis import Jarvis
from workspace import Workspace
from conversation import Conversation
from project_state import ProjectState


class FakeAPIError(Exception):
    pass


state = {"detect": None, "ask": None}


def make_jarvis():
    j = object.__new__(Jarvis)
    j.client = None
    j.workspace = Workspace()
    j.pending_project_confirmation = {"project_id": 1, "section": "Goal", "content": "x"}
    j.task_registry = None
    j.settings_manager = types.SimpleNamespace(get=lambda c, k, d=None: False)
    j.memory = types.SimpleNamespace(process=lambda *a: None, get_context=lambda: "")
    j.process_project_context = lambda message: None

    def detect(client, message, task_registry=None):
        if state["detect"] is not None:
            raise state["detect"]
        route = chat_route()
        if message == "exit":
            route["kind"] = "COMMAND"
            route["command"]["intent"] = "EXIT"
        return route

    def ask(client, conversation, memory, project_context=None):
        if state["ask"] is not None:
            raise state["ask"]
        return "alles gut"

    jarvis_module.route_message = detect
    jarvis_module.ask_jarvis = ask
    jarvis_module.save_message = lambda *a, **k: None
    return j


def quiet(function, *args):
    """Fuehrt aus, ohne den absichtlichen Traceback in die Testausgabe zu drucken."""
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        return function(*args), buffer.getvalue()


# 1) Fehler beim Erkennen des Befehls (z.B. Netzwerk weg): kein Absturz
j = make_jarvis()
state["detect"] = FakeAPIError("Connection error.")
result, stderr = quiet(j.process_message, "Hallo")
assert result["status"] == "response"
assert "Fehler" in result["content"] and "FakeAPIError" in result["content"]
assert "Connection error." in result["content"]
assert "Traceback" in stderr                  # Details bleiben in der Konsole
assert j.pending_project_confirmation is None  # keine Rueckfrage bleibt haengen

# 2) Danach funktioniert alles wieder
state["detect"] = None
result, _ = quiet(j.process_message, "Hallo nochmal")
assert result == {"status": "response", "content": "alles gut"}

# 3) Fehler erst bei der eigentlichen Antwort
state["ask"] = FakeAPIError("Rate limit")
result, _ = quiet(j.process_message, "Noch eine Frage")
assert result["status"] == "response" and "Rate limit" in result["content"]
state["ask"] = None
result, _ = quiet(j.process_message, "Und jetzt?")
assert result["content"] == "alles gut"

# 4) Sehr lange Fehlertexte werden gekuerzt
state["detect"] = FakeAPIError("x" * 5000)
result, _ = quiet(j.process_message, "Hallo")
assert len(result["content"]) < 400
state["detect"] = None

# 5) Beenden bleibt Beenden
result, _ = quiet(j.process_message, "exit")
assert result["status"] == "exit"

# 6) Strg+C wird NICHT verschluckt
state["detect"] = KeyboardInterrupt()
try:
    quiet(j.process_message, "Hallo")
    raise AssertionError("KeyboardInterrupt haette durchkommen muessen")
except KeyboardInterrupt:
    pass

print("ALL TESTS PASSED")
