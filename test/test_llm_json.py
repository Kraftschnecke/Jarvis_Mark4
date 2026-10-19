import sys, types
from pathlib import Path

# Projektordner (eine Ebene ueber diesem Testordner) in den Suchpfad legen,
# damit "import database" usw. funktioniert, egal von wo der Test gestartet wird.
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# psycopg/dotenv ggf. stubben, damit nichts eine echte DB berührt
for name in ("psycopg",):
    try:
        __import__(name)
    except ImportError:
        sys.modules[name] = types.ModuleType(name)
import database
database.DATABASE_URL = None

from llm_json import parse_llm_json
from memory import Memory
from project_analyzer import analyze_project_message

class R:
    def __init__(self, t): self.output_text = t
class Fake:
    def __init__(self, t):
        self.responses = types.SimpleNamespace(create=lambda **k: R(t))

class Reg:
    def get_all(self): return []
    def get(self, t): return object() if t == "GET_TIME" else None

D = {"a": 1, "b": None}
cases = [
    ('{"a": 5}', {"a": 5, "b": None}),
    ('```json\n{"a": 2, "b": 3}\n```', {"a": 2, "b": 3}),
    ('Hier: {"a": 9} fertig', {"a": 9, "b": None}),
    ('kein json', D), ('{"a": ', D), ('[1,2]', D), (None, D), ('', D),
]
for text, exp in cases:
    assert parse_llm_json(text, D) == exp, (text, parse_llm_json(text, D))

# memory
# ohne __init__, damit der Test keine Datenbankverbindung aufbaut
m = object.__new__(Memory); m.memories = {}; saved = []
m.save = lambda *a: saved.append(a)
m.process(Fake("müll"), "x"); assert saved == []
m.process(Fake('{"key": null, "value": null, "type": null}'), "x"); assert saved == []
m.process(Fake('{"key":"name","value":"Moritz","type":"fact"}'), "x"); assert len(saved) == 1
m.process(Fake('{"key":"x","value":"y","type":"quatsch"}'), "x"); assert len(saved) == 1

# project analyzer
assert analyze_project_message(Fake("müll"), "x")["relevant"] is False
assert analyze_project_message(Fake('{"relevant": true, "section": "Erfunden", "content": "x"}'), "x")["relevant"] is False
r = analyze_project_message(Fake('{"relevant": true, "section": "Progress", "content": "DB fertig"}'), "x")
assert r["relevant"] and r["requires_confirmation"] is False
print("ALL TESTS PASSED")
