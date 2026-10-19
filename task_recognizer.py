import json
from config import MODEL
from llm_json import parse_llm_json


def recognize_task(client, message, task_registry):
    task_information = []

    for task in task_registry.get_all():
        task_data = {
            "task_type": task.task_type,
            "goal": task.goal,
            "actions": []
        }

        for action in task.actions:
            task_data["actions"].append({
                "name": action.name,
                "parameters": action.parameters
            })

        task_information.append(task_data)
    response = client.responses.create(
        model=MODEL,
        input=f"""
Analyze the user's message and determine whetever it matches a known task

Available tasks:

{json.dumps(task_information, ensure_ascii=False, indent=2)}

User message:
"{message}"

If the matched task has parameters, extract their values from the user's message and return them under "parameters".

Return ONLY valid JSON

{{
    "task_type": "GET_TIME"
}}

If the message does not match any known task:

{{
    "task_type": null
}}

Do not include any other text.
"""
    )

    recognized = parse_llm_json(
        response.output_text,
        {"task_type": None}
    )

    if recognized["task_type"] is not None and task_registry.get(
        recognized["task_type"]
    ) is None:
        return {"task_type": None}

    return recognized


def is_known_task(recognized):
    return recognized["task_type"] is not None