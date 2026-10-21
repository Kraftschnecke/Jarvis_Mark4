import sys
import types
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# pycaw gibt es nur unter Windows. Auf anderen Systemen stubben,
# damit der Test trotzdem laeuft.
try:
    import pycaw.pycaw  # noqa: F401
except ImportError:
    pycaw = types.ModuleType("pycaw")
    pycaw_inner = types.ModuleType("pycaw.pycaw")
    pycaw_inner.AudioUtilities = None
    pycaw_inner.IAudioEndpointVolume = None
    sys.modules["pycaw"] = pycaw
    sys.modules["pycaw.pycaw"] = pycaw_inner

import task_executor
from task import Task
from action import Action
from task_registry import TaskRegistry
from tools.tool_result import ToolResult


def build_start_program_task():
    task = Task("START_PROGRAM", "Ein Programm starten")
    task.add_action(Action("find_program", {"program": None}))
    task.add_action(Action("open_program", {"path": {"source": "previous_result"}}))
    return task


def fake_execute_action(calls):
    def execute(action):
        calls.append((action.name, dict(action.parameters)))
        if action.name == "find_program":
            return ToolResult(success=True, data=r"C:\Windows\notepad.exe")
        if action.name == "open_program":
            return ToolResult(success=True, data=action.parameters["path"])
        raise ValueError(action.name)
    return execute


# 1) Der Pfad (nicht das ToolResult) landet bei open_program
calls = []
task_executor.execute_action = fake_execute_action(calls)
registry = TaskRegistry()
registry.register(build_start_program_task())

task = task_executor.execute_registered_task(
    registry, "START_PROGRAM", {"program": "notepad"}, confirmed=True
)
assert task.status == "COMPLETED", task.error
assert calls[0] == ("find_program", {"program": "notepad"})
assert calls[1] == ("open_program", {"path": r"C:\Windows\notepad.exe"}), calls[1]
assert isinstance(calls[1][1]["path"], str)

# 2) Das LLM darf den Verweis auf das vorherige Ergebnis nicht ueberschreiben
calls.clear()
task = task_executor.execute_registered_task(
    registry, "START_PROGRAM", {"program": "notepad", "path": r"C:\evil.exe"},
    confirmed=True
)
assert calls[1][1]["path"] == r"C:\Windows\notepad.exe", calls[1]

# 3) Das Original in der Registry bleibt unveraendert (deepcopy)
original = registry.get("START_PROGRAM").actions[1].parameters["path"]
assert original == {"source": "previous_result"}

# 4) Schlaegt find_program fehl, wird open_program nicht ausgefuehrt
calls.clear()
def failing(action):
    calls.append(action.name)
    return ToolResult(success=False, error="Program not found: xyz")
task_executor.execute_action = failing
task = task_executor.execute_registered_task(registry, "START_PROGRAM", {"program": "xyz"}, confirmed=True)
assert task.status == "FAILED" and task.error == "Program not found: xyz"
assert calls == ["find_program"]

print("ALL TESTS PASSED")
