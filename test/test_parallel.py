import contextlib
import io
import sys
import threading
import time
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


stub_if_missing("openai", OpenAI=object)
stub_if_missing("psycopg")
stub_if_missing("psutil")
stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
stub_if_missing("requests")
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

from parallel import Job
import jarvis as jarvis_module
from jarvis import Jarvis
from workspace import Workspace
from router import chat_route
from memory import Memory

# ---------------------------------------------------------------------
# 1) Job
# ---------------------------------------------------------------------
main_thread = threading.get_ident()
job = Job(lambda a, b: (a + b, threading.get_ident()), 2, 3)
value, thread_id = job.result()
assert value == 5 and thread_id != main_thread  # lief in einem anderen Thread
assert job._thread.daemon is True               # blockiert Strg+C / Programmende nicht


def boom():
    raise ValueError("kaputt")


job = Job(boom)
job.wait()  # wait() wirft nie
try:
    job.result()
    raise AssertionError("Fehler ging verloren")
except ValueError as error:
    assert "kaputt" in str(error)

slow = Job(time.sleep, 0.2)
slow.wait()
assert not slow._thread.is_alive()  # nach wait() ist der Thread wirklich fertig

# ---------------------------------------------------------------------
# 2) Jarvis.process_normal_message
# ---------------------------------------------------------------------
PROJECT = (7, "Testprojekt")
CONVERSATION = (5, "Unterhaltung")


class World:
    """Alles, was die Fakes gemeinsam sehen (Memory-Text, project.md, Reihenfolge)."""

    def __init__(self):
        self.memory_text = "Memory: alt"
        self.project_text = "Projekt: alt"
        self.events = []          # Reihenfolge der Ereignisse
        self.saved = []           # save_message-Aufrufe
        self.ask_args = None
        self.memory_done = False
        self.project_done = False
        self.barrier = None       # wenn gesetzt: alle drei muessen gleichzeitig laufen
        self.delay = 0.0
        self.save_delay = 0.0     # bremst nur den Hauptthread, die Jobs sind dann schneller
        self.memory_error = None
        self.project_error = None
        self.project_result = None
        self.ask_error = None
        self.calls = {"memory": 0, "project": 0}


def make_jarvis(world, project=True, memory_enabled=True):
    j = object.__new__(Jarvis)
    j.client = "client"
    j.workspace = Workspace()
    j.pending_project_confirmation = None
    j.task_registry = None
    j.settings_manager = types.SimpleNamespace(
        get=lambda category, key, default=None: (
            memory_enabled if (category, key) == ("memory", "enabled") else default
        )
    )

    if project:
        j.project_state.set_project(PROJECT)

    j.project_state.set_conversation(CONVERSATION)

    def memory_process(client, message):
        world.calls["memory"] += 1
        world.events.append("memory-start")
        if world.barrier:
            world.barrier.wait()
        time.sleep(world.delay)
        if world.memory_error:
            raise world.memory_error
        world.memory_text = "Memory: neu (aus dieser Nachricht)"
        world.memory_done = True
        world.events.append("memory-ende")

    j.memory = types.SimpleNamespace(
        process=memory_process,
        get_context=lambda: world.memory_text
    )

    def project_job(message):
        world.calls["project"] += 1
        world.events.append("projekt-start")
        if world.barrier:
            world.barrier.wait()
        time.sleep(world.delay)
        if world.project_error:
            raise world.project_error
        world.project_text = "Projekt: neu (aus dieser Nachricht)"
        world.project_done = True
        world.events.append("projekt-ende")
        return world.project_result

    j.process_project_context = project_job

    def fake_ask(client, conversation, memory, project_context=None):
        world.events.append("ask-start")
        world.ask_args = (memory, project_context)
        if world.barrier:
            world.barrier.wait()
        if world.ask_error:
            raise world.ask_error
        world.events.append("ask-ende")
        return "Antwort"

    jarvis_module.ask_jarvis = fake_ask
    jarvis_module.get_project_context = lambda project_id: world.project_text
    def save(cid, role, text):
        if role == "user":
            time.sleep(world.save_delay)
        world.saved.append((cid, role, text))
        world.events.append(f"save-{role}")

    jarvis_module.save_message = save
    jarvis_module.route_message = lambda *a, **k: chat_route()
    return j


def run(j, message="Hallo"):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        result = j.process_message(message)
    return result, buffer.getvalue()


# a) Gleichzeitigkeit: Memory, Projekt und Antwort warten aufeinander.
#    Liefen sie nacheinander, bliebe die Barriere stehen und der Test scheitert.
world = World()
world.barrier = threading.Barrier(3, timeout=5)
j = make_jarvis(world)
result, _ = run(j)
assert result == {"status": "response", "content": "Antwort"}, result
assert not world.barrier.broken
assert world.memory_done and world.project_done

# b) Momentaufnahme: die Antwort sieht Memory und project.md VOR dieser Nachricht
assert world.ask_args == ("Memory: alt", "Projekt: alt"), world.ask_args

# b2) Auch wenn die Jobs viel schneller fertig sind als der Hauptthread, sieht die
#     Antwort den alten Stand (die Momentaufnahme entsteht vor dem Start der Jobs)
world = World()
world.save_delay = 0.3
j = make_jarvis(world)
run(j)
assert world.memory_done and world.project_done
assert world.ask_args == ("Memory: alt", "Projekt: alt"), world.ask_args

# c) Nach process_message ist nichts mehr im Hintergrund unterwegs (auch nicht bei Verzoegerung)
world = World()
world.delay = 0.3
j = make_jarvis(world)
run(j)
assert world.memory_done and world.project_done

# d) ... auch dann nicht, wenn die Antwort scheitert
world = World()
world.delay = 0.3
world.ask_error = RuntimeError("Netzwerk weg")
j = make_jarvis(world)
result, _ = run(j)
assert "RuntimeError" in result["content"] and "Fehler" in result["content"]
assert world.memory_done and world.project_done
assert j.pending_project_confirmation is None

# e) Reihenfolge im Verlauf: Nutzer-Nachricht kommt vor der Antwort in die DB,
#    und zwar bevor die Antwort entsteht
world = World()
j = make_jarvis(world)
run(j, "Frage")
assert world.saved == [(5, "user", "Frage"), (5, "assistant", "Antwort")], world.saved
assert world.events.index("save-user") < world.events.index("ask-ende")
assert world.events.index("save-assistant") > world.events.index("ask-ende")
assert [m["role"] for m in j.conversation.get_messages()] == ["user", "assistant"]

# f) Fehler in Memory oder Projekt-Pruefung: Antwort kommt trotzdem
world = World()
world.memory_error = RuntimeError("Neon nicht erreichbar")
j = make_jarvis(world)
result, output = run(j)
assert result == {"status": "response", "content": "Antwort"}
assert "[memory]" in output and "Neon nicht erreichbar" in output

world = World()
world.project_error = RuntimeError("Modell-Fehler")
j = make_jarvis(world)
result, output = run(j)
assert result == {"status": "response", "content": "Antwort"}  # ohne Rueckfrage
assert "[projekt]" in output and "Modell-Fehler" in output
assert j.pending_project_confirmation is None

# g) Rueckfrage wird angehaengt und gemerkt, bleibt aber aus dem Verlauf
world = World()
world.project_result = {
    "status": "confirmation_required",
    "section": "Decisions",
    "content": "Wir nutzen PostgreSQL"
}
j = make_jarvis(world)
result, _ = run(j)
assert result["content"].startswith("Antwort\n\n") and "Decisions" in result["content"]
assert j.pending_project_confirmation == {
    "project_id": 7, "section": "Decisions", "content": "Wir nutzen PostgreSQL"
}
assert j.conversation.get_messages()[-1]["content"] == "Antwort"
assert world.saved[-1] == (5, "assistant", "Antwort")

# Eine folgende Nachricht ohne Rueckfrage macht die alte ungueltig
world.project_result = None
run(j, "naechste")
assert j.pending_project_confirmation is None

# h) Ohne Projekt gibt es keinen Projekt-Job, bei ausgeschaltetem Memory keinen Memory-Job
world = World()
j = make_jarvis(world, project=False)
run(j)
assert world.calls == {"memory": 1, "project": 0}

world = World()
j = make_jarvis(world, memory_enabled=False)
result, _ = run(j)
assert world.calls == {"memory": 0, "project": 1}
assert result["content"] == "Antwort"
assert world.ask_args[0] == Memory.EMPTY_CONTEXT  # Memory aus: nichts genutzt

print("ALL TESTS PASSED")
