"""Web-Oberflaeche fuer J.A.R.V.I.S.

Ein kleiner HTTP-Server nur mit der Python-Standardbibliothek. Er macht zwei
Dinge:

  1. Er liefert die Dateien aus dem Ordner web/ aus (HTML, CSS, JavaScript).
  2. Er stellt eine kleine JSON-Schnittstelle bereit, ueber die die Seite mit
     Jarvis spricht:

       POST /api/message     {"message": "..."}  ->  {"status": ..., "content": ..., "messages": [...]}
                             ("messages" nur, wenn ein Chat-Befehl die offene Konversation geaendert hat)
       GET  /api/background?after=<id>  ->  {"messages": [{"id": 3, "text": "..."}], "last": 3}
                             (ohne "after": nur den aktuellen Stand "last" melden)
       GET  /api/projects    ->  {"projects": [...], "active": {...}}
       GET  /api/settings    ->  {"settings": {...}, "about": {...}}
       POST /api/settings    {"category", "key", "value"}  (nur erlaubte Einstellungen)
       POST /api/project/...       open, new, rename, delete
       POST /api/conversation/...  open, new, rename, reset, delete

Er ist bewusst nur fuer den eigenen Rechner gedacht (127.0.0.1) und hat keine
Anmeldung. Bevor Jarvis ueber das Internet erreichbar sein soll, braucht er
Login, HTTPS und eine Nutzertrennung.

Start:  py server.py
"""

import json
import platform
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config import SERVER_HOST, SERVER_PORT, VERSION
from workspace import WorkspaceError

WEB_DIR = Path(__file__).resolve().parent / "web"
MAX_BODY_BYTES = 64 * 1024
# Bis zu dieser Groesse wird ein Body immer gelesen, auch wenn die Anfrage
# abgelehnt wird. Sonst bricht der Server die Verbindung ab, waehrend der
# Browser noch sendet, und der Browser sieht keine Antwort (Windows: WinError 10053).
MAX_DRAIN_BYTES = 1024 * 1024

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def _is_int(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


# Nur diese Einstellungen duerfen ueber die Seite geaendert werden, und nur
# mit gueltigen Werten. Alles andere in settings.json bleibt unangetastet.
EDITABLE_SETTINGS = {
    ("appearance", "theme"): lambda v: v in ("Dark", "Light", "System"),
    ("appearance", "font_size"): lambda v: _is_int(v, 11, 20),
    ("memory", "enabled"): lambda v: isinstance(v, bool),
}


def settings_state(jarvis):
    return {
        "settings": jarvis.settings_manager.get_all(),
        "about": {
            "version": VERSION,
            "system": (
                f"Python {sys.version_info.major}.{sys.version_info.minor}"
                f".{sys.version_info.micro} · {platform.system()} {platform.release()}"
            ),
        },
    }


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def get_text(data, key):
    value = data.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, "Ungueltige Anfrage")

    return value.strip()


def get_id(data, key):
    value = data.get(key)

    # bool ist in Python auch ein int: True waere sonst die ID 1
    if not isinstance(value, int) or isinstance(value, bool):
        raise ApiError(400, "Ungueltige Anfrage")

    return value


def sidebar_state(jarvis, **extra):
    """Antwort fuer alle Aktionen der Seitenleiste: neuer Stand + Zusatz."""
    state = {
        "projects": jarvis.get_tree(),
        "active": jarvis.get_active()
    }
    state.update(extra)
    return state


def conversation_changed(jarvis, before):
    """Hat sich die offene Konversation durch eine Nachricht veraendert?

    Eine normale Nachricht haengt nur etwas an dieselbe Liste an. Anders ist
    es, wenn eine andere Konversation aktiv wurde, die Liste ersetzt wurde
    (Konversation neu geladen) oder kleiner geworden ist (Reset).
    """
    active, messages, count = before
    conversation = jarvis.conversation

    return (
        jarvis.get_active() != active
        or conversation.messages is not messages
        or len(conversation.messages) < count
    )


def api_post(jarvis, path, data):
    """Fuehrt eine POST-Aktion aus. Gibt das Antwort-Dict zurueck."""
    if path == "/api/message":
        conversation = jarvis.conversation
        before = (jarvis.get_active(), conversation.messages, len(conversation.messages))

        response = jarvis.process_message(get_text(data, "message"))

        result = {
            "status": response["status"],
            "content": response["content"]
        }

        # Chat-Befehle ("Oeffne Projekt X", "Reset", ...) koennen die offene
        # Konversation wechseln oder leeren. Dann bekommt der Browser den neuen
        # Verlauf mit, sonst zeigt das Chatfenster noch den alten.
        if conversation_changed(jarvis, before):
            result["messages"] = [
                dict(message) for message in jarvis.conversation.messages
            ]

        return result

    if path == "/api/settings":
        category = get_text(data, "category")
        key = get_text(data, "key")
        is_valid = EDITABLE_SETTINGS.get((category, key))

        if is_valid is None or "value" not in data or not is_valid(data["value"]):
            raise ApiError(400, "Diese Einstellung kann so nicht geaendert werden.")

        jarvis.settings_manager.set(category, key, data["value"])
        return settings_state(jarvis)

    if path == "/api/project/new":
        jarvis.add_project(get_text(data, "name"))
        return sidebar_state(jarvis)

    if path == "/api/project/open":
        jarvis.select_project(get_id(data, "project_id"))
        return sidebar_state(jarvis)

    if path == "/api/project/rename":
        jarvis.rename_project_by_id(
            get_id(data, "project_id"), get_text(data, "name")
        )
        return sidebar_state(jarvis)

    if path == "/api/project/delete":
        jarvis.delete_project_by_id(get_id(data, "project_id"))
        return sidebar_state(jarvis)

    if path == "/api/conversation/open":
        messages = jarvis.select_conversation(
            get_id(data, "project_id"), get_id(data, "conversation_id")
        )
        return sidebar_state(jarvis, messages=messages)

    if path == "/api/conversation/new":
        project_id = data.get("project_id")

        if project_id is not None:
            project_id = get_id(data, "project_id")

        jarvis.add_conversation(get_text(data, "title"), project_id)
        return sidebar_state(jarvis, messages=[])

    if path == "/api/conversation/rename":
        jarvis.rename_conversation_by_id(
            get_id(data, "project_id"),
            get_id(data, "conversation_id"),
            get_text(data, "title")
        )
        return sidebar_state(jarvis)

    if path == "/api/conversation/reset":
        jarvis.reset_conversation_by_id(
            get_id(data, "project_id"), get_id(data, "conversation_id")
        )
        return sidebar_state(jarvis)

    if path == "/api/conversation/delete":
        jarvis.delete_conversation_by_id(
            get_id(data, "project_id"), get_id(data, "conversation_id")
        )
        return sidebar_state(jarvis)

    raise ApiError(404, "Unbekannte Adresse")


class BackgroundFeed:
    """Sammelt Meldungen aus dem Hintergrund (z.B. Timer) fuer alle Browser-Tabs.

    Jarvis gibt jede Meldung nur einmal heraus. Wuerde jeder Tab direkt dort
    nachfragen, bekaeme nur ein zufaelliger Tab die Meldung (z.B. ein altes,
    vergessenes Fenster). Hier bekommt jede Meldung eine laufende Nummer, und
    jeder Tab fragt "alles nach Nummer X".
    """

    MAX_KEPT = 100

    def __init__(self):
        self.lock = threading.Lock()
        self.items = []   # [(id, text)]
        self.last = 0

    def collect(self, jarvis):
        with self.lock:
            for text in jarvis.check_background_results():
                self.last += 1
                self.items.append((self.last, text))

            del self.items[:-self.MAX_KEPT]

    def since(self, after):
        with self.lock:
            return self.last, [
                {"id": item_id, "text": text}
                for item_id, text in self.items
                if item_id > after
            ]


class JarvisServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, jarvis):
        super().__init__(address, JarvisHandler)
        self.jarvis = jarvis
        self.feed = BackgroundFeed()
        # Jarvis ist nicht fuer mehrere gleichzeitige Nachrichten gebaut.
        self.message_lock = threading.Lock()


class JarvisHandler(BaseHTTPRequestHandler):
    server_version = "Jarvis"

    # --- Hilfen ---------------------------------------------------------

    def log_message(self, format, *args):
        pass  # keine Zeile pro Anfrage im Terminal

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def host_allowed(self):
        """Nur Anfragen an localhost zulassen (Schutz vor DNS-Rebinding)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ("localhost", "127.0.0.1", "[::1]")

    def origin_allowed(self):
        """Eine fremde Webseite darf Jarvis nicht fernsteuern."""
        origin = self.headers.get("Origin")

        if origin is None:
            return True

        return urlparse(origin).hostname in ("localhost", "127.0.0.1", "::1")

    # --- Anfragen -------------------------------------------------------

    def do_GET(self):
        if not self.host_allowed():
            return self.send_json(403, {"error": "Host nicht erlaubt"})

        path = urlparse(self.path).path

        if path == "/api/background":
            feed = self.server.feed
            feed.collect(self.server.jarvis)

            after = parse_qs(urlparse(self.path).query).get("after")

            # Ohne "after" (neuer Tab): nur den aktuellen Stand melden, nichts
            # Altes nachliefern.
            if after is None:
                return self.send_json(200, {"messages": [], "last": feed.since(0)[0]})

            try:
                after = int(after[0])
            except ValueError:
                return self.send_json(400, {"error": "Ungueltige Anfrage"})

            last, messages = feed.since(after)
            return self.send_json(200, {"messages": messages, "last": last})

        if path == "/api/settings":
            return self.send_json(200, settings_state(self.server.jarvis))

        if path == "/api/projects":
            try:
                return self.send_json(200, sidebar_state(self.server.jarvis))
            except Exception:
                traceback.print_exc()
                return self.send_json(500, {"error": "Projekte konnten nicht geladen werden."})

        if path.startswith("/api/"):
            return self.send_json(404, {"error": "Unbekannte Adresse"})

        self.send_static(path)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1

        raw = b""

        if 0 < length <= MAX_DRAIN_BYTES:
            raw = self.rfile.read(length)
        elif length > MAX_DRAIN_BYTES:
            self.close_connection = True

        if not self.host_allowed() or not self.origin_allowed():
            return self.send_json(403, {"error": "Nicht erlaubt"})

        path = urlparse(self.path).path

        if not path.startswith("/api/"):
            return self.send_json(404, {"error": "Unbekannte Adresse"})

        # Nur JSON: ein fremdes Formular kann diesen Typ nicht ohne
        # Vorab-Pruefung des Browsers senden.
        content_type = (self.headers.get("Content-Type") or "").split(";")[0]

        if content_type.strip() != "application/json":
            return self.send_json(415, {"error": "Nur application/json"})

        if length <= 0 or length > MAX_BODY_BYTES:
            return self.send_json(400, {"error": "Ungueltige Laenge"})

        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            return self.send_json(400, {"error": "Ungueltige Anfrage"})

        if not isinstance(data, dict):
            return self.send_json(400, {"error": "Ungueltige Anfrage"})

        try:
            # Alles, was den Zustand von Jarvis aendert, laeuft nacheinander.
            # So wechselt niemand die Konversation, waehrend eine Antwort
            # noch in die alte gespeichert wird.
            with self.server.message_lock:
                result = api_post(self.server.jarvis, path, data)
        except ApiError as error:
            return self.send_json(error.status, {"error": str(error)})
        except WorkspaceError as error:
            return self.send_json(400, {"error": str(error)})
        except Exception:
            traceback.print_exc()
            return self.send_json(500, {"error": "Interner Fehler. Details im Terminal."})

        self.send_json(200, result)

    def send_static(self, url_path):
        if url_path == "/":
            url_path = "/index.html"

        # Nur Dateien innerhalb von web/ ausliefern (kein "../")
        target = (WEB_DIR / url_path.lstrip("/")).resolve()

        if WEB_DIR.resolve() not in target.parents or not target.is_file():
            return self.send_json(404, {"error": "Nicht gefunden"})

        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def main():
    from jarvis import Jarvis

    jarvis = Jarvis()
    server = JarvisServer((SERVER_HOST, SERVER_PORT), jarvis)
    url = f"http://localhost:{server.server_address[1]}"

    print(f"J.A.R.V.I.S. laeuft auf {url}  (beenden mit Strg+C)")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nJ.A.R.V.I.S.: Shutting down, Sir")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
