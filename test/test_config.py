import os
import sys
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
stub_if_missing("dotenv", load_dotenv=lambda *a, **k: None)
stub_if_missing("requests")

# Muss VOR dem ersten Import von config gesetzt sein
os.environ["JARVIS_MODEL"] = "test-modell"

import config
from config import MODEL

# 1) Umgebungsvariable ueberschreibt den Standard
assert MODEL == "test-modell", MODEL
assert config.DATABASE_URL == os.getenv("DATABASE_URL")

# 2) Der Modellname steht nur in config.py, sonst nirgends im Code
offenders = []
for path in PROJECT_DIR.rglob("*.py"):
    if path.name == "config.py" or "test" in path.parts or path.name.startswith("test_"):
        continue
    if any(part in {"venv", ".venv", "__pycache__"} for part in path.parts):
        continue
    if "gpt-" in path.read_text(encoding="utf-8", errors="ignore"):
        offenders.append(str(path.relative_to(PROJECT_DIR)))
assert offenders == [], f"Hartkodierter Modellname in: {offenders}"

# 3) Alle sechs LLM-Aufrufe benutzen config.MODEL
used_models = []


class FakeClient:
    def __init__(self, text):
        self.text = text
        self.responses = types.SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        used_models.append(kwargs["model"])
        return types.SimpleNamespace(output_text=self.text)


from router import route_message
from project_analyzer import analyze_project_message
from memory import Memory
from brain import ask_jarvis, respond_to_task
from conversation import Conversation
from task import Task
from task_registry import TaskRegistry

route_message(FakeClient("{}"), "x", TaskRegistry())
analyze_project_message(FakeClient("{}"), "x")
Memory.analyze(object.__new__(Memory), FakeClient("{}"), "x")
ask_jarvis(FakeClient("ok"), Conversation(), "mem")
task = Task("GET_TIME", "Zeit")
task.result = []
respond_to_task(FakeClient("ok"), "x", task)

assert used_models == ["test-modell"] * 5, used_models

print("ALL TESTS PASSED")
