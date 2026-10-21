"""Plan erzeugen, anzeigen, nach deinem Ja ausfuehren (Step 5.2, vorerst nur im Terminal).

    py run_plan.py "Starte Notepad und sag mir die Uhrzeit"

Ablauf: Plan vom Modell holen und pruefen, anzeigen, fragen. Nur nach "ja" laeuft
er. Schritte mit Rueckfrage-Stufe (Programm starten, Datei oeffnen) sind mit
deinem "ja" freigegeben, sonst laeuft nichts. Jeder Schritt steht danach im
Aktionsprotokoll (Settings > Activity).

Der Anschluss an den normalen Chat und das Web kommt in Step 5.3.
"""

import sys

from openai import OpenAI

import action_log
from config import OPENAI_TIMEOUT
from plan import plan_risk, prepare_step
from plan_executor import confirmable_steps, execute_plan
from planner import create_plan
from risk import describe_task
from task_registry import TaskRegistry
from tasks import register_all_tasks

RISK_TEXT = {
    "safe": "sicher (keine Rueckfrage noetig)",
    "confirm": "enthaelt Schritte mit Rueckfrage",
    "forbidden": "VERBOTEN (wird nicht ausgefuehrt)",
}


def show_plan(plan, registry, confirmable):
    print(f"Ziel: {plan.goal}")

    for number, step in enumerate(plan.steps, start=1):
        goal, _ = describe_task(prepare_step(registry, step))
        mark = "  <- braucht dein Ja" if number in confirmable else ""
        print(f"  {number}. {step.task_type}: {goal}{mark}")

        for name, value in step.parameters.items():
            shown = f"Ergebnis von Schritt {value['from_step']}" if isinstance(value, dict) else value
            print(f"       {name} = {shown}")

    print(f"Risiko des Plans: {RISK_TEXT[plan_risk(plan, registry)]}")


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Benutzung: py run_plan.py "Deine Anfrage"')
        return

    registry = TaskRegistry()
    register_all_tasks(registry)
    action_log.enable()

    plan, reason = create_plan(OpenAI(timeout=OPENAI_TIMEOUT), sys.argv[1], registry)

    if plan is None:
        print(f"Kein Plan: {reason}")
        return

    confirmable = confirmable_steps(plan, registry)
    show_plan(plan, registry, confirmable)

    if input("Ausfuehren? (ja/nein) ").strip().lower() not in ("ja", "j", "yes", "y"):
        print("Abgebrochen, nichts wurde ausgefuehrt.")
        return

    run = execute_plan(plan, registry, approved=set(confirmable))

    for step_run in run.steps:
        detail = step_run.error or step_run.value
        print(f"  {step_run.number}. {step_run.step.task_type}: {step_run.status}"
              + (f" ({detail})" if detail not in (None, "") else ""))

    print(f"Ergebnis: {run.status}" + (f" - {run.error}" if run.error else ""))


main()
