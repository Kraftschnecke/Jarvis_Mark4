import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

for name, attrs in (
    ("dotenv", {"load_dotenv": lambda *a, **k: None}),
    ("openai", {"OpenAI": object}),
    ("psycopg", {}),
    ("psutil", {}),
    ("requests", {}),
):
    try:
        __import__(name)
    except ImportError:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m

project_stub = types.ModuleType("project")
for name in (
    "search_projects", "get_conversations", "create_conversation",
    "load_conversation_messages", "save_message", "get_conversation",
    "rename_conversation", "create_project", "reset_conversation",
    "delete_conversation", "get_projects", "rename_project", "delete_project"
):
    setattr(project_stub, name, lambda *a, **k: None)
sys.modules["project"] = project_stub

import workspace as ws_module
from workspace import Workspace

created_files = []
ws_module.ensure_project_context = lambda pid, name: created_files.append((pid, name))

CONVS = [(1, "Test B", None, None), (2, "Neue Unterhaltung", None, None)]
db = {"projects": [(5, "Abnahmetest")], "convs": list(CONVS), "reset": [], "deleted": [], "renamed": []}

ws_module.search_projects = lambda n: [p for p in db["projects"] if n and n.lower() in p[1].lower()]
ws_module.get_conversations = lambda pid: list(db["convs"])
ws_module.get_conversation = lambda pid, t: next((c for c in db["convs"] if c[1].lower() == t.lower()), None)
ws_module.load_conversation_messages = lambda cid: [{"role": "user", "content": f"alt{cid}"}]
ws_module.create_conversation = lambda pid, t: (9, t, None, None)
ws_module.create_project = lambda n, d=None: 77
ws_module.reset_project_conversation = lambda cid: db["reset"].append(cid)
ws_module.delete_project_conversation = lambda cid: db["deleted"].append(cid)
ws_module.rename_conversation = lambda cid, t: db["renamed"].append((cid, t))

w = Workspace()

# Ohne Projekt
assert "No project" in w.open_conversation("x")
assert "No project" in w.create_conversation("x")
assert "No project" in w.rename_conversation("a", "b")
assert "No project" in w.delete_conversation("a")
assert "No conversation" in w.reset_conversation()
assert "No project" in w.close_project()
assert w.get_conversations() == [] and w.get_conversation("x") is None
assert "couldn't find" in w.open_project("gibtsnicht")
assert "ID: 77" in w.create_project("Neu")

# Projekt mit 2 Konversationen: Liste, nichts geladen
out = w.open_project("abnahmetest")
assert "1. Test B" in out and "2. Neue Unterhaltung" in out
assert w.project_state.active_project == (5, "Abnahmetest")
assert created_files == [(5, "Abnahmetest")]
assert w.project_state.active_conversation is None

# Konversation oeffnen laedt den Verlauf
assert "Test B" in w.open_conversation("test b")
assert w.conversation.get_messages() == [{"role": "user", "content": "alt1"}]
assert "couldn't find" in w.open_conversation("nope")

# Umbenennen aktualisiert den Zustand
assert "from Test B to Test C" in w.rename_conversation("Test B", "Test C")
assert db["renamed"] == [(1, "Test C")]
assert w.project_state.active_conversation[1] == "Test C"

# Neue Konversation leert den Verlauf
assert "Test D" in w.create_conversation("Test D")
assert w.conversation.get_messages() == []

# Zuruecksetzen / Loeschen
w.conversation.add_message("user", "x")
assert w.reset_conversation() == "Conversation reset, Sir"
assert db["reset"] == [9] and w.conversation.get_messages() == []
w.open_conversation("Neue Unterhaltung")
assert "deleted" in w.delete_conversation("Neue Unterhaltung")
assert db["deleted"] == [2] and w.project_state.active_conversation is None

# Schliessen
assert "Closing project Abnahmetest" in w.close_project()
assert w.project_state.active_project is None

# Projekt ohne Konversation legt eine an
db["convs"] = []
assert "new conversation" in w.open_project("abnahmetest")
assert w.project_state.active_conversation[1] == "Neue Unterhaltung"

# Jarvis delegiert, und close_project verwirft die offene Rueckfrage
import jarvis as jarvis_module
j = object.__new__(jarvis_module.Jarvis)
j.workspace = w
j.pending_project_confirmation = {"project_id": 5, "section": "Goal", "content": "x"}
assert j.project_state is w.project_state and j.conversation is w.conversation
assert "Closing project" in j.close_project()
assert j.pending_project_confirmation is None


# =====================================================================
# Aktionen ueber IDs (Seitenleiste)
# =====================================================================
from workspace import WorkspaceError
from fake_project_db import FakeProjectDB


def raises(function, *args):
    try:
        function(*args)
    except WorkspaceError as error:
        return str(error)
    raise AssertionError("WorkspaceError erwartet")


fdb = FakeProjectDB()
fdb.install(ws_module)
ws = Workspace()

p1 = fdb.add_project("Zebra")
p2 = fdb.add_project("alpha")
c1 = fdb.add_conversation(p1, "Gleich", [{"role": "user", "content": "eins"}])
c2 = fdb.add_conversation(p1, "Gleich", [{"role": "user", "content": "zwei"}])  # gleicher Titel!
c3 = fdb.add_conversation(p2, "Andere")

# Baum: nach Name sortiert (ohne Gross/Klein), Konversationen mit IDs
tree = ws.get_tree()
assert [p["name"] for p in tree] == ["alpha", "Zebra"]
assert [c["id"] for c in tree[1]["conversations"]] == [c2, c1]
assert ws.get_active() == {"project_id": None, "conversation_id": None}

# Oeffnen: gleicher Titel ist kein Problem, es zaehlt die ID
assert ws.select_conversation(p1, c1) == [{"role": "user", "content": "eins"}]
assert ws.get_active() == {"project_id": p1, "conversation_id": c1}
assert ws.conversation.get_messages()[0]["content"] == "eins"
assert (p1, "Zebra") in fdb.files
assert ws.select_conversation(p1, c2)[0]["content"] == "zwei"

# Falsche Kombination Projekt/Konversation oder unbekannte IDs
assert "Konversation" in raises(ws.select_conversation, p2, c1)
assert "Projekt" in raises(ws.select_conversation, 999, c1)
assert ws.get_active()["conversation_id"] == c2  # Zustand unveraendert

# Projekt anklicken: wird aktiv, ohne Konversation; schon aktiv = keine Aenderung
assert ws.select_project(p2) is True
assert ws.get_active() == {"project_id": p2, "conversation_id": None}
assert ws.conversation.get_messages() == []
ws.select_conversation(p1, c2)
assert ws.select_project(p1) is False          # schon aktiv
assert ws.get_active()["conversation_id"] == c2  # Konversation bleibt offen
assert ws.select_project(p2) is True
assert ws.get_active() == {"project_id": p2, "conversation_id": None}
assert ws.conversation.get_messages() == []    # Chat des alten Projekts weg
assert "Projekt" in raises(ws.select_project, 999)
ws.select_conversation(p1, c2)

# Neues Projekt: wird sofort aktiv; Name pruefen
new_pid = ws.add_project("Neu")
assert isinstance(new_pid, int)
assert ws.get_active() == {"project_id": new_pid, "conversation_id": None}
assert (new_pid, "Neu") in fdb.files
ws.select_conversation(p1, c2)
assert "schon" in raises(ws.add_project, "neu")
assert "leer" in raises(ws.add_project, "   ")
assert "leer" in raises(ws.add_project, None)
assert "lang" in raises(ws.add_project, "x" * 101)

# Neue Konversation: braucht ein Projekt, ist danach aktiv und leer
other = Workspace()
assert "zuerst" in raises(other.add_conversation, "x")
# ... oder ein angegebenes Projekt (wird dabei aktiv)
cid_in_new = other.add_conversation("Erste", new_pid)
assert other.get_active() == {"project_id": new_pid, "conversation_id": cid_in_new}
assert fdb.conversations[cid_in_new] == (new_pid, "Erste")
# ungueltiger Titel aendert das aktive Projekt nicht
assert "leer" in raises(other.add_conversation, " ", p1)
assert other.get_active()["project_id"] == new_pid
new_id = ws.add_conversation("  Frisch  ")
assert ws.get_active() == {"project_id": p1, "conversation_id": new_id}
assert ws.conversation.get_messages() == []
assert fdb.conversations[new_id] == (p1, "Frisch")

# Umbenennen der aktiven Konversation aktualisiert den Zustand
ws.rename_conversation_by_id(p1, new_id, "Umbenannt")
assert ws.project_state.active_conversation[1] == "Umbenannt"
assert fdb.conversations[new_id][1] == "Umbenannt"
assert "Konversation" in raises(ws.rename_conversation_by_id, p1, 999, "x")
assert "leer" in raises(ws.rename_conversation_by_id, p1, new_id, "")

# Zuruecksetzen: nur der Chat der aktiven Konversation wird geleert
ws.select_conversation(p1, c1)
ws.reset_conversation_by_id(p1, c2)
assert fdb.messages[c2] == [] and ws.conversation.get_messages() != []
ws.reset_conversation_by_id(p1, c1)
assert fdb.messages[c1] == [] and ws.conversation.get_messages() == []

# Loeschen der aktiven Konversation: Projekt bleibt, Konversation nicht
ws.delete_conversation_by_id(p1, c1)
assert c1 not in fdb.conversations
assert ws.get_active() == {"project_id": p1, "conversation_id": None}
ws.select_conversation(p1, c2)
ws.delete_conversation_by_id(p2, c3)  # fremde Konversation: Zustand bleibt
assert ws.get_active()["conversation_id"] == c2

# Projekt umbenennen / loeschen
ws.rename_project_by_id(p1, "Zebra 2")
assert ws.project_state.active_project[1] == "Zebra 2" and fdb.projects[p1] == "Zebra 2"
assert "schon" in raises(ws.rename_project_by_id, p1, "ALPHA")
ws.rename_project_by_id(p1, "zebra 2")  # nur Schreibweise aendern ist erlaubt
ws.delete_project_by_id(p2)             # nicht das aktive
assert ws.get_active()["project_id"] == p1
ws.delete_project_by_id(p1)             # das aktive
assert ws.get_active() == {"project_id": None, "conversation_id": None}
assert ws.conversation.get_messages() == []
assert "Projekt" in raises(ws.delete_project_by_id, p1)

# Jarvis: offene Rueckfrage verfaellt beim Wechseln und beim Projekt-Loeschen
pa = fdb.add_project("PA")
ca = fdb.add_conversation(pa, "K")
jj = object.__new__(jarvis_module.Jarvis)
jj.workspace = Workspace()
pending = {"project_id": pa, "section": "Goal", "content": "x"}
jj.pending_project_confirmation = dict(pending)
jj.select_conversation(pa, ca)
assert jj.pending_project_confirmation is None
jj.pending_project_confirmation = dict(pending)
jj.delete_project_by_id(pa)
assert jj.pending_project_confirmation is None

print("ALL TESTS PASSED")
