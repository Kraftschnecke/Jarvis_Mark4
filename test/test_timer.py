"""Timer-Dauer (convert_to_seconds): Einheiten in beiden Sprachen, ungueltige Werte."""

import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import timer
from timer import convert_to_seconds

assert convert_to_seconds(10, "seconds") == 10
assert convert_to_seconds(5, "minutes") == 300
assert convert_to_seconds(2, "hours") == 7200
for unit, factor in (("Minuten", 60), (" Minute ", 60), ("MIN", 60), ("Sekunden", 1), ("s", 1),
                     ("Stunden", 3600), ("h", 3600), ("Hours", 3600)):
    assert convert_to_seconds(1, unit) == factor, unit
assert convert_to_seconds(1.5, "minutes") == 90
assert convert_to_seconds("5", "minutes") == 300           # Zahl als Text
assert convert_to_seconds("2,5", "minutes") == 150         # deutsches Komma
assert convert_to_seconds(24, "hours") == 86400            # genau erlaubt

for bad_unit in ("Tage", "", None, 5, ["minutes"], "ms"):
    try:
        convert_to_seconds(5, bad_unit)
        raise AssertionError(f"Einheit haette abgelehnt werden muessen: {bad_unit!r}")
    except ValueError:
        pass

for bad_value in (0, -5, "abc", "", None, True, [5], {"a": 1}, float("nan"), float("inf"), 25, 10 ** 9):
    unit = "hours" if bad_value == 25 else "minutes"
    try:
        convert_to_seconds(bad_value, unit)
        raise AssertionError(f"Wert haette abgelehnt werden muessen: {bad_value!r}")
    except ValueError:
        pass

# Der Fehler von frueher: "5" * 60 darf nie entstehen
assert not isinstance(convert_to_seconds("5", "minutes"), str)

# ---------- Timer mit Namen (Step 6b) ----------
import time
import background_tasks

assert timer.clean_name("Nudeln") == "Nudeln"
assert timer.clean_name("  Nu\ndeln\t\x00 !  ") == "Nu deln !"
for empty in (None, "", "   ", 5, ["x"], {"a": 1}, "\u200b\u200b"):
    assert timer.clean_name(empty) == "Timer", empty
assert len(timer.clean_name("x" * 500)) <= timer.MAX_NAME_LENGTH

assert timer.format_duration(45) == "45 Sekunden"
assert timer.format_duration(300) == "5 Minuten"
assert timer.format_duration(90) == "1 Minuten 30 Sekunden"
assert timer.format_duration(3600) == "1 Stunde"
assert timer.format_duration(3900) == "1 Stunde 5 Minuten"
assert timer.format_duration(7200) == "2 Stunden"


def clear_all():
    for t in timer.list_timers():
        timer.cancel_timer_by_id(t["id"])
    background_tasks.get_results()


clear_all()
assert timer.list_timers() == []

# Starten, auflisten (der naechste zuerst), Restzeit
timer.start_timer(600, "Nudeln")
timer.start_timer(60, "Ei")
listed = timer.list_timers()
assert [t["name"] for t in listed] == ["Ei", "Nudeln"], listed
assert 0 < listed[0]["remaining"] <= 60 and listed[1]["seconds"] == 600

# Abbrechen nach Namen (Gross-/Kleinschreibung egal), nur dieser eine
assert timer.cancel_timer("nudeln") == "Nudeln"
assert [t["name"] for t in timer.list_timers()] == ["Ei"]

# Unbekannter Name: nichts wird abgebrochen, Meldung nennt die laufenden
try:
    timer.cancel_timer("Pizza")
    raise AssertionError("haette abgelehnt werden muessen")
except timer.TimerError as error:
    assert "Ei" in str(error)
assert len(timer.list_timers()) == 1

# Ohne Namen: bei genau einem Timer wird dieser abgebrochen
assert timer.cancel_timer(None) == "Ei"
assert timer.list_timers() == []
try:
    timer.cancel_timer("Ei")
    raise AssertionError("kein Timer laeuft")
except timer.TimerError as error:
    assert "kein Timer" in str(error)

# Mehrdeutig: zwei gleiche Namen oder kein Name bei mehreren -> nichts passiert
timer.start_timer(600, "Tee")
timer.start_timer(600, "Tee")
for ask in ("Tee", None, "Timer"):
    try:
        timer.cancel_timer(ask)
        raise AssertionError(f"haette nachfragen muessen: {ask!r}")
    except timer.TimerError:
        pass
assert len(timer.list_timers()) == 2
clear_all()

# "Timer" ist der Standardname: trifft den unbenannten, auch wenn andere laufen
timer.start_timer(600, "Nudeln")
timer.start_timer(600)
assert timer.cancel_timer("Timer") == "Timer"
assert [t["name"] for t in timer.list_timers()] == ["Nudeln"]
clear_all()

# Abbrechen nach Nummer (Oberflaeche)
entry = timer.start_timer(600, "Eins")
assert timer.cancel_timer_by_id(entry.id) is True
assert timer.cancel_timer_by_id(entry.id) is False      # zweites Mal: gibt es nicht mehr
assert timer.cancel_timer_by_id("x") is False

# Ein abgebrochener Timer meldet sich nie
timer.start_timer(0.2, "Still")
timer.cancel_timer("Still")
time.sleep(0.5)
assert background_tasks.get_results() == []

# Ein ablaufender Timer meldet sich mit Namen und verschwindet aus der Liste
timer.start_timer(0.1, "Kurz")
time.sleep(0.5)
results = background_tasks.get_results()
assert results == [{"type": "TIMER_FINISHED", "data": {"seconds": 0.1, "name": "Kurz"}}], results
assert timer.list_timers() == []

# Obergrenze
for i in range(timer.MAX_ACTIVE_TIMERS):
    timer.start_timer(600, f"T{i}")
try:
    timer.start_timer(600, "zu viel")
    raise AssertionError("Obergrenze fehlt")
except timer.TimerError as error:
    assert str(timer.MAX_ACTIVE_TIMERS) in str(error)
assert len(timer.list_timers()) == timer.MAX_ACTIVE_TIMERS
clear_all()
# Nach dem Abbrechen ist wieder Platz
timer.start_timer(600, "wieder frei")
clear_all()

# ---------- Auswahl bei mehreren Timern (Step 6b) ----------
c = [{"id": 1, "name": "A", "remaining": 30}, {"id": 2, "name": "B", "remaining": 90},
     {"id": 3, "name": "C", "remaining": 4000}]


def names(chosen):
    return None if chosen is None else [t["name"] for t in chosen]


for text, expected in (
    ("1", ["A"]), ("2", ["B"]), (" 3. ", ["C"]), ("Nummer 2", ["B"]), ("nr. 2", ["B"]), ("Timer 3", ["C"]),
    ("den zweiten", ["B"]), ("der erste", ["A"]), ("dritten", ["C"]),
    ("den kürzeren", ["A"]), ("kürzesten", ["A"]), ("den kuerzeren", ["A"]), ("den nächsten", ["A"]),
    ("den längeren", ["C"]), ("längsten", ["C"]), ("der letzte", ["C"]),
    ("beide", ["A", "B", "C"]), ("alle", ["A", "B", "C"]), ("alle Timer", ["A", "B", "C"]),
):
    assert names(timer.pick(text, c)) == expected, text

for text in ("0", "4", "99", "-1", "foo", "", "   ", "Brich den Timer ab", "ja", "nein", "1 2", "zwei", None, 5, ["1"]):
    assert timer.pick(text, c) is None, text
assert timer.pick("1", []) is None
assert names(timer.pick("den längeren", c[:2])) == ["B"]

assert timer.describe(c) == "1: A (noch 0:30), 2: B (noch 1:30), 3: C (noch 1:06:40)"

# Nachfrage: zwei Timer ohne Namen -> nichts passiert, Liste mit Nummern, naechste Nachricht waehlt
clear_all()
timer.clear_choice()
timer.start_timer(600)
timer.start_timer(300)
try:
    timer.cancel_timer("Timer")
    raise AssertionError("haette nachfragen muessen")
except timer.TimerError as error:
    assert "1: Timer (noch 5:0" in str(error) and "2: Timer (noch 10:0" in str(error), str(error)
    assert "Welchen meinst du" in str(error)
assert len(timer.list_timers()) == 2

assert timer.answer_pending("den längeren") == "Timer abgebrochen: Timer."
remaining = timer.list_timers()
assert len(remaining) == 1 and remaining[0]["seconds"] == 300       # der kuerzere laeuft weiter
assert timer.answer_pending("1") is None                            # Rueckfrage ist verbraucht
assert len(timer.list_timers()) == 1
clear_all()

# Die Rueckfrage gilt nur fuer die DIREKT folgende Nachricht
timer.start_timer(600, "Tee")
timer.start_timer(300, "Tee")
try:
    timer.cancel_timer("Tee")
    raise AssertionError("haette nachfragen muessen")
except timer.TimerError:
    pass
assert timer.answer_pending("Wie spät ist es") is None              # keine Auswahl: verworfen
assert timer.answer_pending("2") is None                            # zu spaet
assert len(timer.list_timers()) == 2

# Ohne offene Rueckfrage tut "2" nichts
assert timer.answer_pending("2") is None and len(timer.list_timers()) == 2

# Rueckfrage laeuft ab
try:
    timer.cancel_timer("Tee")
except timer.TimerError:
    pass
timer._pending["until"] = time.monotonic() - 1
assert timer.answer_pending("1") is None and len(timer.list_timers()) == 2

# Auswahl "beide"
try:
    timer.cancel_timer("Tee")
except timer.TimerError:
    pass
assert timer.answer_pending("beide") == "Timer abgebrochen: Tee, Tee."
assert timer.list_timers() == []

# Der Timer ist inzwischen von selbst abgelaufen
timer.start_timer(600, "X")
timer.start_timer(0.1, "Y")
try:
    timer.cancel_timer("Timer")
except timer.TimerError:
    pass
time.sleep(0.4)
assert timer.answer_pending("1") == "Dieser Timer ist schon abgelaufen."
clear_all(); background_tasks.get_results()

# Die Nummern bleiben, wie sie angeboten wurden, auch wenn inzwischen einer ablaeuft
timer.start_timer(600, "X")
timer.start_timer(0.1, "Y")
try:
    timer.cancel_timer("Timer")
except timer.TimerError as error:
    assert "1: Y" in str(error) and "2: X" in str(error), str(error)
time.sleep(0.4)
assert timer.answer_pending("2") == "Timer abgebrochen: X."           # "2" ist weiter X, nicht Y
assert timer.list_timers() == []
background_tasks.get_results()

# clear_choice verwirft die Rueckfrage (z.B. beim Wechsel der Konversation)
timer.start_timer(600, "P"); timer.start_timer(300, "Q")
try:
    timer.cancel_timer("Timer")
except timer.TimerError:
    pass
timer.clear_choice()
assert timer.answer_pending("1") is None and len(timer.list_timers()) == 2
clear_all()

# Direkt per Nummer / Selektor, ohne Nachfrage (das Modell schreibt z.B. "2" oder "kuerzester")
timer.start_timer(600, "Nudeln"); timer.start_timer(300, "Ei"); timer.start_timer(900, "Tee")
assert timer.cancel_timer("2") == "Nudeln"                          # Liste: 1 Ei, 2 Nudeln, 3 Tee
assert timer.cancel_timer("kürzester") == "Ei"
assert timer.cancel_timer("alle") == "Tee"
assert timer.list_timers() == []
# Ein Timer, der "2" heisst, hat Vorrang vor der Nummer
timer.start_timer(600, "2"); timer.start_timer(300, "Ei")
assert timer.cancel_timer("2") == "2"
clear_all()

print("ALL TESTS PASSED")
