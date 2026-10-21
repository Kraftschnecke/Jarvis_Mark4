import config
from untrusted import wrap_untrusted, UNTRUSTED_RULES
from config import MODEL
from personality import JARVIS_PERSONALITY, jarvis_personality, get_address
import json


def build_instructions(memory, project_context=None):
    """Persoenlichkeit + Hintergrundwissen als System-Anweisung.

    Memory und Projektkontext gehoeren hierher und nicht in die Nachricht:
    sonst behandelt das Modell sie wie Gespraechstext und zitiert sie.
    """
    parts = [jarvis_personality()]

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


def limit_history(messages, limit):
    """Nur die letzten `limit` Nachrichten; 0 oder weniger = alle.

    Der Ausschnitt beginnt immer mit einer Nutzer-Nachricht: Eine Antwort ohne
    die zugehoerige Frage waere ein halber Satz ohne Zusammenhang.
    """
    if limit <= 0 or len(messages) <= limit:
        return list(messages)

    recent = list(messages[-limit:])

    while recent and recent[0]["role"] != "user":
        recent.pop(0)

    return recent


def build_input(conversation):
    """Gespraech als echte Rollen-Nachrichten (user / assistant).

    Nur die letzten config.HISTORY_LIMIT Nachrichten: Je laenger ein Chat wird,
    desto mehr Tokens (Kosten, Zeit) braucht jede Antwort. Aelteres Wissen
    steckt im Memory und in project.md.
    """
    return [
        {
            "role": "user" if message["role"] == "user" else "assistant",
            "content": message["content"]
        }
        for message in limit_history(
            conversation.get_messages(), config.HISTORY_LIMIT
        )
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
    
    # Ergebnisse und Fehlertext stammen aus Tools (z.B. dem Internet): als
    # unvertraute Daten verpackt, nie als Anweisung (siehe untrusted.py)
    task_result_block = wrap_untrusted(f"task:{task.task_type}", task_result_context)
    task_error_block = wrap_untrusted(
        f"task-error:{task.task_type}", task.error if task.error else "None"
    )

    response = client.responses.create(
        model=MODEL,
        instructions=jarvis_personality() + UNTRUSTED_RULES,
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
{task_result_block}

Task error:
{task_error_block}

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

Speak as J.A.R.V.I.S and address the user as {get_address()} when appropriate.
"""
    )

    return response.output_text