import os
import sys
import tempfile
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

# Echtes "project" nie importieren (verbindet sich mit der DB)
project_stub = types.ModuleType("project")
for name in (
    "search_projects", "get_conversations", "create_conversation",
    "load_conversation_messages", "save_message", "get_conversation",
    "rename_conversation", "create_project", "reset_conversation",
    "delete_conversation", "get_projects", "rename_project", "delete_project"
):
    setattr(project_stub, name, lambda *a, **k: None)
sys.modules["project"] = project_stub

import jarvis as jarvis_module
import workspace as workspace_module
from jarvis import Jarvis
from workspace import Workspace
from conversation import Conversation
from project_state import ProjectState
from project_context import get_project_file, add_to_project_section

# Alles in einem Wegwerf-Ordner, "projects/" liegt relativ zum Arbeitsverzeichnis
os.chdir(tempfile.mkdtemp())


def make_jarvis():
    j = object.__new__(Jarvis)
    j.workspace = Workspace()
    j.pending_project_confirmation = None
    return j


workspace_module.search_projects = lambda name: [(42, "Step9 Test")]
workspace_module.get_conversations = lambda project_id: []
workspace_module.create_conversation = lambda project_id, title: (1, title, None, None)

# 1) Datei fehlt -> wird beim Oeffnen angelegt, Speichern funktioniert danach
assert not get_project_file(42).exists()
j = make_jarvis()
j.open_project("Step9")
assert get_project_file(42).exists()
assert get_project_file(42).read_text().startswith("# Step9 Test")
assert add_to_project_section(42, "Decisions", "Backend in Python") is True
assert "Backend in Python" in get_project_file(42).read_text()

# 2) Datei existiert -> bleibt unveraendert
before = get_project_file(42).read_text()
make_jarvis().open_project("Step9")
assert get_project_file(42).read_text() == before

print("ALL TESTS PASSED")
