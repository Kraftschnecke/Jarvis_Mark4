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

print("ALL TESTS PASSED")
