from config import MODEL
from llm_json import parse_llm_json

VALID_INTENTS = {
    "CREATE_PROJECT", "OPEN_PROJECT", "CLOSE_PROJECT",
    "CREATE_CONVERSATION", "OPEN_CONVERSATION", "RENAME_CONVERSATION",
    "RESET_CONVERSATION", "EXIT", "NORMAL_MESSAGE"
}

DEFAULT_COMMAND = {
    "intent": "NORMAL_MESSAGE",
    "project_name": None,
    "conversation_name": None,
    "new_conversation_name": None
}


def detect_command(client, message):
    response = client.responses.create(
        model=MODEL,
        input=f"""
Determine the user's intent.

Possible intents:

- CREATE_PROJECT
  The user wants to create a new project.

- OPEN_PROJECT
  The user wants to open, continue, or resume an existing project.

- CLOSE_PROJECT
  The user wants to close or leave the currently active project.

- CREATE_CONVERSATION
  The user wants to create a new conversation inside the currently
  selected project.
  Detect request to create a new conversation.
  Extract the complete conversation name after "create conversation".
  The conversation name may contain multiple words.
  Example:
    "create conversation Test 123"
    --> conversation_name = "Test 123"

- OPEN_CONVERSATION
  The user wants to open, continue, or resume a specific conversation
  inside the currently selected project.

- RENAME_CONVERSATION
  The user wants to rename an existing conversation inside the currently
  selected project

- RESET_CONVERSATION
  The user wants to reset the current conversation.

- EXIT
  The user wants to exit or shut down J.A.R.V.I.S.

- NORMAL_MESSAGE
  The message is a normal conversation and is not a command.

Important:
- Understand the user's meaning, not exact wording.
- The user may write in German or English.
- Minor spelling mistakes are possible.
- Only classify something as a command if the user's intent is clear.
- If a project is mentioned, extract the name as accurately as possible.
- Do not invent or complete a project name that the user did not provide.
- If the user wants to create a new conversation, do not invent a conversation
  name

Return ONLY valid JSON in this exact format:

{{
    "intent": "INTENT_NAME",
    "project_name": "project name or null",
    "conversation_name": "conversation name or null",
    "new_conversation_name": "new name or null"
}}

Examples:

User: "create conversation Test 123"

JSON:
{{
    "intent": "CREATE_CONVERSATION",
    "project_name": null,
    "conversation_name": "Test 123",
    "new_conversation_name": null
}}

If the user wants to open a specific conversation, extract its name as
accurately as possible.
Do not invent or complete a conversation name that the user did not provide.

If the user wants to rename a conversation:
- conversation_name must contain the current conversation name.
- new_conversation_name must contain the new name.
- Do not invent either name.

User message::
{message}
"""
    )

    command = parse_llm_json(response.output_text, DEFAULT_COMMAND)

    if command["intent"] not in VALID_INTENTS:
        return dict(DEFAULT_COMMAND)

    return command
