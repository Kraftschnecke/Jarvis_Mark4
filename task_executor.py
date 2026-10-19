from action_executor import execute_action
from tools.tool_result import ToolResult
import copy


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


def execute_task(task):
    results = []
    action = None

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


def execute_registered_task(registry, task_type, parameters=None):
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

    execute_task(task)

    return task
