import os
import sys
import tempfile
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    import dotenv  # noqa: F401
except ImportError:
    module = types.ModuleType("dotenv")
    module.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = module


# ---------- Fake-Datenbank (ersetzt psycopg VOR dem Import von project) ----------

class FakeDB:
    def __init__(self):
        self.statements = []
        self.fetchone_queue = []
        self.fetchall_queue = []
        self.connections = []


db = FakeDB()


class FakeCursor:
    def execute(self, sql, params=None):
        db.statements.append((" ".join(sql.split()), params))

    def fetchone(self):
        return db.fetchone_queue.pop(0) if db.fetchone_queue else None

    def fetchall(self):
        return db.fetchall_queue.pop(0) if db.fetchall_queue else []


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.committed = False
        self.rolled_back = False
        db.connections.append(self)

    def cursor(self):
        return FakeCursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


fake_psycopg = types.ModuleType("psycopg")
fake_psycopg.connect = lambda url: FakeConnection()
sys.modules["psycopg"] = fake_psycopg

os.chdir(tempfile.mkdtemp())      # "projects/" liegt relativ zum Arbeitsordner

import project                    # fuehrt init_project_db() gegen die Fake-DB aus
from project_context import get_project_file


def last_sql():
    return db.statements[-1]


# 1) Beim Import werden die drei Tabellen angelegt
created = " ".join(sql for sql, _ in db.statements)
for table in ("projects", "conversations", "messages"):
    assert f"CREATE TABLE IF NOT EXISTS {table}" in created, table
assert db.connections[0].committed and not db.connections[0].closed

# 2) Suche: ILIKE, Platzhalter werden entschaerft, leere Suche findet nichts
db.statements.clear()
db.fetchall_queue.append([(1, "Step9 Test")])
assert project.search_projects("step9") == [(1, "Step9 Test")]
sql, params = last_sql()
assert "ILIKE" in sql and "LIKE %s" in sql
assert params == ("%step9%",)

project.search_projects("100%_fertig")
assert last_sql()[1] == ("%100\\%\\_fertig%",)
project.search_projects("a\\b")
assert last_sql()[1] == ("%a\\\\b%",)
project.search_projects("  Jarvis  ")
assert last_sql()[1] == ("%Jarvis%",)

db.statements.clear()
for empty in (None, "", "   "):
    assert project.search_projects(empty) == []
assert db.statements == []        # nicht einmal eine Anfrage

# 3) Nachrichten: stabile Reihenfolge auch bei gleichem Zeitstempel
project.get_messages(7)
sql, params = last_sql()
assert "ORDER BY timestamp ASC, id ASC" in sql and params == (7,)

# 4) Projekt anlegen: Datei wird erzeugt, ID kommt zurueck
db.fetchone_queue.append((42,))
assert project.create_project("Alpha", "Beschreibung") == 42
assert get_project_file(42).exists()
assert get_project_file(42).read_text().startswith("# Alpha")
assert db.connections[-1].committed and not db.connections[-1].closed

# 5) Projekt loeschen: erst Nachrichten, dann Unterhaltungen, dann Projekt
db.statements.clear()
project.delete_project(42)
order = [sql.split()[2] for sql, _ in db.statements]
assert order == ["messages", "conversations", "projects"], order
assert all(params == (42,) for _, params in db.statements)
assert not get_project_file(42).exists()

# 6) Unterhaltung: anlegen, umbenennen, zuruecksetzen, loeschen
db.fetchone_queue.extend([(5,), (5, "Test 1", None, None)])
assert project.create_conversation(42, "Test 1") == (5, "Test 1", None, None)

db.statements.clear()
project.rename_conversation(5, "Neu")
assert last_sql()[1] == ("Neu", 5)

project.reset_conversation(5)
assert "DELETE FROM messages" in last_sql()[0]

db.statements.clear()
project.delete_conversation(5)
assert [sql.split()[2] for sql, _ in db.statements] == ["messages", "conversations"]

# 7) Nachricht speichern: Nachricht einfuegen UND last_active aktualisieren
db.statements.clear()
project.save_message(5, "user", "Hallo")
assert "INSERT INTO messages" in db.statements[0][0]
assert db.statements[0][1] == (5, "user", "Hallo")
assert "UPDATE conversations SET last_active" in db.statements[1][0]
assert db.connections[-1].committed

# 7b) Der Pool benutzt die Verbindung wieder: kein neues connect() pro Funktion
before = len(db.connections)
for _ in range(5):
    project.get_messages(5)
    project.get_projects()
assert len(db.connections) == before, (before, len(db.connections))

# 8) Gespeicherte Nachrichten -> Chatformat
db.fetchall_queue.append([(1, 5, "user", "Hi", None), (2, 5, "assistant", "Hallo", None)])
assert project.load_conversation_messages(5) == [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hallo"},
]

print("ALL TESTS PASSED")
