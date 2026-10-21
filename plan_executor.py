"""Plan ausfuehren (Mark 4, Step 5.2).

execute_plan() arbeitet einen geprueften Plan (plan.py) Schritt fuer Schritt ab.
Jeder Schritt laeuft ueber task_executor.execute_task, also durch dieselben
Risikostufen (risk.py) und dasselbe Aktionsprotokoll wie jede einzelne Aufgabe.

Regeln:

Grenzen
- Hoechstens max_steps Schritte (Standard: plan.MAX_STEPS). Ein laengerer Plan
  wird gar nicht erst begonnen.
- Hoechstens max_seconds Gesamtdauer (Standard 120 s), geprueft vor jedem Schritt.
- Abbruch: should_abort() wird vor jedem Schritt gefragt. Gibt es True zurueck
  (oder wirft einen Fehler), laeuft kein weiterer Schritt.
- Ein fehlgeschlagener Schritt beendet den Plan. Es wird nie "trotzdem weitergemacht".

Ergebnis eines Schritts fuer den naechsten ({"from_step": n})
- Weitergegeben wird nur ein einfacher Wert: Text (hoechstens 500 Zeichen, ohne
  Steuer-/Unsichtbar-Zeichen) oder eine Zahl. Eine Liste oder ein Objekt (z.B. die
  Treffer der Websuche) wird NIE als Parameter weitergegeben. Damit kann Text aus
  dem Internet nicht zum Dateipfad oder Programmnamen eines spaeteren Schritts werden.

Risiko (Stufen aus 4.2)
- Verbotenes laeuft nie.
- Ein Schritt mit Stufe "confirm" laeuft nur, wenn seine Nummer in approved steht
  UND alle seine Parameter schon vor dem Start feststanden. Ein Wert, der erst
  aus einem frueheren Schritt kommt, wurde dem Nutzer nie gezeigt und ist deshalb
  durch keine Freigabe gedeckt: Ein solcher Plan wird gar nicht erst begonnen.
- Was sich vor dem Start entscheiden laesst (verboten, nicht freigegeben), wird
  vor dem ersten Schritt entschieden: Es laeuft dann gar nichts, statt halb.
- Zusaetzlich prueft der Executor jeden Schritt unmittelbar vor der Ausfuehrung
  mit den dann bekannten Werten noch einmal (zweite Sicherung).
"""

import math
import time

from untrusted import clean_text
import plan as plan_module
import risk
from plan import MAX_STEPS, MAX_TEXT, is_step_reference, prepare_step
from task_executor import execute_task

MAX_SECONDS = 120

# Status eines Plans
COMPLETED = "COMPLETED"
FAILED = "FAILED"
ABORTED = "ABORTED"
BLOCKED = "BLOCKED"

# Status eines Schritts (zusaetzlich die Task-Status COMPLETED / FAILED / BLOCKED)
SKIPPED = "SKIPPED"


class StepRun:
    def __init__(self, number, step):
        self.number = number
        self.step = step
        self.status = "PENDING"
        self.task = None
        self.value = None       # der Wert, den spaetere Schritte per from_step bekommen
        self.value_error = None  # warum dieser Schritt keinen weitergebbaren Wert hat
        self.error = None


class PlanRun:
    def __init__(self, plan):
        self.plan = plan
        self.status = "PENDING"
        self.error = None
        self.steps = [StepRun(n, s) for n, s in enumerate(plan.steps, start=1)]

    def completed_steps(self):
        return [s for s in self.steps if s.status == "COMPLETED"]


def references(step):
    return [v for v in step.parameters.values() if is_step_reference(v)]


def confirmable_steps(plan, task_registry):
    """Nummern der Schritte, die der Nutzer vorab freigeben kann (5.3 zeigt sie ihm).

    Das sind die Schritte der Stufe confirm, deren Parameter schon feststehen.
    """
    numbers = []

    for number, step in enumerate(plan.steps, start=1):
        if references(step):
            continue

        if plan_module.step_risk(task_registry, step) == risk.CONFIRM:
            numbers.append(number)

    return numbers


def step_value(task):
    """Der Wert, den ein Schritt weitergibt (oder ValueError, wenn er das nicht darf)."""
    results = task.result if isinstance(task.result, list) else []

    if not results:
        raise ValueError("der Schritt hat kein Ergebnis geliefert")

    last = results[-1]
    data = getattr(last, "data", last)

    if isinstance(data, bool) or data is None:
        raise ValueError("das Ergebnis ist kein Text und keine Zahl")

    if isinstance(data, (int, float)):
        if isinstance(data, float) and not math.isfinite(data):
            raise ValueError("das Ergebnis ist keine gueltige Zahl")

        return data

    if isinstance(data, str):
        text = data.strip()

        if not text:
            raise ValueError("das Ergebnis ist leer")

        if len(text) > MAX_TEXT or clean_text(text, MAX_TEXT + 1) != text:
            raise ValueError("das Ergebnis ist zu lang oder enthaelt unzulaessige Zeichen")

        return text

    raise ValueError(
        f"das Ergebnis ist {type(data).__name__}, nur Text oder Zahlen werden weitergegeben"
    )


def find_blocker(plan, task_registry, approved):
    """Was spricht VOR dem Start gegen diesen Plan? (Schrittnummer, Schritt-Fehler, Meldung) oder None.

    Vorab entscheiden, was sich vorab entscheiden laesst: lieber gar nichts
    als halb. Wird auch von Jarvis benutzt, bevor ein Plan angezeigt wird.
    """
    for number, step in enumerate(plan.steps, start=1):
        level = plan_module.step_risk(task_registry, step)

        # Ein Schritt mit Verweis (Wert noch unbekannt) kann hoechstens "confirm" sein,
        # und das laesst sich nie vorab freigeben: Er wird gar nicht erst begonnen.
        if references(step) and level == risk.CONFIRM:
            return (
                number,
                "Dieser Schritt braucht eine Bestaetigung, die vorab nicht moeglich ist.",
                f"Schritt {number} ({step.task_type}) braucht eine Bestaetigung, "
                "aber sein Wert steht erst waehrend der Ausfuehrung fest und kann dir vorher "
                "nicht gezeigt werden. Es wurde nichts ausgefuehrt.",
            )

        if references(step):
            continue

        if level == risk.FORBIDDEN:
            return (
                number,
                "Diese Aktion ist verboten.",
                f"Schritt {number} ({step.task_type}) ist verboten. Es wurde nichts ausgefuehrt.",
            )

        if level == risk.CONFIRM and number not in approved:
            return (
                number,
                "Dieser Schritt braucht eine Bestaetigung.",
                f"Schritt {number} ({step.task_type}) braucht eine Bestaetigung. "
                "Es wurde nichts ausgefuehrt.",
            )

    return None


def _finish(run, status, error=None):
    run.status = status
    run.error = error

    for step_run in run.steps:
        if step_run.status == "PENDING":
            step_run.status = SKIPPED

    return run


def execute_plan(plan, task_registry, approved=(), should_abort=None,
                 max_steps=MAX_STEPS, max_seconds=MAX_SECONDS, clock=time.monotonic):
    """Fuehrt den Plan aus und gibt einen PlanRun zurueck. Wirft keine Fehler der Schritte."""
    run = PlanRun(plan)
    approved = set(approved)

    if len(plan.steps) > max_steps:
        return _finish(
            run, BLOCKED,
            f"Der Plan hat {len(plan.steps)} Schritte, erlaubt sind hoechstens {max_steps}."
        )

    # Auch ein von Hand gebauter Plan geht noch einmal durch das Tor: Es gibt keinen
    # Weg, einen ungeprueften Plan auszufuehren.
    try:
        plan_module.parse_plan(plan.to_dict(), task_registry)
    except plan_module.PlanError as error:
        return _finish(run, BLOCKED, f"Ungueltiger Plan: {error}")

    blocker = find_blocker(plan, task_registry, approved)

    if blocker is not None:
        number, step_error, message = blocker
        run.steps[number - 1].status = BLOCKED
        run.steps[number - 1].error = step_error

        return _finish(run, BLOCKED, message)

    started = clock()

    for step_run in run.steps:
        step = step_run.step

        try:
            if should_abort is not None and should_abort():
                return _finish(run, ABORTED, "Der Plan wurde abgebrochen.")
        except Exception:
            return _finish(run, ABORTED, "Der Plan wurde abgebrochen.")

        if clock() - started > max_seconds:
            return _finish(run, ABORTED, f"Zeitlimit von {max_seconds} Sekunden erreicht.")

        step_run.status = "RUNNING"

        try:
            parameters = {}

            for name, value in step.parameters.items():
                if not is_step_reference(value):
                    parameters[name] = value
                    continue

                number = value["from_step"]
                source = run.steps[number - 1]

                if source.value_error is not None:
                    raise ValueError(
                        f"Das Ergebnis von Schritt {number} kann nicht weitergegeben werden: "
                        f"{source.value_error}."
                    )

                parameters[name] = source.value

            task = prepare_step(task_registry, plan_module.Step(step.task_type, parameters))

            if task is None:
                raise ValueError("unbekannte Aufgabe")

            has_reference = bool(references(step))
            confirmed = step_run.number in approved and not has_reference

            execute_task(task, confirmed=confirmed)
            step_run.task = task
            step_run.status = task.status
            step_run.error = task.error

            if task.status != "COMPLETED":
                return _finish(
                    run,
                    BLOCKED if task.status == "BLOCKED" else FAILED,
                    f"Schritt {step_run.number} ({step.task_type}): {task.error}",
                )

            # Der Wert fuer spaetere Schritte. Hat der Schritt keinen einfachen Wert
            # (Liste, Objekt), ist das nur dann ein Problem, wenn ihn jemand braucht.
            try:
                step_run.value = step_value(task)
            except ValueError as error:
                step_run.value_error = str(error)
        except Exception as error:
            step_run.status = FAILED
            step_run.error = str(error)

            return _finish(run, FAILED, f"Schritt {step_run.number} ({step.task_type}): {error}")

    return _finish(run, COMPLETED)
