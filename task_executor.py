from action_executor import execute_action
from tools.tool_result import ToolResult
import copy

import action_log
import risk


def is_result_reference(definition):
    """True, wenn ein Parameter auf das Ergebnis der vorherigen Action zeigt."""
    return (
        isinstance(definition, dict)
        and definition.get("source") == "previous_result"
    )


def resolve_action_parameters(action, previous_result):
    if previous_result is None:
        return

    # Tools liefern ein ToolResult. Die naechste Action braucht nur den
    # eigentlichen Wert (z.B. den Programmpfad), nicht das ganze Objekt.
    if isinstance(previous_result, ToolResult):
        previous_result = previous_result.data

    for parameter, definition in action.parameters.items():
        if is_result_reference(definition):
            action.parameters[parameter] = previous_result


def block_reason(task, confirmed):
    """Warum diese Task NICHT laufen darf (oder None, wenn sie darf)."""
    level = risk.task_risk(task)

    if level == risk.FORBIDDEN:
        return "Diese Aktion ist verboten."

    if level == risk.CONFIRM and not confirmed:
        return "Diese Aktion braucht eine Bestaetigung."

    return None


def execute_task(task, confirmed=False):
    """Fuehrt die Task aus (siehe _execute_task) und haelt das Ergebnis im Aktionsprotokoll fest."""
    results = _execute_task(task, confirmed)

    if task.status == "BLOCKED":
        decision = "blocked"
    elif confirmed and risk.task_risk(task) == risk.CONFIRM:
        decision = "confirmed"
    else:
        decision = "auto"

    action_log.record(task, decision)

    return results


def _execute_task(task, confirmed=False):
    """Fuehrt die Actions der Task aus, aber nur, wenn ihre Risikostufe es erlaubt.

    confirmed=True heisst: der Nutzer hat diese Task ausdruecklich bestaetigt.
    Verbotenes laeuft auch dann nie. Geprueft wird VOR der ersten Action, damit
    nie eine Task halb ausgefuehrt wird.
    """
    results = []
    action = None

    reason = block_reason(task, confirmed)

    if reason is not None:
        task.status = "BLOCKED"
        task.result = results
        task.error = reason

        return results

    try:
        for action in task.actions:
            action.status = "RUNNING"

            previous_result = results[-1] if results else None
            resolve_action_parameters(action, previous_result)

            result = execute_action(action)

            if hasattr(result, "success") and not result.success:
                raise RuntimeError(result.error)

            action.result = result

            action.status = "COMPLETED"

            results.append(result)

    except Exception as error:
        if action is not None:
            action.status = "FAILED"
            action.result = str(error)

        task.status = "FAILED"
        task.result = results
        task.error = str(error)

        return results

    task.result = results
    task.status = "COMPLETED"

    return results


def prepare_registered_task(registry, task_type, parameters=None):
    """Baut eine Kopie der registrierten Task mit den Parametern, fuehrt sie NICHT aus."""
    registered_task = registry.get(task_type)

    if registered_task is None:
        return None

    task = copy.deepcopy(registered_task)

    if parameters is not None:
        for action in task.actions:
            for key, value in parameters.items():
                if key not in action.parameters:
                    continue

                # Parameter, die aus der vorherigen Action kommen, darf
                # das LLM nicht ueberschreiben.
                if is_result_reference(action.parameters[key]):
                    continue

                action.parameters[key] = value

    return task


def execute_registered_task(registry, task_type, parameters=None, confirmed=False):
    task = prepare_registered_task(registry, task_type, parameters)

    if task is None:
        return None

    execute_task(task, confirmed=confirmed)

    return task
