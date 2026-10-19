from config import MODEL
from personality import JARVIS_PERSONALITY
import json


def build_instructions(memory, project_context=None):
    """Persoenlichkeit + Hintergrundwissen als System-Anweisung.

    Memory und Projektkontext gehoeren hierher und nicht in die Nachricht:
    sonst behandelt das Modell sie wie Gespraechstext und zitiert sie.
    """
    parts = [JARVIS_PERSONALITY]

    if memory:
        parts.append(
            "Background knowledge about the user (use it when relevant, "
            "never quote or list it unprompted):\n" + str(memory)
        )

    if project_context:
        parts.append(
            "Context of the currently open project (use it when relevant, "
            "never quote or list it unprompted):\n" + str(project_context)
        )

    return "\n\n".join(parts)


def build_input(conversation):
    """Gespraech als echte Rollen-Nachrichten (user / assistant)."""
    return [
        {
            "role": "user" if message["role"] == "user" else "assistant",
            "content": message["content"]
        }
        for message in conversation.get_messages()
    ]


def ask_jarvis(client, conversation, memory, project_context=None):
    response = client.responses.create(
        model=MODEL,
        instructions=build_instructions(memory, project_context),
        input=build_input(conversation)
    )

    return response.output_text


def respond_to_task(client, user_message, task):
    task_results = []

    for result in task.result:
        if hasattr(result, "success"):
            task_results.append({
                "success": result.success,
                "data": result.data,
                "error": result.error
            })
        else:
            task_results.append(result)

    task_result_context = json.dumps(
        task_results, ensure_ascii=False, indent=2, default=str
    )
    
    response = client.responses.create(
        model=MODEL,
        instructions=JARVIS_PERSONALITY,
        input=f"""
The user asked:

{user_message}

A task was executed to fulfill the user's request.

Task type:
{task.task_type}

Task goal:
{task.goal}

Task status:
{task.status}

Task result:
{task_result_context}

Task error:
{task.error}

Respond naturally to the user's original request based on the task result.

When the task result contains web search results:
- Use the result as information sources for your answer.
- Summarize the relevant information naturally.
- Do not simply dump the raw search result data.
- Do not invent information that is not supported by the search results.
- If the search results do not provide enough information, say so.

If the task completed successfully, give the user the useful result
If the task failed, explain briefly that the task could not be completed
and mention the error in a natural way.

Do not mention internal concepts such as:
- TaskRegistry
- Task Executor
- Action Executor
- task_type
- internal architecture

Speak as J.A.R.V.I.S and address the user as Sir when appropriate.
"""
    )

    return response.output_text