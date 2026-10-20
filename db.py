"""Verbindungspool fuer die Datenbank (Mark 4, Step 2.5).

Vorher oeffnete jede Datenbank-Funktion eine neue Verbindung zu Neon (im Netz,
mit TLS und Anmeldung: je ca. 0,1 bis 0,3 s) und schloss sie wieder. Jetzt
werden Verbindungen nach Gebrauch aufgehoben und wiederverwendet.

Benutzung (in memory.py und project.py):

    with db.connect() as connection:
        cursor = connection.cursor()
        cursor.execute(...)

- Ende des Blocks ohne Fehler -> commit, Verbindung zurueck in den Pool.
- Fehler im Block            -> rollback, Fehler wird weitergereicht.
- Kein manuelles commit()/close() mehr noetig (und nicht mehr vergessbar).

Warum kein Fremdpaket (psycopg-pool)? Die Aufgabe ist klein genug, um sie in
einer Datei zu verstehen, und es gibt keine neue Abhaengigkeit.

Regeln:
- Hoechstens MAX_CONNECTIONS Verbindungen gleichzeitig offen (Neon begrenzt
  das). Ist alles belegt, wartet der Aufrufer bis zu WAIT_SECONDS.
- Eine Verbindung wird nie von zwei Threads gleichzeitig benutzt: Wer sie hat,
  hat sie allein, bis der Block endet.
- Neon schaltet ruhende Datenbanken ab und trennt dann die Verbindungen. Eine
  Verbindung, die laenger als IDLE_CHECK_SECONDS ungenutzt war, wird deshalb
  vor der Benutzung mit "SELECT 1" geprueft; ist sie tot, wird eine neue
  geoeffnet. Der Aufrufer merkt davon nichts.
"""

import threading
import time
from contextlib import contextmanager

import psycopg

import config

MAX_CONNECTIONS = 4
IDLE_CHECK_SECONDS = 30
WAIT_SECONDS = 30

_lock = threading.Lock()
_idle = []          # [(verbindung, zeitpunkt_der_letzten_nutzung)], neueste zuletzt
_slots = threading.BoundedSemaphore(MAX_CONNECTIONS)


def _close(connection):
    try:
        connection.close()
    except Exception:
        pass


def _is_usable(connection, last_used):
    """Ist die aufgehobene Verbindung noch brauchbar?"""
    if getattr(connection, "closed", False) or getattr(connection, "broken", False):
        return False

    if time.monotonic() - last_used < IDLE_CHECK_SECONDS:
        return True

    # Lange ungenutzt: kurz anklopfen
    try:
        connection.execute("SELECT 1")
        connection.rollback()
    except Exception:
        return False

    return True


def _take():
    """Gibt eine brauchbare Verbindung. Belegt dafuer einen der Plaetze."""
    if not _slots.acquire(timeout=WAIT_SECONDS):
        raise RuntimeError(
            "Datenbank: alle Verbindungen sind belegt (Zeitueberschreitung)."
        )

    try:
        while True:
            with _lock:
                entry = _idle.pop() if _idle else None

            if entry is None:
                return psycopg.connect(config.DATABASE_URL)

            connection, last_used = entry

            if _is_usable(connection, last_used):
                return connection

            _close(connection)
    except BaseException:
        _slots.release()
        raise


def _give_back(connection, healthy):
    """Legt die Verbindung zurueck in den Pool oder schliesst sie."""
    try:
        if not healthy:
            # Nach einem Fehler ist die Transaktion kaputt: zuruecksetzen.
            # Klappt das nicht, ist die Verbindung unbrauchbar.
            connection.rollback()

        if getattr(connection, "closed", False) or getattr(connection, "broken", False):
            raise ConnectionError("Verbindung geschlossen")

        with _lock:
            _idle.append((connection, time.monotonic()))
    except Exception:
        _close(connection)
    finally:
        _slots.release()


@contextmanager
def connect():
    """Leiht eine Verbindung aus dem Pool (siehe Kopf dieser Datei)."""
    connection = _take()
    healthy = False

    try:
        yield connection
        connection.commit()
        healthy = True
    finally:
        _give_back(connection, healthy)


def close_all():
    """Schliesst alle aufgehobenen Verbindungen (z.B. beim Beenden, in Tests)."""
    with _lock:
        entries = list(_idle)
        _idle.clear()

    for connection, _ in entries:
        _close(connection)
