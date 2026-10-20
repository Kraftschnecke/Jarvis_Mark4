"""project.md in der Datenbank (Step 3.1). Fake-Datenbank im Speicher."""

import os
import re
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

import db as db_module
import project_context as pc
import workspace as workspace_module
from jarvis import Jarvis
from workspace import Workspace


# ---------- Fake-Datenbank, die die SQL-Befehle von project_context versteht ----------

class FakeDB:
    def __init__(self):
        self.contexts = {}                  # project_id -> content
        self.names = {42: "Step9 Test", 7: "Sieben", 5: "Fuenf", 6: "Sechs"}
        self.projects = {42, 7}             # Projekte, die es "gibt"
        self.statements = []
        self.commits = 0
        self.rollbacks = 0


fake = FakeDB()


class FakeCursor:
    rowcount = 0

    def __init__(self):
        self._row = None

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        fake.statements.append(sql)
        self.rowcount = 0
        self._row = None

        if sql.startswith("INSERT INTO project_contexts (project_id, content) SELECT"):
            assert "ON CONFLICT (project_id) DO NOTHING" in sql, sql
            text, pid = params
            if pid in fake.projects and pid not in fake.contexts:
                fake.contexts[pid] = text
                self.rowcount = 1
        elif sql.startswith("INSERT INTO project_contexts") and "DO NOTHING" in sql:
            pid, text = params
            fake.contexts.setdefault(pid, text)
        elif sql.startswith("INSERT INTO project_contexts") and "DO UPDATE" in sql:
            pid, text = params
            fake.contexts[pid] = text
        elif sql.startswith("SELECT content FROM project_contexts"):
            pid = params[0]
            self._row = (fake.contexts[pid],) if pid in fake.contexts else None
        elif sql.startswith("SELECT c.content, p.name FROM project_contexts"):
            pid = params[0]
            self._row = (
                (fake.contexts[pid], fake.names[pid]) if pid in fake.contexts else None
            )
        elif sql.startswith("UPDATE project_contexts SET content"):
            text, pid = params
            fake.contexts[pid] = text
        elif sql.startswith("DELETE FROM project_contexts"):
            fake.contexts.pop(params[0], None)
        else:
            raise AssertionError("unerwartetes SQL: " + sql)

    def fetchone(self):
        return self._row


class FakeConnection:
    closed = False
    broken = False

    def cursor(self):
        return FakeCursor()

    def commit(self):
        fake.commits += 1

    def rollback(self):
        fake.rollbacks += 1

    def close(self):
        pass


db_module.psycopg = types.SimpleNamespace(connect=lambda url: FakeConnection())
os.chdir(tempfile.mkdtemp())      # "projects/" (alter Ort) liegt relativ dazu

# 1) Vorlage anlegen; ein zweiter Aufruf ueberschreibt nichts
assert pc.get_project_context(42) is None
pc.ensure_project_context(42, "Step9 Test")
text = pc.get_project_context(42)
assert text.startswith("# Step9 Test") and "## Decisions" in text
pc.save_project_context(42, text + "\nEigener Zusatz\n")
pc.ensure_project_context(42, "Anderer Name")
assert "Eigener Zusatz" in pc.get_project_context(42)
assert pc.get_project_context(42).startswith("# Step9 Test")
pc.save_project_context(42, text)

# 2) Eintrag hinzufuegen: einmal, nicht doppelt, nicht in fehlende Abschnitte
assert pc.add_to_project_section(42, "Decisions", "Backend in Python") is True
assert "Backend in Python" in pc.get_project_context(42)
assert pc.add_to_project_section(42, "Decisions", "Backend in Python") is False
assert pc.get_project_context(42).count("Backend in Python") == 1
assert pc.add_to_project_section(42, "Gibt es nicht", "x") is False
assert pc.add_to_project_section(999, "Decisions", "x") is False       # kein Kontext

# Andere Abschnitte bleiben unberuehrt
assert "## Next Steps" in pc.get_project_context(42)
assert "None yet." in pc.get_project_context(42).split("## Open Topics")[1]

# 3) Abschnitt ersetzen
assert pc.update_project_section(42, "Goal", "Roboter bauen") is True
goal = pc.get_project_context(42).split("## Goal")[1].split("## Description")[0]
assert "Roboter bauen" in goal and "Not defined yet" not in goal
assert pc.update_project_section(42, "Gibt es nicht", "x") is False
assert pc.update_project_section(999, "Goal", "x") is False

# 4) Lesen und Schreiben in EINER Transaktion mit Sperre (kein Ueberschreiben)
fake.statements.clear()
commits = fake.commits
pc.add_to_project_section(42, "Progress", "Pool fertig")
assert fake.commits == commits + 1
assert "FOR UPDATE" in fake.statements[0] and fake.statements[1].startswith("UPDATE")

# Nichts zu aendern -> kein UPDATE
fake.statements.clear()
pc.add_to_project_section(42, "Progress", "Pool fertig")
assert not any(s.startswith("UPDATE") for s in fake.statements)

# 5) Loeschen
pc.delete_project_context(42)
assert pc.get_project_context(42) is None

# 6) Oeffnen eines Projekts legt den Text an (aelteres Projekt ohne Kontext)
workspace_module.search_projects = lambda name: [(42, "Step9 Test")]
workspace_module.get_conversations = lambda project_id: []
workspace_module.create_conversation = lambda project_id, title: (1, title, None, None)


def make_jarvis():
    j = object.__new__(Jarvis)
    j.workspace = Workspace()
    j.pending_project_confirmation = None
    return j


assert pc.get_project_context(42) is None
make_jarvis().open_project("Step9")
assert pc.get_project_context(42).startswith("# Step9 Test")
before = pc.get_project_context(42)
make_jarvis().open_project("Step9")
assert pc.get_project_context(42) == before

# 7) Einmalige Uebernahme der alten Dateien
fake.contexts.clear()
legacy = Path("projects")
(legacy / "42").mkdir(parents=True)
(legacy / "42" / "project.md").write_text("# Alt 42\n\n## Goal\n\nAlt\n", encoding="utf-8")
(legacy / "7").mkdir()
(legacy / "7" / "project.md").write_text("# Alt 7\n", encoding="utf-8")
(legacy / "99").mkdir()                                              # Projekt 99 gibt es nicht
(legacy / "99" / "project.md").write_text("# Alt 99\n", encoding="utf-8")
(legacy / "abc").mkdir()                                             # kein Projektordner
(legacy / "abc" / "project.md").write_text("# abc\n", encoding="utf-8")
(legacy / "5").mkdir()                                               # Ordner ohne Datei
fake.projects.add(5)

fake.contexts[7] = "# Neuer Stand in der DB\n"                       # darf nicht ueberschrieben werden
assert pc.migrate_local_files() == 1
assert fake.contexts[42].startswith("# Alt 42")
assert fake.contexts[7] == "# Neuer Stand in der DB\n"
assert 99 not in fake.contexts and 5 not in fake.contexts
assert (legacy / "42" / "project.md").exists()                       # Dateien bleiben liegen
assert pc.migrate_local_files() == 0                                 # zweiter Lauf: nichts mehr

# Alte Dateien aus Mark 3 sind cp1252 (Windows), nicht UTF-8: Umlaute muessen stimmen
fake.contexts.clear()
(legacy / "5" / "project.md").write_bytes("# Fuenf\n\n## Goal\n\nGrößere Prüfung\n".encode("cp1252"))
(legacy / "7" / "project.md").write_bytes("# Sieben ü\n".encode("utf-8"))    # UTF-8 geht auch
assert pc.migrate_local_files() == 3                                 # 42, 7 und 5
assert "Größere Prüfung" in fake.contexts[5]
assert fake.contexts[7] == "# Sieben ü\n"

# Datenbank-Text ist noch die reine Vorlage -> die Datei darf ihn ersetzen
fake.projects.add(6)
fake.contexts[6] = pc.template("Sechs")
(legacy / "6").mkdir()
(legacy / "6" / "project.md").write_text("# Sechs\n\n## Goal\n\nEcht\n", encoding="utf-8")
fake.contexts[7] = "# Sieben bearbeitet\n"                               # veraendert -> bleibt
fake.contexts[42] = "# Alt 42\n\n## Goal\n\nAlt\n"
fake.contexts[5] = "x"                                               # veraendert -> bleibt
assert pc.migrate_local_files() == 1
assert "Echt" in fake.contexts[6]
assert fake.contexts[7] == "# Sieben bearbeitet\n" and fake.contexts[5] == "x"
assert pc.migrate_local_files() == 0

# Eine Datei, die sich nicht lesen laesst, stoppt die anderen nicht
fake.contexts.clear()
real_read = pc._read_legacy


def broken_read(file):
    if file.parent.name == "5":
        raise OSError("gesperrt")

    return real_read(file)


pc._read_legacy = broken_read
assert pc.migrate_local_files() == 3                                 # 42, 7, 6; 5 fehlgeschlagen
assert 5 not in fake.contexts
pc._read_legacy = real_read

# Ohne Ordner projects/: nichts zu tun
os.chdir(tempfile.mkdtemp())
assert pc.migrate_local_files() == 0

print("ALL TESTS PASSED")
