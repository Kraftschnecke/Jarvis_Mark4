"""Widgets der rechten Seitenleiste (Etappe C): Notizen, Tagesziele, Kalender-Termine, Eishockey.

Notizen, Ziele und Termine liegen in widgets.json neben settings.json (nur auf deinem Rechner).
Spielplaene kommen aus dem Netz, und zwar nur ueber den Server: der Browser ruft nie selbst
ins Internet. Ohne Netz zeigt die Seite den letzten bekannten Stand oder eine Meldung.
"""

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MAX_NOTES = 5000
MAX_GOALS = 20
MAX_GOAL_LENGTH = 200
MAX_EVENTS = 500
MAX_EVENT_TITLE = 100
EVENT_KEEP_DAYS = 31            # Termine, die laenger her sind, werden beim Speichern aufgeraeumt

# Alle Zugriffe auf widgets.json (Seite UND Jarvis-Aufgaben) laufen durch dieses eine Schloss,
# damit sich zwei gleichzeitige Speichervorgaenge nichts ueberschreiben.
_FILE_LOCK = threading.RLock()

_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class WidgetStore:
    def __init__(self, path="widgets.json", today=date.today):
        self.path = Path(path)
        self.today = today
        self._lock = _FILE_LOCK

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data):
        # Erst in eine Nebendatei, dann umbenennen: ein Absturz hinterlaesst keine halbe Datei
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _clean_goals(items):
        clean = []
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                clean.append({"text": item["text"][:MAX_GOAL_LENGTH], "done": item.get("done") is True,
                              "daily": item.get("daily") is True})
        return clean[:MAX_GOALS]

    @staticmethod
    def _clean_events(items):
        clean = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            title, day, at, event_id = item.get("title"), item.get("date"), item.get("time", ""), item.get("id")
            if isinstance(title, str) and isinstance(event_id, str) and isinstance(at, str) \
                    and (at == "" or _TIME.match(at)) and _valid_date(day):
                clean.append({"id": event_id, "title": title[:MAX_EVENT_TITLE], "date": day, "time": at})
        clean.sort(key=lambda e: (e["date"], e["time"] or "00:00", e["title"]))
        return clean[:MAX_EVENTS]

    def get(self):
        with self._lock:
            data = self._load()
        today = self.today().isoformat()
        notes = data.get("notes") if isinstance(data.get("notes"), str) else ""
        goals = data.get("goals") if isinstance(data.get("goals"), dict) else {}
        items = self._clean_goals(goals.get("items"))
        if goals.get("date") != today:
            # Neuer Tag: einmalige Ziele sind weg, taegliche kommen wieder, als noch nicht erledigt
            items = [dict(g, done=False) for g in items if g["daily"]]
        return {"notes": notes, "goals": items, "date": today, "events": self._clean_events(data.get("events"))}

    def set_notes(self, text):
        if not isinstance(text, str) or len(text) > MAX_NOTES:
            raise ValueError(f"Die Notiz darf höchstens {MAX_NOTES} Zeichen lang sein.")
        with self._lock:
            data = self._load()
            data["notes"] = text
            self._save(data)

    def set_goals(self, items):
        if not isinstance(items, list) or len(items) > MAX_GOALS:
            raise ValueError(f"Höchstens {MAX_GOALS} Ziele pro Tag.")
        clean = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) \
                    or not isinstance(item.get("done"), bool) \
                    or not isinstance(item.get("daily", False), bool):
                raise ValueError("Ungültiges Ziel.")
            text = " ".join(item["text"].split())
            if not text:
                raise ValueError("Ein Ziel darf nicht leer sein.")
            if len(text) > MAX_GOAL_LENGTH:
                raise ValueError(f"Ein Ziel darf höchstens {MAX_GOAL_LENGTH} Zeichen lang sein.")
            clean.append({"text": text, "done": item["done"], "daily": item.get("daily", False)})
        with self._lock:
            data = self._load()
            data["goals"] = {"date": self.today().isoformat(), "items": clean}
            self._save(data)

    # ---- Kalender-Termine (von der Seite oder von Jarvis)
    def add_event(self, title, day, at=""):
        if not isinstance(title, str) or not isinstance(day, str) or not isinstance(at, str):
            raise ValueError("Ungültiger Termin.")
        title = " ".join(title.split())
        at = at.strip()
        if not title:
            raise ValueError("Ein Termin braucht einen Titel.")
        if len(title) > MAX_EVENT_TITLE:
            raise ValueError(f"Der Titel darf höchstens {MAX_EVENT_TITLE} Zeichen lang sein.")
        if not _valid_date(day):
            raise ValueError("Ungültiges Datum.")
        today = self.today()
        chosen = date.fromisoformat(day)
        if chosen < today - timedelta(days=EVENT_KEEP_DAYS) or chosen > today + timedelta(days=365 * 5):
            raise ValueError("Das Datum liegt zu weit weg (höchstens 5 Jahre voraus).")
        if at and not _TIME.match(at):
            raise ValueError("Ungültige Uhrzeit (Format HH:MM).")
        with self._lock:
            data = self._load()
            events = self._clean_events(data.get("events"))
            cutoff = (today - timedelta(days=EVENT_KEEP_DAYS)).isoformat()
            events = [e for e in events if e["date"] >= cutoff]
            if len(events) >= MAX_EVENTS:
                raise ValueError(f"Es sind höchstens {MAX_EVENTS} Termine möglich.")
            event = {"id": secrets.token_hex(4), "title": title, "date": day, "time": at}
            events.append(event)
            data["events"] = events
            self._save(data)
        return event

    def delete_event(self, event_id):
        if not isinstance(event_id, str):
            raise ValueError("Ungültiger Termin.")
        with self._lock:
            data = self._load()
            events = self._clean_events(data.get("events"))
            kept = [e for e in events if e["id"] != event_id]
            if len(kept) == len(events):
                raise ValueError("Diesen Termin gibt es nicht.")
            data["events"] = kept
            self._save(data)

    def events_on(self, day):
        return [e for e in self.get()["events"] if e["date"] == day]

    def upcoming_events(self, limit=10):
        today = self.today().isoformat()
        return [e for e in self.get()["events"] if e["date"] >= today][:limit]


def _valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


_default_store = None


def default_store():
    """Die eine Datei widgets.json (Seite und Jarvis-Aufgaben teilen sich diese)."""
    global _default_store
    if _default_store is None:
        _default_store = WidgetStore()
    return _default_store


def set_default_store(store):
    """Nur fuer Tests."""
    global _default_store
    _default_store = store


# ----------------------------------------------------------------------
# Eishockey (NHL-Schnittstelle, Adler Mannheim per Kalenderdatei)
# ----------------------------------------------------------------------

# Anzeigename in den Einstellungen -> woher der Spielplan kommt und wie viele Spiele folgen.
# Weitere Teams: hier eintragen und in settings_manager.CHOICES ergaenzen.
TEAMS = {
    "Edmonton Oilers": {
        "kind": "nhl", "abbrev": "EDM", "next": 4,
        "url": "https://api-web.nhle.com/v1/club-schedule-season/EDM/now",
    },
    # Offizielle Kalenderdatei der Adler ("Download Spielplan"): Paarungen und Termine, ohne Ergebnisse
    "Adler Mannheim": {
        "kind": "ics", "match": "adler mannheim", "next": 3,
        "url": "https://adler-mannheim.de/saison/spielplan/iCal.ics",
    },
}
NEXT_GAMES = 4
CACHE_SECONDS = 300
MAX_RESPONSE_BYTES = 8_000_000
ALLOWED_HOSTS = ("api-web.nhle.com", "adler-mannheim.de", "www.adler-mannheim.de")
GAME_DURATION = timedelta(hours=3)      # so lange gilt ein Spiel ohne Ergebnis-Quelle als "laeuft"

_LIVE = {"LIVE", "CRIT"}
_FINAL = {"FINAL", "OFF"}


class HockeyError(Exception):
    pass


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    """Weiterleitungen nur auf erlaubte Hosts und nur per https."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed(newurl):
            raise HockeyError("Weiterleitung auf eine unerlaubte Adresse.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _allowed(url):
    parts = urllib.parse.urlsplit(url)
    return parts.scheme == "https" and parts.hostname in ALLOWED_HOSTS


def fetch_text(url):
    """Holt Text aus dem Netz (nur https, nur erlaubte Hosts, Zeit- und Groessenlimit)."""
    if not _allowed(url):
        raise HockeyError("Unerlaubte Adresse.")
    opener = urllib.request.build_opener(_SafeRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": "Jarvis"})
    with opener.open(request, timeout=8) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise HockeyError("Antwort zu groß.")
    return raw.decode("utf-8")


def fetch_json(url):
    return json.loads(fetch_text(url))


def _name(node):
    """Name eines Teams: NHL liefert {"default": "Oilers"} oder einen Text."""
    if isinstance(node, dict):
        node = node.get("default")
    return node if isinstance(node, str) else None


def _side(node):
    if not isinstance(node, dict):
        return None
    abbrev = node.get("abbrev")
    if not isinstance(abbrev, str):
        return None
    score = node.get("score")
    return {
        "abbrev": abbrev,
        "name": _name(node.get("commonName")) or _name(node.get("placeName")) or abbrev,
        "score": score if isinstance(score, int) and not isinstance(score, bool) else None,
    }


def parse_games(data, abbrev):
    """Macht aus der NHL-Antwort eine einfache Liste. Kaputte Eintraege werden uebersprungen."""
    games = data.get("games") if isinstance(data, dict) else None
    result = []
    for game in games if isinstance(games, list) else []:
        if not isinstance(game, dict):
            continue
        home, away = _side(game.get("homeTeam")), _side(game.get("awayTeam"))
        start = game.get("startTimeUTC")
        if not home or not away or not isinstance(start, str) or len(start) > 40:
            continue
        try:
            datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            continue
        state = game.get("gameState")
        result.append({
            "start": start,
            "state": "live" if state in _LIVE else "final" if state in _FINAL else "future",
            "home": home,
            "away": away,
            "team_is_home": home["abbrev"] == abbrev,
        })
    result.sort(key=lambda g: g["start"])
    return result


# ---- Kalenderdatei (iCal) der Adler

def _last_sunday(year, month):
    day = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return day - timedelta(days=(day.weekday() + 1) % 7)


def berlin_to_utc(local):
    """Ortszeit Berlin (ohne Zeitzone) -> UTC. Sommerzeit: letzter Sonntag im Maerz 2 Uhr
    bis letzter Sonntag im Oktober 3 Uhr (EU-Regel). Ohne tzdata, das gibt es unter Windows nicht immer."""
    begin = datetime.combine(_last_sunday(local.year, 3), datetime.min.time()) + timedelta(hours=2)
    finish = datetime.combine(_last_sunday(local.year, 10), datetime.min.time()) + timedelta(hours=3)
    offset = 2 if begin <= local < finish else 1
    return (local - timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def _unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _unescape(value):
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) in "nN" else m.group(1), value)


def parse_ics(text, match, now=None):
    """Liest die Kalenderdatei. 'Heim vs. Gast' im Titel, Beginn mit Zeitzone Berlin oder UTC.
    Gibt dieselbe Liste wie parse_games zurueck (ohne Punktestand). Unpassendes wird uebersprungen."""
    now = now or datetime.now(timezone.utc)
    games = []
    event = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            event = {}
        elif line == "END:VEVENT":
            game = _ics_game(event, match, now) if event is not None else None
            if game:
                games.append(game)
            event = None
        elif event is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *params = head.split(";")
            if name.upper() in ("SUMMARY", "DTSTART"):
                event[name.upper()] = (value, [p.upper() for p in params])
    games.sort(key=lambda g: g["start"])
    return games


def _ics_game(event, match, now):
    if "SUMMARY" not in event or "DTSTART" not in event:
        return None
    summary = _unescape(event["SUMMARY"][0])
    value, params = event["DTSTART"]
    parts = re.split(r"\s+vs\.?\s+", summary, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return None
    home, away = parts[0].strip()[:60], parts[1].strip()[:60]
    found = re.fullmatch(r"(\d{8}T\d{6})(Z?)", value.strip())
    if not found or any(p.startswith("VALUE=DATE") and "DATE-TIME" not in p for p in params):
        return None                              # ganztaegige Termine u.a. gibt es hier nicht
    try:
        naive = datetime.strptime(found.group(1), "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    tzid = next((p[5:] for p in params if p.startswith("TZID=")), None)
    if found.group(2) == "Z":
        start = naive.replace(tzinfo=timezone.utc)
    elif tzid in (None, "EUROPE/BERLIN"):
        start = berlin_to_utc(naive)
    else:
        return None                              # fremde Zeitzone: lieber nichts als eine falsche Uhrzeit
    if now >= start + GAME_DURATION:
        state = "final"
    elif now >= start:
        state = "live"
    else:
        state = "future"
    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": state,
        "home": {"abbrev": home, "name": home, "score": None},
        "away": {"abbrev": away, "name": away, "score": None},
        "team_is_home": match in home.lower(),
    }


def pick_games(games, count=NEXT_GAMES):
    """Aktuelles Spiel = laufendes, sonst das letzte beendete. Dazu die naechsten `count`."""
    live = [g for g in games if g["state"] == "live"]
    final = [g for g in games if g["state"] == "final"]
    future = [g for g in games if g["state"] == "future"]
    current = live[0] if live else (final[-1] if final else None)
    return {"current": current, "next": future[:count]}


class HockeyFeed:
    def __init__(self, fetch=fetch_text, clock=time.time, ttl=CACHE_SECONDS):
        self.fetch = fetch
        self.clock = clock
        self.ttl = ttl
        self._cache = {}
        self._lock = threading.Lock()

    def _load(self, source):
        text = self.fetch(source["url"])
        if source["kind"] == "ics":
            return parse_ics(text, source["match"], datetime.fromtimestamp(self.clock(), timezone.utc))
        return parse_games(json.loads(text) if isinstance(text, str) else text, source["abbrev"])

    def get(self, team_name):
        source = TEAMS.get(team_name)
        if source is None:
            raise HockeyError("Unbekanntes Team.")
        with self._lock:
            cached = self._cache.get(team_name)
            if cached and self.clock() - cached["at"] < self.ttl:
                return dict(cached["data"], stale=False)
            try:
                games = self._load(source)
            except Exception as error:
                # Ohne Netz: lieber der alte Stand (als veraltet markiert) als nichts
                if cached:
                    return dict(cached["data"], stale=True)
                raise HockeyError("Der Spielplan ist gerade nicht erreichbar.") from error
            data = dict(pick_games(games, source["next"]), team=team_name,
                        scores=source["kind"] == "nhl",
                        updated=datetime.now(timezone.utc).isoformat())
            self._cache[team_name] = {"at": self.clock(), "data": data}
            return dict(data, stale=False)
