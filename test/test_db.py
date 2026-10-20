"""Tests fuer den Verbindungspool (db.py, Step 2.5). Keine echte Datenbank."""

import sys
import threading
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

try:
    import psycopg  # noqa: F401
except ImportError:
    sys.modules["psycopg"] = types.ModuleType("psycopg")

import db


# ---------- Fake-Verbindung ----------

class FakeConnection:
    def __init__(self):
        self.closed = False
        self.broken = False
        self.commits = 0
        self.rollbacks = 0
        self.pings = 0
        self.ping_fails = False
        self.rollback_fails = False

    def execute(self, sql):
        assert sql == "SELECT 1"
        self.pings += 1

        if self.ping_fails:
            raise RuntimeError("Verbindung getrennt")

    def commit(self):
        self.commits += 1

    def rollback(self):
        if self.rollback_fails:
            raise RuntimeError("rollback geht nicht")

        self.rollbacks += 1

    def close(self):
        self.closed = True


opened = []
connect_error = []


def fake_connect(url):
    if connect_error:
        raise connect_error[0]

    connection = FakeConnection()
    connection.url = url
    opened.append(connection)

    return connection


db.psycopg = types.SimpleNamespace(connect=fake_connect)


def reset(max_connections=4):
    db.close_all()
    opened.clear()
    connect_error.clear()
    db._slots = threading.BoundedSemaphore(max_connections)
    db.IDLE_CHECK_SECONDS = 30
    db.WAIT_SECONDS = 30


# 1) Wiederverwendung: zwei Aufrufe nacheinander, nur EINE Verbindung
reset()
with db.connect() as first:
    pass
with db.connect() as second:
    pass
assert first is second and len(opened) == 1
assert first.commits == 2 and not first.closed
assert first.url == db.config.DATABASE_URL

# 2) Fehler im Block: rollback, Fehler kommt durch, Verbindung bleibt brauchbar
reset()
try:
    with db.connect() as connection:
        raise ValueError("SQL kaputt")
    raise AssertionError("Fehler haette durchschlagen muessen")
except ValueError:
    pass
assert connection.rollbacks == 1 and connection.commits == 0
with db.connect() as again:
    pass
assert again is connection and len(opened) == 1

# 3) rollback geht nicht -> Verbindung wird geschlossen und nicht wiederverwendet
reset()
try:
    with db.connect() as connection:
        connection.rollback_fails = True
        raise ValueError("kaputt")
except ValueError:
    pass
assert connection.closed
with db.connect() as fresh:
    pass
assert fresh is not connection and len(opened) == 2

# 4) Eine geschlossene oder kaputte aufgehobene Verbindung wird verworfen
for flag in ("closed", "broken"):
    reset()
    with db.connect() as connection:
        pass
    setattr(connection, flag, True)
    with db.connect() as fresh:
        pass
    assert fresh is not connection and len(opened) == 2, flag

# 5) Frische Verbindung: kein Anklopfen. Alte Verbindung: "SELECT 1" davor.
reset()
with db.connect() as connection:
    pass
with db.connect():
    pass
assert connection.pings == 0

db.IDLE_CHECK_SECONDS = 0
with db.connect() as again:
    pass
assert again is connection and connection.pings == 1
assert connection.rollbacks == 1      # das Anklopfen beendet seine Transaktion

# 5b) Anklopfen schlaegt fehl (Neon hat getrennt) -> neue Verbindung, kein Fehler
connection.ping_fails = True
with db.connect() as fresh:
    pass
assert fresh is not connection and connection.closed and len(opened) == 2

# 6) Hoechstens MAX_CONNECTIONS gleichzeitig; Wartende bekommen einen Fehler
reset(max_connections=2)
db.WAIT_SECONDS = 0.2
outer_a = db.connect()
outer_b = db.connect()
a = outer_a.__enter__()
b = outer_b.__enter__()
assert a is not b
try:
    with db.connect():
        raise AssertionError("dritte Verbindung haette warten muessen")
except RuntimeError as error:
    assert "belegt" in str(error)
assert len(opened) == 2           # es wurde keine dritte geoeffnet

# 6b) Wird eine frei, kommt der Wartende dran (und bekommt genau diese)
db.WAIT_SECONDS = 5
got = []
started = threading.Event()


def waiter():
    started.set()

    with db.connect() as connection:
        got.append(connection)


thread = threading.Thread(target=waiter)
thread.start()
started.wait()
thread.join(0.3)
assert thread.is_alive() and not got          # wartet noch
outer_a.__exit__(None, None, None)
thread.join(5)
assert not thread.is_alive() and got == [a]
outer_b.__exit__(None, None, None)

# 7) Scheitert psycopg.connect, bleibt der Platz frei (kein Leck)
reset(max_connections=2)
connect_error.append(OSError("Neon nicht erreichbar"))
for _ in range(5):                  # mehr Versuche als Plaetze
    try:
        with db.connect():
            raise AssertionError("connect haette scheitern muessen")
    except OSError:
        pass
connect_error.clear()
with db.connect():
    pass
assert len(opened) == 1

# 8) Auch bei BaseException (z.B. Strg+C) wird der Platz frei
reset(max_connections=1)


class Abort(BaseException):
    pass


try:
    with db.connect():
        raise Abort()
except Abort:
    pass
db.WAIT_SECONDS = 0.2
with db.connect():                  # waere bei einem Leck ein RuntimeError
    pass

# 9) Gleichzeitig: jeder Thread bekommt eine EIGENE Verbindung
reset(max_connections=4)
barrier = threading.Barrier(4)
seen = []
lock = threading.Lock()


def worker():
    with db.connect() as connection:
        barrier.wait(5)             # alle vier halten gleichzeitig eine
        with lock:
            seen.append(connection)


threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join(10)
assert len(seen) == 4 and len({id(c) for c in seen}) == 4

# 10) close_all schliesst alles Aufgehobene
reset()
with db.connect() as connection:
    pass
db.close_all()
assert connection.closed

print("ALL TESTS PASSED")
