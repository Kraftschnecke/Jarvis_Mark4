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

import db as db_module
import memory as memory_module
from memory import Memory
import jarvis as jarvis_module
from router import chat_route
from jarvis import Jarvis
from workspace import Workspace
from conversation import Conversation
from project_state import ProjectState


# ---------- Fake-Datenbank: schreibt alle SQL-Befehle mit ----------

class FakeDB:
    def __init__(self):
        self.statements = []
        self.connections = []
        self.fail_on = None
        self.rows = []
        self.rowcount = 0


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self.rowcount = 0

    def execute(self, sql, params=None):
        if self.db.fail_on and self.db.fail_on in sql:
            raise RuntimeError("DB kaputt")
        self.db.statements.append((" ".join(sql.split()), params))
        self.rowcount = self.db.rowcount

    def fetchall(self):
        return self.db.rows

    def fetchone(self):
        return self.db.rows[0] if self.db.rows else None


class FakeConnection:
    def __init__(self, db):
        self.db = db
        self.closed = False
        self.committed = False
        self.rolled_back = False
        db.connections.append(self)

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


db = FakeDB()
db_module.psycopg = types.SimpleNamespace(
    connect=lambda url: FakeConnection(db)
)

# 1) Beim Erzeugen wird die Tabelle angelegt (frische Datenbank)
m = Memory()
assert "CREATE TABLE IF NOT EXISTS memories" in db.statements[0][0]
assert "PRIMARY KEY" in db.statements[0][0]

# 2) Upsert aktualisiert Wert UND Typ
m.save("lieblingsfarbe", "blau", "preference")
sql, params = db.statements[-1]
assert "value = EXCLUDED.value" in sql and "type = EXCLUDED.type" in sql
assert params == ("lieblingsfarbe", "blau", "preference")
assert m.memories["lieblingsfarbe"] == {"value": "blau", "type": "preference"}
# Die Verbindung geht zurueck in den Pool (bleibt offen) und ist committet
assert db.connections[-1].committed and not db.connections[-1].closed

# 3) Schlaegt die DB fehl: kein Eintrag im Cache, Verbindung zurueckgesetzt
db.fail_on = "INSERT"
db.connections[-1].committed = False     # Verbindung wird wiederverwendet
try:
    m.save("alter", "30", "fact")
    raise AssertionError("Fehler haette durchschlagen muessen")
except RuntimeError:
    pass
assert "alter" not in m.memories
assert db.connections[-1].rolled_back and not db.connections[-1].committed
assert not db.connections[-1].closed      # nach rollback wieder brauchbar
db.fail_on = None

# 4) load() fuellt den Cache, get_context() nutzt ihn
db.rows = [("name", "Moritz", "fact")]
m2 = Memory()
m2.load()
assert m2.memories["name"] == {"value": "Moritz", "type": "fact"}
assert "name = Moritz" in m2.get_context()
assert Memory().get_context() == Memory.EMPTY_CONTEXT


# ---------- Jarvis: memory.enabled ----------

def make_jarvis(enabled):
    calls = {"process": 0, "context_passed": None}

    j = object.__new__(Jarvis)
    j.client = None
    j.workspace = Workspace()
    j.pending_project_confirmation = None
    j.task_registry = None
    j.settings_manager = types.SimpleNamespace(
        get=lambda category, key, default=None: (
            enabled if (category, key) == ("memory", "enabled") else default
        )
    )

    def process(client, message):
        calls["process"] += 1

    j.memory = types.SimpleNamespace(
        process=process,
        get_context=lambda: "fact: name = Moritz"
    )
    j.process_project_context = lambda message: None

    def fake_ask(client, conversation, memory, project_context=None):
        calls["context_passed"] = memory
        return "ok"

    jarvis_module.ask_jarvis = fake_ask
    jarvis_module.save_message = lambda *a, **k: None
    jarvis_module.route_message = lambda *a, **k: chat_route()
    return j, calls


# 5) Memory an: wird gelernt und genutzt
j, calls = make_jarvis(True)
j.process_message("Ich heisse Moritz")
assert calls["process"] == 1
assert calls["context_passed"] == "fact: name = Moritz"

# 6) Memory aus: nichts gelernt, nichts genutzt (auch kein LLM-Aufruf dafuer)
j, calls = make_jarvis(False)
j.process_message("Ich heisse Moritz")
assert calls["process"] == 0
assert calls["context_passed"] == Memory.EMPTY_CONTEXT

# 7) Fehler beim Speichern verhindert die Antwort nicht
j, calls = make_jarvis(True)
def broken(client, message):
    raise RuntimeError("Neon nicht erreichbar")
j.memory.process = broken
result = j.process_message("Ich heisse Moritz")
assert result == {"status": "response", "content": "ok"}

# Anzeige (Step 3.2): list_all liest die Datenbank, sortiert nach Typ und Schluessel
db.rows = [("farbe", "blau", "preference"), ("name", "Moritz", "fact")]
listing = Memory.list_all(m)
assert listing == [
    {"key": "farbe", "value": "blau", "type": "preference"},
    {"key": "name", "value": "Moritz", "type": "fact"},
]
assert "ORDER BY type, key" in db.statements[-1][0]
db.rows = []
assert Memory.list_all(m) == []
db.fail_on = "SELECT key"
try:
    Memory.list_all(m)
    raise AssertionError("Fehler haette durchschlagen muessen")
except RuntimeError:
    pass
db.fail_on = None

# Bearbeiten und Loeschen (Step 3.3)
m.memories = {"a": {"value": "1", "type": "fact"}, "b": {"value": "2", "type": "fact"}}

db.rowcount = 1
assert m.update("a", "neu", "preference") is True
sql, params = db.statements[-1]
assert sql == "UPDATE memories SET value = %s, type = %s WHERE key = %s"
assert params == ("neu", "preference", "a")
assert m.memories["a"] == {"value": "neu", "type": "preference"}

# Gibt es den Eintrag nicht (mehr): False, kein neuer Eintrag im Zwischenspeicher
db.rowcount = 0
assert m.update("weg", "x", "fact") is False
assert "weg" not in m.memories

db.rowcount = 1
assert m.delete("a") is True
assert db.statements[-1] == ("DELETE FROM memories WHERE key = %s", ("a",))
assert "a" not in m.memories and "b" in m.memories
db.rowcount = 0
assert m.delete("a") is False

db.rowcount = 7
assert m.delete_all() == 7
assert db.statements[-1][0] == "DELETE FROM memories"
assert m.memories == {}
db.rowcount = 0

# Schlaegt die DB fehl, bleibt der Zwischenspeicher unveraendert
m.memories = {"x": {"value": "1", "type": "fact"}}
db.fail_on = "DELETE"
for call in (lambda: m.delete("x"), lambda: m.delete_all()):
    try:
        call()
        raise AssertionError("Fehler haette durchschlagen muessen")
    except RuntimeError:
        pass
assert "x" in m.memories
db.fail_on = "UPDATE"
try:
    m.update("x", "y", "fact")
    raise AssertionError("Fehler haette durchschlagen muessen")
except RuntimeError:
    pass
assert m.memories["x"]["value"] == "1"
db.fail_on = None

print("ALL TESTS PASSED")
