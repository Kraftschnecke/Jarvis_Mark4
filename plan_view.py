"""Plan fuer den Nutzer lesbar machen (Mark 4, Step 5.3).

Aus einem geprueften Plan wird die Ansicht, die Jarvis dir VOR dem Start zeigt:
Ziel, nummerierte Schritte, welche Schritte dein Ja brauchen, und Gesamtrisiko.
Nur Anzeige, keine Logik: Was ausgefuehrt wird, entscheidet plan_executor.
"""

import re

import risk
from plan import is_step_reference, plan_risk, prepare_step

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def view_step(task_registry, number, step, needs_confirmation):
    task = prepare_step(task_registry, step)
    title, _ = risk.describe_task(task)
    details = []

    for name, value in step.parameters.items():
        if is_step_reference(value):
            details.append(f"{name}: Ergebnis von Schritt {value['from_step']}")
        else:
            details.append(_CONTROL.sub(" ", str(value))[:200])

    return {
        "number": number,
        "task_type": step.task_type,
        "title": title,
        "details": details,
        "needs_confirmation": needs_confirmation,
    }


def view_plan(plan, task_registry, approvable):
    return {
        "goal": plan.goal,
        "risk": plan_risk(plan, task_registry),
        "steps": [
            view_step(task_registry, number, step, number in approvable)
            for number, step in enumerate(plan.steps, start=1)
        ],
    }


def plan_text(view, address):
    """Text fuer Chat und Terminal (** fett, ` Code, wie die Oberflaeche es darstellt)."""
    lines = [f"{address}, so würde ich das angehen:", "", f"**{view['goal']}**", ""]

    for step in view["steps"]:
        line = f"{step['number']}. {step['title']}"

        for detail in step["details"]:
            line += " `" + detail.replace("`", "'") + "`"

        if step["needs_confirmation"]:
            line += "  (braucht dein Ja)"

        lines.append(line)

    lines += ["", "Soll ich den Plan ausführen? Antworte mit **ja** oder **nein**."]

    return "\n".join(lines)
