"""Zeigt, welchen Plan das Sprachmodell fuer eine Anfrage vorschlaegt (Step 5.1).

    py show_plan.py "Starte Notepad und sag mir die Uhrzeit"

Es wird NICHTS ausgefuehrt: nur ein Plan erzeugt, geprueft und angezeigt.
Der Aufruf kostet eine normale Modell-Anfrage.
"""

import sys

from openai import OpenAI

from config import OPENAI_TIMEOUT
from plan import plan_risk
from planner import create_plan
from risk import describe_task
from plan import prepare_step
from task_registry import TaskRegistry
from tasks import register_all_tasks

RISK_TEXT = {
    "safe": "sicher (laeuft ohne Rueckfrage)",
    "confirm": "braucht Bestaetigung",
    "forbidden": "VERBOTEN (wuerde nicht ausgefuehrt)",
}


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Benutzung: py show_plan.py "Deine Anfrage"')
        return

    registry = TaskRegistry()
    register_all_tasks(registry)

    plan, reason = create_plan(OpenAI(timeout=OPENAI_TIMEOUT), sys.argv[1], registry)

    if plan is None:
        print(f"Kein Plan: {reason}")
        return

    print(f"Ziel: {plan.goal}")

    for number, step in enumerate(plan.steps, start=1):
        goal, _ = describe_task(prepare_step(registry, step))
        print(f"  {number}. {step.task_type}: {goal}")

        for name, value in step.parameters.items():
            shown = f"Ergebnis von Schritt {value['from_step']}" if isinstance(value, dict) else value
            print(f"       {name} = {shown}")

    print(f"Risiko des Plans: {RISK_TEXT[plan_risk(plan, registry)]}")
    print("(Nichts wurde ausgefuehrt.)")


main()
