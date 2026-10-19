from config import MODEL
from llm_json import parse_llm_json
from project_context import add_to_project_section

VALID_SECTIONS = {
    "Goal", "Description", "Current Status", "Important Information",
    "Decisions", "Progress", "Open Topics", "Next Steps"
}

DEFAULT_ANALYSIS = {
    "relevant": False,
    "section": None,
    "content": None,
    "requires_confirmation": False
}


def analyze_project_message(client, message):
    response = client.responses.create(
        model=MODEL,
        input=f"""
Analyze this user message:

"{message}"
Determine whether it contains information that is relevant to the user´s current project.

If it contains relevant project information, identify the appropriate category.

Possible categories:
- Goal
- Description
- Current Status
- Important Information
- Decisions
- Progress
- Open Topics
- Next Steps

Return ONLY valid JSON in this exact format:

{{
    "relevant": true,
    "section": "Progress",
    "content": "Datenbankanbindung fertig",
    "requires_confirmation": false
}}

If the message does not contain relevant project information, return:

{{
    "relevant": false,
    "section": null,
    "content": null,
    "requires_confirmation": false
}}

Set "requires_confirmation" to true when:
- the information changes or creates a project Goal
- the information represents a project Decision
- the user is only suggesting, considering, or discussing a possible change

Set "requires_confirmation" to false when:
- the information is an objective progress update
- the information describes the current status
- the information adds general project information
- the user clearly confirms a decision themselves

If relevant is false, requires_confirmation must be false.

Do not include any other text.
"""
    )
    result = parse_llm_json(response.output_text, DEFAULT_ANALYSIS)

    if (
        result["relevant"] is not True
        or result["section"] not in VALID_SECTIONS
        or not result["content"]
    ):
        return dict(DEFAULT_ANALYSIS)

    return result


def process_project_context(client, project_id, message):
    result = analyze_project_message(client, message)

    if not result["relevant"]:
        return result

    if result["requires_confirmation"]:
        result["status"] = "confirmation_required"
        return result

    add_to_project_section(
        project_id,
        result["section"],
        result["content"]
    )

    result["status"] = "saved"

    return result