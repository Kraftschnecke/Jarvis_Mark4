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


# Nur Pakete stubben, die auf diesem Rechner fehlen (z.B. pycaw unter Linux)
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

# "project" immer stubben: das echte Modul verbindet sich beim Import
# mit der Datenbank (init_project_db).
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
from router import chat_route
from jarvis import Jarvis
from workspace import Workspace
from conversation import Conversation
from project_state import ProjectState

CONFIRMATION = {
    "relevant": True,
    "section": "Decisions",
    "content": "Wir nutzen PostgreSQL",
    "requires_confirmation": True,
    "status": "confirmation_required"
}


def make_jarvis(analysis=CONFIRMATION, project_id=7):
    saved = []
    llm_calls = []

    j = object.__new__(Jarvis)
    j.client = None
    j.workspace = Workspace()
    j.project_state.set_project((project_id, "Testprojekt"))
    j.pending_project_confirmation = None
    j.task_registry = None
    j.settings_manager = types.SimpleNamespace(get=lambda c, k, d=None: True)
    j.memory = types.SimpleNamespace(
        process=lambda client, message: None,
        get_context=lambda: ""
    )
    # Wie das echte Jarvis: ohne aktives Projekt gibt es keine Analyse
    j.process_project_context = lambda message: (
        analysis if j.project_state.active_project is not None else None
    )

    jarvis_module.ask_jarvis = lambda *a, **k: (
        llm_calls.append("ask_jarvis") or "Klingt gut."
    )
    jarvis_module.get_project_context = lambda project_id: ""
    jarvis_module.save_message = lambda *a, **k: None
    jarvis_module.route_message = lambda *a, **k: (
        llm_calls.append("route_message") or chat_route()
    )

    def fake_add(project_id, section, content):
        saved.append((project_id, section, content))
        return True
    jarvis_module.add_to_project_section = fake_add

    return j, saved, llm_calls


# 1) Rueckfrage erscheint in der Antwort, Nachricht wird normal beantwortet
j, saved, llm = make_jarvis()
result = j.process_message("Ich glaube wir nehmen PostgreSQL")
assert result["status"] == "response"
assert "Klingt gut." in result["content"]
assert "Decisions" in result["content"] and "Wir nutzen PostgreSQL" in result["content"]
assert "(ja / nein)" in result["content"]
assert j.pending_project_confirmation == {
    "project_id": 7, "section": "Decisions", "content": "Wir nutzen PostgreSQL"
}
# Rueckfrage steht nicht im Chatverlauf
assert j.conversation.get_messages()[-1] == {"role": "assistant", "content": "Klingt gut."}

# 2) "Ja!" speichert, ohne ein LLM zu fragen
llm.clear()
result = j.process_message("Ja!")
assert saved == [(7, "Decisions", "Wir nutzen PostgreSQL")]
assert "gespeichert" in result["content"]
assert j.pending_project_confirmation is None
assert llm == []

# 3) "nein" speichert nichts
j, saved, llm = make_jarvis()
j.process_message("Ich glaube wir nehmen PostgreSQL")
result = j.process_message("  Nein. ")
assert saved == [] and "nicht gespeichert" in result["content"]
assert j.pending_project_confirmation is None

# 4) Andere Nachricht: Rueckfrage verfaellt, spaetes "ja" speichert nichts
j, saved, llm = make_jarvis()
j.process_message("Ich glaube wir nehmen PostgreSQL")
j.process_project_context = lambda message: None
j.process_message("Wie spaet ist es?")
assert j.pending_project_confirmation is None
j.process_message("ja")
assert saved == []

# 5) Projektwechsel zwischen Frage und Antwort: nichts wird gespeichert
j, saved, llm = make_jarvis()
j.process_message("Ich glaube wir nehmen PostgreSQL")
j.project_state.set_project((99, "Anderes Projekt"))
j.process_message("ja")
assert saved == []

# 6) Projekt geschlossen: nichts wird gespeichert, kein Absturz
j, saved, llm = make_jarvis()
j.process_message("Ich glaube wir nehmen PostgreSQL")
j.project_state.clear()
j.process_message("ja")
assert saved == []

# 7) Speichern schlaegt fehl (z.B. steht schon drin): ehrliche Antwort
j, saved, llm = make_jarvis()
j.process_message("Ich glaube wir nehmen PostgreSQL")
jarvis_module.add_to_project_section = lambda *a: False
result = j.process_message("ja")
assert "nicht speichern" in result["content"]

# 8) Ohne Bestaetigungsbedarf bleibt die Antwort unveraendert
j, saved, llm = make_jarvis(analysis={"relevant": True, "status": "saved"})
result = j.process_message("Datenbank ist fertig")
assert result["content"] == "Klingt gut."
assert j.pending_project_confirmation is None

print("ALL TESTS PASSED")
