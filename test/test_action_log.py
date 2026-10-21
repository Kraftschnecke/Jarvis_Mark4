"""Aktionsprotokoll (Step 4.3): Eintraege, Kurzfassung, Fehlertoleranz, /api/actions. Fake-Datenbank."""

import contextlib
import io
import json
import re
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


class FakeTimeout(Exception):
    pass


stub_if_missing("openai", OpenAI=object)
stub_if_missing("psycopg")
stub_if_missing("psutil")
stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
stub_if_missing("requests", get=None, exceptions=types.SimpleNamespace(Timeout=FakeTimeout))
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




import datetime
import http.client
import io
import contextlib
import threading

import action_log
import db
import jarvis as jarvis_module
import risk
import server
import task_executor
from action import Action
from jarvis import Jarvis
from task import Task
from task_registry import TaskRegistry
from tasks import register_all_tasks
from tools.tool_result import ToolResult

# Standard nach dem Import: aus. Nur Jarvis() schaltet es ein.
assert action_log._enabled is False

registry = TaskRegistry()
register_all_tasks(registry)


# ---------- Fake-Datenbank, die die SQL-Befehle des Protokolls versteht ----------

class FakeDB:
    def __init__(self):
        self.rows = []
        self.next_id = 1
        self.statements = []
        self.connects = 0
        self.fail = False


fake = FakeDB()


class FakeCursor:
    def __init__(self):
        self._result = []

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        fake.statements.append(sql)

        if sql.startswith("CREATE TABLE IF NOT EXISTS action_log"):
            return

        if sql.startswith("INSERT INTO action_log"):
            fields = ("task_type", "goal", "details", "risk", "decision", "status", "summary")
            row = dict(zip(fields, params))
            row["id"] = fake.next_id
            row["created_at"] = datetime.datetime(2026, 10, 21, 3, 0, fake.next_id % 60,
                                                  tzinfo=datetime.timezone.utc)
            fake.next_id += 1
            fake.rows.append(row)
            return

        if sql.startswith("DELETE FROM action_log"):
            keep = params[0]
            top = max((r["id"] for r in fake.rows), default=0)
            fake.rows = [r for r in fake.rows if r["id"] > top - keep]
            return

        if sql.startswith("SELECT id, created_at"):
            ordered = sorted(fake.rows, key=lambda r: -r["id"])[: params[0]]
            self._result = [
                (r["id"], r["created_at"], r["task_type"], r["goal"], r["details"],
                 r["risk"], r["decision"], r["status"], r["summary"])
                for r in ordered
            ]
            return

        raise AssertionError("unbekanntes SQL: " + sql)

    def fetchall(self):
        return self._result


class FakeConnection:
    def cursor(self):
        return FakeCursor()


class FakeConnect:
    def __enter__(self):
        fake.connects += 1

        if fake.fail:
            raise RuntimeError("Datenbank nicht erreichbar")

        return FakeConnection()

    def __exit__(self, *exc):
        return False


db.connect = lambda: FakeConnect()


def reset(enabled=True):
    fake.rows.clear()
    fake.next_id = 1
    fake.statements.clear()
    fake.connects = 0
    fake.fail = False
    action_log.disable()
    action_log._table_ready = False

    if enabled:
        action_log.enable()


def task_of(task_type, parameters=None):
    return task_executor.prepare_registered_task(registry, task_type, parameters)


ran = []


def spy(action):
    ran.append(action.name)

    if action.name == "find_program":
        return ToolResult(success=True, data="C:/Programme/steam.exe")

    if action.name == "search_web":
        return ToolResult(success=True, data=[{"title": "T", "description": "GEHEIMER-TREFFERTEXT"}] * 3)

    if action.name == "fail_me":
        raise RuntimeError("kaputt")

    return ToolResult(success=True, data="ok")


task_executor.execute_action = spy

# 1) Ohne enable() wird nie geschrieben (Tests duerfen die echte DB nie anfassen)
reset(enabled=False)
task_executor.execute_task(task_of("GET_TIME"))
assert fake.connects == 0 and fake.rows == []

# 2) Sichere Aufgabe: ein Eintrag, "auto", ausgefuehrt
reset()
task_executor.execute_task(task_of("GET_TIME"))
assert len(fake.rows) == 1
row = fake.rows[0]
assert (row["task_type"], row["risk"], row["decision"], row["status"]) == (
    "GET_TIME", "safe", "auto", "COMPLETED")
assert row["goal"] == "Aktuelle Uhrzeit ermitteln" and row["summary"] == "ok"

# 3) Mit Bestaetigung: "confirmed", Parameter stehen als Details
reset()
task_executor.execute_task(task_of("START_PROGRAM", {"program": "steam"}), confirmed=True)
row = fake.rows[0]
assert (row["risk"], row["decision"], row["status"]) == ("confirm", "confirmed", "COMPLETED")
# Der aufgeloeste Pfad steht auch drin: man sieht, WAS wirklich gestartet wurde
assert row["details"] == "steam\nC:/Programme/steam.exe"

# 4) Ohne Bestaetigung blockiert der Executor: "blocked", nichts lief
reset()
ran.clear()
task_executor.execute_task(task_of("START_PROGRAM", {"program": "steam"}))
row = fake.rows[0]
assert (row["decision"], row["status"]) == ("blocked", "BLOCKED") and ran == []
assert "Bestaetigung" in row["summary"]

# 5) Verbotenes: auch mit confirmed=True nur "blocked"
reset()
task_executor.execute_task(task_of("OPEN_FILE", {"path": "C:/x/boese.exe"}), confirmed=True)
row = fake.rows[0]
assert (row["risk"], row["decision"], row["status"]) == ("forbidden", "blocked", "BLOCKED")

# 6) Fehlgeschlagene Aufgabe: Status FAILED, Fehlertext als Kurzfassung
reset()
broken = Task("KAPUTT", "Etwas Kaputtes")
broken.add_action(Action("get_current_time"))
task_executor.execute_action = lambda a: (_ for _ in ()).throw(RuntimeError("Das ging schief"))
task_executor.execute_task(broken)
task_executor.execute_action = spy
row = fake.rows[0]
assert (row["status"], row["summary"]) == ("FAILED", "Das ging schief")

# 7) Kurzfassung: Tool-Inhalte werden nie gespeichert
reset()
task_executor.execute_task(task_of("SEARCH_WEB", {"query": "wetter"}))
row = fake.rows[0]
assert row["summary"] == "3 Einträge" and row["details"] == "wetter"
assert all("GEHEIMER-TREFFERTEXT" not in str(v) for v in row.values())

t = Task("T", "x")
t.status = "COMPLETED"
t.result = [ToolResult(success=True, data={"a": 1})]
assert action_log.summarize(t) == "Daten erhalten"
t.result = [ToolResult(success=True, data="x" * 500)]
assert len(action_log.summarize(t)) == 200 and action_log.summarize(t).endswith("…")
t.result = [ToolResult(success=True, data="a\nb\x00c\u202ed")]
assert action_log.summarize(t) == "a b c d"
t.result = [ToolResult(success=True, data=True)]
assert action_log.summarize(t) == ""
t.result = None
assert action_log.summarize(t) == ""
t.error = "Fehler\n" + "y" * 500
assert len(action_log.summarize(t)) == 200 and "\n" not in action_log.summarize(t)

# 8) Details: hoechstens 5, ohne Steuerzeichen, gekuerzt
reset()
many = Task("MANY", "Viele")
many.add_action(Action("calculate", {f"p{i}": f"wert{i}\n" + "z" * 400 for i in range(9)}))
many.status = "COMPLETED"
action_log.record(many, "auto")
lines = fake.rows[0]["details"].split("\n")
assert len(lines) == 5 and all(len(line) <= 200 for line in lines)

# 9) Ein Fehler im Protokoll darf die Aufgabe nicht beeintraechtigen
reset()
fake.fail = True
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    task = task_of("GET_TIME")
    task_executor.execute_task(task)
assert task.status == "COMPLETED" and "[aktionslog]" in buffer.getvalue()
assert fake.rows == []

# 10) Tabelle wird nur einmal angelegt; alte Eintraege fallen weg
reset()
action_log.KEEP_ROWS = 3
for _ in range(6):
    task_executor.execute_task(task_of("GET_TIME"))
creates = [s for s in fake.statements if s.startswith("CREATE TABLE")]
assert len(creates) == 1
assert [r["id"] for r in fake.rows] == [4, 5, 6]
action_log.KEEP_ROWS = 2000

# 11) recent: neueste zuerst, feste Form, Grenze
reset()
for i in range(5):
    task_executor.execute_task(task_of("START_PROGRAM", {"program": f"p{i}"}), confirmed=True)
entries = action_log.recent(3)
assert [e["id"] for e in entries] == [5, 4, 3]
first = entries[0]
assert set(first) == {"id", "time", "task_type", "goal", "details", "risk",
                      "decision", "status", "summary"}
assert first["details"] == ["p4", "C:/Programme/steam.exe"] and first["time"].startswith("2026-10-21T03:00:")
assert len(action_log.recent(100)) == 5
assert len(action_log.recent(0)) == 1                   # mindestens 1
assert action_log.recent(10 ** 9) is not None           # wird auf 500 begrenzt

# =====================================================================
# Jarvis: Absagen und Ablehnen werden protokolliert
# =====================================================================

routes = []
jarvis_module.route_message = lambda client, message, reg: routes.pop(0)
jarvis_module.respond_to_task = lambda client, message, task: "Erledigt."


def route_for(task_type, parameters):
    return {"kind": "TASK", "task_type": task_type, "parameters": parameters,
            "command": {"intent": "NORMAL_MESSAGE"}}


j = object.__new__(Jarvis)
j.client = object()
j.task_registry = registry
j.pending_project_confirmation = None


def run(message):
    with contextlib.redirect_stdout(io.StringIO()):
        return j.process_message(message)


# Verboten: "refused", keine Ausfuehrung
reset()
ran.clear()
routes.append(route_for("OPEN_FILE", {"path": "C:/x/boese.exe"}))
run("Oeffne boese.exe")
assert [(r["decision"], r["status"], r["risk"]) for r in fake.rows] == [("refused", "BLOCKED", "forbidden")]
assert ran == []

# Rueckfrage nur gestellt: noch KEIN Eintrag (es ist ja nichts passiert)
reset()
routes.append(route_for("START_PROGRAM", {"program": "steam"}))
out = run("Starte Steam")
assert out["status"] == "confirmation" and fake.rows == []

# Abbrechen: "declined" / DECLINED, nichts ausgefuehrt
j.confirm_action(out["confirmation"]["id"], False)
assert [(r["decision"], r["status"]) for r in fake.rows] == [("declined", "DECLINED")]
assert fake.rows[0]["details"] == "steam" and ran == []

# Nein per Chat: ebenfalls "declined"
reset()
routes.append(route_for("START_PROGRAM", {"program": "steam"}))
run("Starte Steam")
run("nein")
assert [r["decision"] for r in fake.rows] == ["declined"]

# Ja per Knopf: ein Eintrag "confirmed" (vom Executor), kein doppelter
reset()
routes.append(route_for("START_PROGRAM", {"program": "steam"}))
out = run("Starte Steam")
j.confirm_action(out["confirmation"]["id"], True)
assert [(r["decision"], r["status"]) for r in fake.rows] == [("confirmed", "COMPLETED")]

# Abgelaufene / ungueltige Rueckfrage: nichts ausgefuehrt, nichts protokolliert
reset()
routes.append(route_for("START_PROGRAM", {"program": "steam"}))
run("Starte Steam")
j.confirm_action("0000000000000000", True)
assert fake.rows == []

# Sichere Aufgabe ueber Jarvis: ein Eintrag "auto"
reset()
routes.append(route_for("GET_TIME", {}))
run("Wie spaet ist es")
assert [(r["decision"], r["status"]) for r in fake.rows] == [("auto", "COMPLETED")]

# =====================================================================
# /api/actions
# =====================================================================

reset()
for i in range(3):
    task_executor.execute_task(task_of("GET_TIME"))

httpd = server.JarvisServer(("127.0.0.1", 0), object())
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def get(path):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request("GET", path)
    response = connection.getresponse()
    body = json.loads(response.read().decode("utf-8"))
    connection.close()
    return response.status, body


status, body = get("/api/actions")
assert status == 200 and [a["id"] for a in body["actions"]] == [3, 2, 1]
assert body["actions"][0]["decision"] == "auto"

# Es gibt absichtlich keine Moeglichkeit, Eintraege ueber die Oberflaeche zu aendern
for method in ("POST", "DELETE", "PUT"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, "/api/actions", body=b"{}", headers={"Content-Type": "application/json"})
    response = connection.getresponse()
    response.read()
    assert response.status in (404, 405, 501), (method, response.status)
    connection.close()
assert len(fake.rows) == 3

# Datenbank-Fehler: 500 mit freundlicher Meldung, kein Absturz
fake.fail = True
with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    status, body = get("/api/actions")
assert status == 500 and "Aktionsprotokoll" in body["error"]
fake.fail = False
assert get("/api/actions")[0] == 200

httpd.shutdown()
print("ALL TESTS PASSED")
