"""Risikostufen fuer Aktionen (Mark 4, Step 4.2).

Jede Action hat genau eine Stufe:

    safe       -> Jarvis fuehrt sie sofort aus.
    confirm    -> Jarvis fragt zuerst; ausgefuehrt wird nur nach deinem "Ja".
    forbidden  -> Jarvis fuehrt sie nie aus, auch nicht auf Nachfrage.

Eine Task ist so riskant wie ihre riskanteste Action (START_PROGRAM = erst
find_program: safe, dann open_program: confirm -> die ganze Task: confirm).

Wichtig fuer die Sicherheit:
- Eine Action, die hier NICHT steht, ist forbidden. Wer eine neue Action
  baut, muss sie bewusst einstufen (Standard = verboten, nicht erlaubt).
- Die Stufe haengt nur von Action-Name und Parametern ab, nie von dem,
  was das Sprachmodell sagt ("das ist harmlos" zaehlt nicht).
- Durchgesetzt wird sie in task_executor.execute_task, also an der
  einzigen Stelle, an der Actions ausgefuehrt werden. Wer das umgehen will,
  muss den Executor umgehen.
"""

import re
from pathlib import Path

from tools.file_tool import BLOCKED_EXTENSIONS, URI_PATTERN

SAFE = "safe"
CONFIRM = "confirm"
FORBIDDEN = "forbidden"

_ORDER = {SAFE: 0, CONFIRM: 1, FORBIDDEN: 2}

ACTION_RISK = {
    # reine Auskunft / harmlos
    "get_current_time": SAFE,
    "get_current_date": SAFE,
    "calculate": SAFE,
    "get_system_info": SAFE,
    "get_running_programs": SAFE,
    "find_program": SAFE,
    "search_web": SAFE,
    "start_timer": SAFE,
    "list_timers": SAFE,
    "cancel_timer": SAFE,        # bricht nur einen eigenen Timer ab
    # schreibt nur in widgets.json, auf der Seite per Klick wieder loeschbar
    "add_calendar_event": SAFE,
    "list_calendar_events": SAFE,
    # veraendert nur die Lautstaerke, sofort wieder korrigierbar
    "set_volume": SAFE,
    # greift auf deinen Rechner zu: erst fragen
    "open_file": CONFIRM,
    "open_program": CONFIRM,
}


def _open_file_is_forbidden(path):
    """Dateien, die ohnehin nie geoeffnet werden, werden auch nicht erfragt."""
    if not isinstance(path, str) or not path.strip():
        return False         # fehlender Pfad: der Fehler kommt vom Tool selbst

    path = path.strip()

    if URI_PATTERN.match(path) or path.startswith(("\\\\", "//")):
        return True

    extension = Path(path.rstrip(" .").replace("\\", "/").split("/")[-1].rstrip(" .")).suffix.lower()

    return extension in BLOCKED_EXTENSIONS


def higher(a, b):
    """Die riskantere von zwei Stufen."""
    return a if _ORDER[a] >= _ORDER[b] else b


def action_risk(action):
    level = ACTION_RISK.get(action.name, FORBIDDEN)

    if action.name == "open_file" and _open_file_is_forbidden(
        action.parameters.get("path")
    ):
        return FORBIDDEN

    return level


def task_risk(task):
    """Hoechste Stufe aller Actions. Eine Task ohne Actions ist 'safe'."""
    level = SAFE

    for action in task.actions or []:
        level = higher(level, action_risk(action))

    return level


def describe_task(task):
    """Kurzer Text fuer die Rueckfrage: was soll passieren, womit?"""
    details = []

    for action in task.actions:
        for name, value in action.parameters.items():
            if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).strip()

                if text:
                    details.append(text[:200])

    return task.goal, details
