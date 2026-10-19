import http.client
import json
import sys
import threading
import time
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    import dotenv  # noqa: F401
except ImportError:
    m = types.ModuleType("dotenv")
    m.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = m

project_stub = types.ModuleType("project")
for name in (
    "search_projects", "get_conversations", "create_conversation",
    "load_conversation_messages", "save_message", "get_conversation",
    "rename_conversation", "create_project", "reset_conversation",
    "delete_conversation", "get_projects", "rename_project", "delete_project"
):
    setattr(project_stub, name, lambda *a, **k: None)
sys.modules["project"] = project_stub
for name, attrs in (("openai", {"OpenAI": object}), ("psycopg", {}),
                    ("psutil", {}), ("requests", {})):
    try:
        __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod

import tempfile
from settings_manager import SettingsManager
import config
import server
import workspace as workspace_module
import jarvis as jarvis_module
from fake_project_db import FakeProjectDB


class FakeJarvis:
    def __init__(self):
        self.received = []
        self.background = ["Sir, der Timer ist abgelaufen."]
        self.active = 0
        self.max_active = 0

    def process_message(self, message):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        self.active -= 1
        self.received.append(message)
        if message == "exit":
            return {"status": "exit", "content": "Shutting down, Sir"}
        return {"status": "response", "content": f"Echo: {message}"}

    def check_background_results(self):
        out, self.background = self.background, []
        return out


fdb = FakeProjectDB()
fdb.install(workspace_module)

fake = object.__new__(jarvis_module.Jarvis)
fake.workspace = workspace_module.Workspace()
fake.pending_project_confirmation = None
settings_file = Path(tempfile.mkdtemp()) / "settings.json"
fake.settings_manager = SettingsManager(settings_file)
helper = FakeJarvis()
fake.process_message = helper.process_message
fake.check_background_results = helper.check_background_results
fake.received = helper.received
httpd = server.JarvisServer(("127.0.0.1", 0), fake)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def request(method, path, body=None, headers=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = dict(headers or {})
    conn.putrequest(method, path, skip_host=True)
    conn.putheader("Host", host or f"localhost:{port}")
    for key, value in headers.items():
        conn.putheader(key, value)
    if body is not None:
        conn.putheader("Content-Length", str(len(body)))
    conn.endheaders(body)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, response.getheader("Content-Type"), data


def post(payload, headers=None, raw=None, host=None):
    body = raw if raw is not None else json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    return request("POST", "/api/message", body, h, host)


# 1) Statische Dateien
status, ctype, data = request("GET", "/")
assert status == 200 and "text/html" in ctype and b"J.A.R.V.I.S." in data
assert request("GET", "/style.css")[0] == 200
status, ctype, _ = request("GET", "/app.js")
assert status == 200 and "javascript" in ctype
assert request("GET", "/gibtsnicht.html")[0] == 404

# 2) Kein Zugriff auf Dateien ausserhalb von web/
for evil in ("/../server.py", "/..%2fserver.py", "/%2e%2e/config.py", "/../.env"):
    assert request("GET", evil)[0] == 404, evil

# 3) Nachricht
status, _, data = post({"message": "Hallo"})
assert status == 200
assert json.loads(data) == {"status": "response", "content": "Echo: Hallo"}
assert fake.received == ["Hallo"]
assert json.loads(post({"message": "exit"})[2])["status"] == "exit"

# 4) Ungueltige Anfragen
assert post({"message": ""})[0] == 400
assert post({"message": "   "})[0] == 400
assert post({"message": 5})[0] == 400
assert post({"x": 1})[0] == 400
assert post(None, raw=b"kein json")[0] == 400
assert post(None, raw=b"[1,2]")[0] == 400
assert post({"message": "x" * 70000})[0] == 400
# Grosse Anfrage: der Browser muss die Antwort sehen (kein Verbindungsabbruch)
assert post({"message": "x" * 600000})[0] == 400
assert post({"message": "x" * 600000}, headers={"Content-Type": "text/plain"})[0] == 415
assert post({"message": "x"}, headers={"Content-Type": "text/plain"})[0] == 415
assert request("POST", "/api/message", None, {"Content-Type": "application/json"})[0] == 400
assert request("POST", "/api/anderes", b"{}", {"Content-Type": "application/json"})[0] == 404
assert request("GET", "/api/anderes")[0] == 404
assert "x" * 5 not in fake.received  # nichts davon erreichte Jarvis

# 5) Schutz vor fremden Seiten
before = len(fake.received)
assert post({"message": "boese"}, headers={"Origin": "https://evil.example"})[0] == 403
assert post({"message": "boese"}, host="evil.example")[0] == 403
assert request("GET", "/", host="evil.example")[0] == 403
assert request("GET", "/api/background?after=0", host="evil.example")[0] == 403
assert len(fake.received) == before
assert post({"message": "ok"}, headers={"Origin": f"http://localhost:{port}"})[0] == 200

# 6) Hintergrundmeldungen: jeder Tab bekommt jede Meldung (nummeriert)
def background(after=None):
    path = "/api/background" if after is None else f"/api/background?after={after}"
    status, _, data = request("GET", path)
    return status, json.loads(data)


# Neuer Tab: bekommt nichts Altes, nur den aktuellen Stand
status, data = background()
assert status == 200 and data["messages"] == [] and data["last"] == 1  # die alte Meldung ist gezaehlt
tab_a = tab_b = data["last"]

helper.background = ["Sir, der Timer ist abgelaufen."]
status, data = background(tab_a)
assert data["messages"] == [{"id": 2, "text": "Sir, der Timer ist abgelaufen."}] and data["last"] == 2
# ein zweiter Tab fragt auch noch nach derselben Meldung und bekommt sie ebenfalls
assert background(tab_b)[1]["messages"] == data["messages"]
tab_a = tab_b = 2
assert background(tab_a)[1]["messages"] == []
assert background(2)[1]["last"] == 2
# Ein ganz neuer Tab (ohne "after") bekommt die alte Meldung nicht nachgeliefert
assert background()[1]["messages"] == []
assert background("abc")[0] == 400
assert background(-5)[1]["messages"][0]["id"] == 1   # alles seit Anfang

# 7) Gleichzeitige Nachrichten laufen nacheinander
helper.max_active = 0
threads = [threading.Thread(target=post, args=({"message": f"m{i}"},)) for i in range(5)]
[t.start() for t in threads]
[t.join() for t in threads]
assert helper.max_active == 1, helper.max_active

# 8) Hintergrund-Abfrage blockiert nicht, waehrend Jarvis denkt
helper.background = ["spaet"]
slow = threading.Thread(target=post, args=({"message": "langsam"},))
slow.start()
time.sleep(0.01)
assert background(2)[1]["messages"] == [{"id": 3, "text": "spaet"}]
slow.join()

# =====================================================================
# Seitenleiste
# =====================================================================
def call(path, payload=None):
    if payload is None:
        status, _, data = request("GET", path)
    else:
        status, _, data = post_to(path, payload)
    return status, json.loads(data)


def post_to(path, payload, headers=None):
    body = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    return request("POST", path, body, h)


# Leer starten
status, data = call("/api/projects")
assert status == 200 and data == {
    "projects": [], "active": {"project_id": None, "conversation_id": None}
}

# Konversation ohne Projekt: lesbare Fehlermeldung
status, data = call("/api/conversation/new", {"title": "X"})
assert status == 400 and "zuerst" in data["error"]

# Projekt anlegen: wird sofort aktiv
status, data = call("/api/project/new", {"name": "Roboter"})
assert status == 200 and [p["name"] for p in data["projects"]] == ["Roboter"]
pid = data["projects"][0]["id"]
assert data["active"] == {"project_id": pid, "conversation_id": None}
status, data = call("/api/project/new", {"name": "roboter"})
assert status == 400 and "schon" in data["error"]
assert call("/api/project/new", {"name": ""})[0] == 400
assert call("/api/project/new", {})[0] == 400

# Projekt anklicken (open) und Konversation direkt in einem Projekt anlegen
other_pid = fdb.add_project("Zweites")
status, data = call("/api/project/open", {"project_id": other_pid})
assert status == 200 and data["active"] == {"project_id": other_pid, "conversation_id": None}
status, data = call("/api/conversation/new", {"title": "Im ersten", "project_id": pid})
assert status == 200 and data["active"]["project_id"] == pid
first_cid = data["active"]["conversation_id"]
assert call("/api/conversation/new", {"title": "x", "project_id": "1"})[0] == 400
assert call("/api/conversation/new", {"title": "x", "project_id": 999})[0] == 400
assert call("/api/project/open", {"project_id": 999})[0] == 400
assert call("/api/project/open", {})[0] == 400
call("/api/conversation/delete", {"project_id": pid, "conversation_id": first_cid})
call("/api/project/delete", {"project_id": other_pid})
call("/api/project/open", {"project_id": pid})

# Konversation mit Verlauf oeffnen
cid = fdb.add_conversation(pid, "Alt", [{"role": "user", "content": "frueher"}])
status, data = call("/api/conversation/open", {"project_id": pid, "conversation_id": cid})
assert status == 200 and data["messages"] == [{"role": "user", "content": "frueher"}]
assert data["active"] == {"project_id": pid, "conversation_id": cid}
assert data["projects"][0]["conversations"] == [{"id": cid, "title": "Alt"}]

# Neue Konversation, umbenennen, zuruecksetzen, loeschen
status, data = call("/api/conversation/new", {"title": "Neu"})
assert status == 200 and data["messages"] == []
new_cid = data["active"]["conversation_id"]
status, data = call("/api/conversation/rename", {"project_id": pid, "conversation_id": new_cid, "title": "Neu 2"})
assert status == 200 and {"id": new_cid, "title": "Neu 2"} in data["projects"][0]["conversations"]
assert call("/api/conversation/reset", {"project_id": pid, "conversation_id": cid})[0] == 200
assert fdb.messages[cid] == []
status, data = call("/api/conversation/delete", {"project_id": pid, "conversation_id": new_cid})
assert status == 200 and data["active"]["conversation_id"] is None

# Projekt umbenennen und loeschen
status, data = call("/api/project/rename", {"project_id": pid, "name": "Roboter 2"})
assert status == 200 and data["projects"][0]["name"] == "Roboter 2"
status, data = call("/api/project/delete", {"project_id": pid})
assert status == 200 and data["projects"] == [] and data["active"]["project_id"] is None

# Fehlerfaelle: falsche Typen und unbekannte IDs
assert call("/api/conversation/open", {"project_id": "1", "conversation_id": 2})[0] == 400
assert call("/api/conversation/open", {"project_id": True, "conversation_id": 1})[0] == 400
assert call("/api/conversation/open", {"project_id": 999, "conversation_id": 1})[0] == 400
assert call("/api/project/delete", {"project_id": 999})[0] == 400
assert call("/api/conversation/gibtsnicht", {"x": 1})[0] == 404

# Schutz gilt auch fuer die neuen Adressen
assert post_to("/api/project/new", {"name": "boese"}, {"Origin": "https://evil.example"})[0] == 403
assert request("GET", "/api/projects", host="evil.example")[0] == 403
assert call("/api/projects")[1]["projects"] == []

# Unerwarteter Fehler: 500 ohne interne Details
workspace_module.get_projects = lambda: 1 / 0
status, _, data = request("GET", "/api/projects")
assert status == 500 and b"division" not in data
fdb.install(workspace_module)

# =====================================================================
# Einstellungen
# =====================================================================
status, data = call("/api/settings")
assert status == 200
assert data["settings"]["appearance"]["theme"] == "Dark"
assert data["settings"]["memory"]["enabled"] is True
assert data["about"]["version"] == config.VERSION and "Python" in data["about"]["system"]

# Erlaubte Aenderungen wirken sofort und werden in settings.json gespeichert
status, data = call("/api/settings", {"category": "appearance", "key": "theme", "value": "Light"})
assert status == 200 and data["settings"]["appearance"]["theme"] == "Light"
assert json.loads(settings_file.read_text(encoding="utf-8"))["appearance"]["theme"] == "Light"
assert call("/api/settings", {"category": "appearance", "key": "font_size", "value": 16})[0] == 200
assert fake.settings_manager.get("appearance", "font_size") == 16

# Der Memory-Schalter erreicht Jarvis wirklich
assert fake.memory_enabled() is True
call("/api/settings", {"category": "memory", "key": "enabled", "value": False})
assert fake.memory_enabled() is False
call("/api/settings", {"category": "memory", "key": "enabled", "value": True})
assert fake.memory_enabled() is True

# Ungueltiges wird abgelehnt und aendert nichts
before = fake.settings_manager.get_all()
for bad in (
    {"category": "appearance", "key": "theme", "value": "Neon"},
    {"category": "appearance", "key": "font_size", "value": 5},
    {"category": "appearance", "key": "font_size", "value": 99},
    {"category": "appearance", "key": "font_size", "value": True},
    {"category": "appearance", "key": "font_size", "value": "16"},
    {"category": "memory", "key": "enabled", "value": "false"},
    {"category": "memory", "key": "enabled", "value": 0},
    {"category": "jarvis", "key": "name", "value": "Hacker"},      # (noch) nicht aenderbar
    {"category": "general", "key": "language", "value": "Deutsch"},
    {"category": "nope", "key": "x", "value": 1},
    {"category": "appearance", "key": "theme"},                    # ohne Wert
    {"key": "theme", "value": "Dark"},                             # ohne Kategorie
):
    assert call("/api/settings", bad)[0] == 400, bad
assert fake.settings_manager.get_all() == before

# Schutz gilt auch hier
assert post_to("/api/settings", {"category": "memory", "key": "enabled", "value": False},
               {"Origin": "https://evil.example"})[0] == 403
assert fake.memory_enabled() is True
assert request("GET", "/api/settings", host="evil.example")[0] == 403

httpd.shutdown()
print("ALL TESTS PASSED")
