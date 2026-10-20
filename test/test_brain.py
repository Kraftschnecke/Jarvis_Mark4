import json
import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

for name, attrs in (("dotenv", {"load_dotenv": lambda *a, **k: None}),):
    try:
        __import__(name)
    except ImportError:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m

import brain
import action_executor
from action import Action
from task import Task
from tools.tool_result import ToolResult


class FakeConversation:
    def __init__(self, messages):
        self.messages = messages

    def get_messages(self):
        return self.messages


class FakeClient:
    def __init__(self):
        self.calls = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(output_text="ok")


# 1) Memory und Projektkontext stehen in instructions, nicht im Gespraech
client = FakeClient()
conv = FakeConversation([
    {"role": "user", "content": "Hallo"},
    {"role": "assistant", "content": "Guten Tag, Sir."},
    {"role": "user", "content": "Was ist 2+2?"},
])
brain.ask_jarvis(client, conv, "preference: Lieblingstier = Axolotl", "## Goal\nSocken")
call = client.calls[0]
assert "Axolotl" in call["instructions"] and "Socken" in call["instructions"]
assert call["instructions"].startswith(brain.JARVIS_PERSONALITY)
assert isinstance(call["input"], list)
assert [m["role"] for m in call["input"]] == ["user", "assistant", "user"]
assert "Axolotl" not in json.dumps(call["input"])
assert "User memory" not in json.dumps(call["input"])

# 2) Ohne Projektkontext / Memory kein leerer Platzhalter
text = brain.build_instructions("", None)
assert text == brain.JARVIS_PERSONALITY, text
assert "None" not in brain.build_instructions("x", None)

# 3) Timer liefert ein ToolResult (kein Thread), und respond_to_task kann es serialisieren
action_executor.start_timer = lambda seconds: object()
result = action_executor.execute_action(
    Action("start_timer", {"value": 10, "unit": "seconds"})
)
assert isinstance(result, ToolResult) and result.success
assert result.data == {"seconds": 10}

task = Task("START_TIMER", "Timer")
task.status = "COMPLETED"
task.result = [ToolResult(True, data={"obj": object()}), object()]
client = FakeClient()
brain.respond_to_task(client, "Timer", task)  # darf nicht mit TypeError abbrechen
assert client.calls

# 4) Verlauf begrenzen (Step 2.6)
def chat(n):
    """n Nachrichten: user0, assistant1, user2, ... (endet bei ungeradem n mit user)."""
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
        for i in range(n)
    ]


# kurzer Verlauf und limit 0 -> unveraendert
assert brain.limit_history(chat(5), 20) == chat(5)
assert brain.limit_history(chat(50), 0) == chat(50)
assert brain.limit_history(chat(50), -1) == chat(50)

# langer Verlauf: die letzten N, Ausschnitt beginnt mit "user"
history = chat(31)                               # user0 ... user30
cut = brain.limit_history(history, 20)
assert cut[-1] == history[-1]                    # die aktuelle Frage ist immer dabei
assert cut[0]["role"] == "user"
assert len(cut) <= 20 and cut == history[-len(cut):]
assert cut[0]["content"] == "m12"                # 31 - 20 = 11 waere assistant -> weg

# Ausschnitt beginnt schon mit user -> nichts wird zusaetzlich verworfen
cut = brain.limit_history(chat(30)[:-1] + [{"role": "user", "content": "x"}], 20)
assert len(cut) == 20 or cut[0]["role"] == "user"

# Die Original-Liste bleibt unveraendert (die Oberflaeche zeigt alles)
original = chat(31)
brain.limit_history(original, 20)
assert original == chat(31)

# Ende-zu-Ende: ask_jarvis schickt nur das Fenster
import config
config.HISTORY_LIMIT = 10
client = FakeClient()
brain.ask_jarvis(client, FakeConversation(chat(41)), "", None)
sent = client.calls[-1]["input"]
assert len(sent) <= 10 and sent[-1]["content"] == "m40" and sent[0]["role"] == "user"
config.HISTORY_LIMIT = 0
client = FakeClient()
brain.ask_jarvis(client, FakeConversation(chat(41)), "", None)
assert len(client.calls[-1]["input"]) == 41

# 5) Anrede kommt in beide Prompts (Chat und Aufgaben-Antwort)
import personality
personality.set_address("Chef")
client = FakeClient()
brain.ask_jarvis(client, FakeConversation([{"role": "user", "content": "Hi"}]), "", None)
assert "address me as Chef" in client.calls[-1]["instructions"]
task = Task("GET_TIME", "Zeit")
task.status = "COMPLETED"
task.result = []
client = FakeClient()
brain.respond_to_task(client, "Zeit?", task)
assert "address me as Chef" in client.calls[-1]["instructions"]
assert "address the user as Chef when appropriate" in client.calls[-1]["input"]
assert "Sir" not in client.calls[-1]["input"] and "Sir" not in client.calls[-1]["instructions"]
personality.set_address("Sir")

print("ALL TESTS PASSED")
