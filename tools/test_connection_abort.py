"""Bricht der Browser eine GET-Anfrage ab (Seite neu geladen), darf nichts im Terminal stehen
(Fehler 8.5 der Abnahme: Traceback bei /api/projects)."""
import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re

source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"), encoding="utf-8").read()

# Jedes "except Exception:" mit traceback.print_exc() muss davor ein "except ConnectionError:" haben
blocks = re.findall(r"(?m)^( +)except Exception:\n\1    traceback\.print_exc\(\)", source)
guarded = re.findall(r"(?m)^( +)except ConnectionError:\n\1    raise[^\n]*\n\1except Exception:\n\1    traceback\.print_exc\(\)", source)
assert len(blocks) == len(guarded) and blocks, (len(blocks), len(guarded))

# Netzwerkfehler der KI: eine Zeile statt Traceback
jarvis_source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.py"), encoding="utf-8").read()
assert "APIConnectionError" in jarvis_source and "Keine Verbindung zur KI" in jarvis_source

print("ALL TESTS PASSED")
