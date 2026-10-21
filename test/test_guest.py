"""Gastmodus (guest.py): nur plaudern + 4 harmlose Aufgaben, nichts vom Besitzer, kein Zugriff."""

import importlib.abc
import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# Diese Module gehoeren zu Datenbank, Gedaechtnis, Projekten und dem echten Jarvis.
# Der Gastmodus darf sie weder importieren noch brauchen: Jeder Import schlaegt hier fehl.
FORBIDDEN_MODULES = {"db", "memory", "project", "workspace", "jarvis", "psycopg", "project_context",
                     "project_analyzer", "project_state", "database"}


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name in FORBIDDEN_MODULES:
            raise ImportError(f"Der Gastmodus darf {name} nicht importieren")
        return None


sys.meta_path.insert(0, Blocker())


def stub_if_missing(name, **attrs):
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module


stub_if_missing("openai", OpenAI=object)
stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
stub_if_missing("requests")

import background_tasks
import guest
import router
import task_executor
from guest import GuestJarvis, REFUSAL

assert not (FORBIDDEN_MODULES & set(sys.modules)), FORBIDDEN_MODULES & set(sys.modules)


class FakeClient:
    def __init__(self, answer="Gerne, Sir."):
        self.calls = []
        self.answer = answer
        self.error = None
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return types.SimpleNamespace(output_text=self.answer)


def chat_route():
    return {"kind": "CHAT", "task_type": None, "parameters": {},
            "command": {"intent": "NORMAL_MESSAGE", "project_name": None,
                        "conversation_name": None, "new_conversation_name": None}}


routes = []
routed_registries = []


def fake_route(client, message, registry):
    routed_registries.append(registry)
    return routes.pop(0) if routes else chat_route()


guest.route_message = fake_route

executed = []
real_execute_action = task_executor.execute_action
task_executor.execute_action = lambda action: (executed.append(action.name), real_execute_action(action))[1]

# 1) Nur vier Aufgaben, alle harmlos
client = FakeClient()
g = GuestJarvis(client)
assert sorted(g.task_registry.tasks) == sorted(["GET_TIME", "GET_DATE", "CALCULATE", "SEARCH_WEB"])
for forbidden in ("OPEN_FILE", "START_PROGRAM", "SET_VOLUME", "START_TIMER", "CANCEL_TIMER", "LIST_TIMERS",
                  "GET_RUNNING_PROGRAMS", "GET_SYSTEM_INFO", "FIND_PROGRAM"):
    assert g.task_registry.get(forbidden) is None, forbidden

# Wird eine Gast-Aufgabe riskant, startet der Gastmodus gar nicht erst
import risk
original = risk.ACTION_RISK["search_web"]
risk.ACTION_RISK["search_web"] = risk.CONFIRM
try:
    GuestJarvis(FakeClient())
    raise AssertionError("haette nicht starten duerfen")
except RuntimeError:
    pass
risk.ACTION_RISK["search_web"] = original

# 2) Chat: Gast-Hinweis im Prompt, kein Gedaechtnis, nur der Gast-Verlauf
reply = g.process_message("Wer bist du?")
assert reply == {"status": "response", "content": "Gerne, Sir."}
call = client.calls[-1]
assert "Gastmodus" in call["instructions"] and "Behaupte nie" in call["instructions"]
assert [m["role"] for m in call["input"]] == ["user"]
g.process_message("Und noch eine Frage")
assert [m["role"] for m in client.calls[-1]["input"]] == ["user", "assistant", "user"]
assert len(g.conversation.messages) == 4
assert routed_registries[-1] is g.task_registry          # Router kennt nur die Gast-Aufgaben

# Verlauf bleibt begrenzt
for i in range(60):
    g.process_message(f"Nachricht {i}")
    g.hits.clear()
assert len(g.conversation.messages) <= 40

# 3) Befehle und Plaene werden abgelehnt, ohne Modellaufruf danach und ohne Folgen
for intent in sorted(router.COMMAND_INTENTS):
    client = FakeClient(); g = GuestJarvis(client)
    route = chat_route(); route["kind"] = "COMMAND"; route["command"]["intent"] = intent
    routes.append(route)
    assert g.process_message("irgendwas")["content"] == REFUSAL, intent
    assert client.calls == [] and g.conversation.messages == [], intent
client = FakeClient(); g = GuestJarvis(client)
plan_route = chat_route(); plan_route["kind"] = "PLAN"
routes.append(plan_route)
assert g.process_message("Starte Notepad und sag die Uhrzeit")["content"] == REFUSAL
assert client.calls == []

# 4) Harmlose Aufgabe laeuft und wird beantwortet
client = FakeClient("Es ist spaet, Sir.")
g = GuestJarvis(client)
task_route = chat_route(); task_route.update(kind="TASK", task_type="GET_TIME", parameters={})
routes.append(task_route)
executed.clear()
assert g.process_message("Wie spaet ist es?")["content"] == "Es ist spaet, Sir."
assert executed == ["get_current_time"]
assert len(client.calls) == 1                           # nur die Antwort, kein Chat-Aufruf

# 5) Ein (boeswilliger oder fehlerhafter) Router, der eine gefaehrliche Aufgabe nennt: nichts passiert
for task_type in ("OPEN_FILE", "START_PROGRAM", "SET_VOLUME", "START_TIMER", "gibtsnicht", None, ["x"]):
    client = FakeClient(); g = GuestJarvis(client)
    evil = chat_route(); evil.update(kind="TASK", task_type=task_type, parameters={"path": "C:/x.txt", "program": "steam"})
    routes.append(evil)
    executed.clear()
    assert g.process_message("Oeffne etwas")["content"] == REFUSAL, task_type
    assert executed == [] and client.calls == [], task_type

# 5b) Zweite Sicherung: wird eine Gast-Aufgabe nachtraeglich riskant, wird sie nicht ausgefuehrt
client = FakeClient(); g = GuestJarvis(client)
risk.ACTION_RISK["search_web"] = risk.CONFIRM
search = chat_route(); search.update(kind="TASK", task_type="SEARCH_WEB", parameters={"query": "Wetter"})
routes.append(search)
executed.clear()
assert g.process_message("Suche das Wetter")["content"] == REFUSAL
assert executed == [] and client.calls == []
risk.ACTION_RISK["search_web"] = original

# 6) Eingaben pruefen
client = FakeClient(); g = GuestJarvis(client)
for bad in (None, 5, ["x"], "", "   ", "\n"):
    assert "Bitte schreibe etwas" in g.process_message(bad)["content"], bad
assert "kürzer" in g.process_message("x" * (guest.MAX_MESSAGE_CHARS + 1))["content"]
assert client.calls == []                               # nichts davon kostet Geld
assert g.process_message("x" * guest.MAX_MESSAGE_CHARS)["content"] == "Gerne, Sir."

# 7) Begrenzung der Nachrichten (schuetzt deine OpenAI-Kosten)
now = [1000.0]
client = FakeClient(); g = GuestJarvis(client, clock=lambda: now[0])
for i in range(guest.RATE_LIMIT_MESSAGES):
    assert g.process_message(f"Frage {i}")["content"] == "Gerne, Sir."
n = len(client.calls)
limited = g.process_message("Eine zu viel")["content"]
assert "höchstens" in limited and str(guest.RATE_LIMIT_MESSAGES) in limited
assert len(client.calls) == n, "abgelehnte Nachrichten duerfen nichts kosten"
now[0] += guest.RATE_LIMIT_SECONDS - 1
assert "höchstens" in g.process_message("noch zu frueh")["content"]
now[0] += 2
assert g.process_message("jetzt wieder")["content"] == "Gerne, Sir."
# Ungueltige Eingaben zaehlen nicht mit
g2 = GuestJarvis(FakeClient(), clock=lambda: 5.0)
for _ in range(100):
    g2.process_message("")
assert len(g2.hits) == 0

# 8) Fehler des Modells: freundliche Meldung ohne Details
client = FakeClient(); client.error = RuntimeError("Incorrect API key sk-geheim123")
g = GuestJarvis(client)
text = g.process_message("Hallo")["content"]
assert "sk-geheim123" not in text and "RuntimeError" not in text and "nicht geklappt" in text

# 9) Nichts vom Besitzer: Hintergrundmeldungen bleiben in der Warteschlange, Einstellungen sind Standard
background_tasks.submit_result({"type": "TIMER_FINISHED", "data": {"seconds": 5, "name": "Nudeln"}})
assert g.check_background_results() == []
assert background_tasks.result_queue.qsize() == 1
background_tasks.get_results()
assert g.memory_enabled() is False
from settings_manager import SettingsManager
assert g.settings_manager.get_all() == SettingsManager.DEFAULT_SETTINGS
assert Path(g.settings_manager.file_path).resolve() != (PROJECT_DIR / "settings.json").resolve()
assert g.guest is True

assert not (FORBIDDEN_MODULES & set(sys.modules)), FORBIDDEN_MODULES & set(sys.modules)

print("ALL TESTS PASSED")
