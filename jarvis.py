import traceback

from openai import OpenAI
import ai_log
from parallel import Job
from config import OPENAI_TIMEOUT, TIMING_ENABLED
from memory import Memory
from settings_manager import SettingsManager
from personality import get_address, set_address, DEFAULT_ADDRESS
from task_registry import TaskRegistry
from task_executor import execute_registered_task
from brain import respond_to_task, ask_jarvis
from project_context import (
    get_project_context,
    add_to_project_section
)
from project_analyzer import process_project_context
from router import route_message
from background_tasks import get_results
from workspace import Workspace
from tasks import (
    register_all_tasks
)
from project import save_message


YES_ANSWERS = {
    "ja", "yes", "y", "okay", "ok", "genau", "klar", "gerne",
    "do it", "speichern", "mach das", "yep", "jo"
}

NO_ANSWERS = {
    "nein", "no", "n", "nope", "nee", "nicht speichern", "lieber nicht"
}


def normalize_answer(message):
    """Macht aus 'Ja!' oder ' ja. ' ein vergleichbares 'ja'."""
    return message.strip().lower().strip(" .!?,;:")


def build_confirmation_question(section, content):
    return (
        f"{get_address()}, soll ich das im Project Context unter \"{section}\" "
        f"festhalten?\n"
        f"-> {content}\n"
        f"(ja / nein)"
    )


class Jarvis:
    def __init__(self):
        self.client = OpenAI(timeout=OPENAI_TIMEOUT)

        # Nur wenn JARVIS_TIMING=1: jeder KI-Aufruf wird gemessen (ai_log.py)
        if TIMING_ENABLED:
            self.client = ai_log.wrap(self.client)

        self.workspace = Workspace()
        self.pending_project_confirmation = None
        self.settings_manager = SettingsManager()
        self.apply_settings()
        self.memory = Memory()
        self.memory.load()
        self.task_registry = TaskRegistry()
        register_all_tasks(self.task_registry)

    def apply_settings(self):
        """Uebernimmt Einstellungen, die im Programm gebraucht werden (Anrede)."""
        set_address(
            self.settings_manager.get("jarvis", "address", DEFAULT_ADDRESS)
        )

    def memory_enabled(self):
        return bool(
            self.settings_manager.get("memory", "enabled", True)
        )

    def get_memory_context(self):
        # Ist Memory aus, lernt Jarvis nichts Neues und nutzt auch nichts Altes.
        if not self.memory_enabled():
            return Memory.EMPTY_CONTEXT

        return self.memory.get_context()

    # --- Projekte und Konversationen: Verwaltung liegt in workspace.py ---

    @property
    def project_state(self):
        return self.workspace.project_state

    @property
    def conversation(self):
        return self.workspace.conversation

    def open_project(self, name):
        return self.workspace.open_project(name)

    def create_project(self, name, description=None):
        return self.workspace.create_project(name, description)

    def open_conversation(self, name):
        return self.workspace.open_conversation(name)

    def create_conversation(self, name):
        return self.workspace.create_conversation(name)

    def get_conversations(self):
        return self.workspace.get_conversations()

    def get_conversation(self, name):
        return self.workspace.get_conversation(name)

    def rename_conversation(self, old_name, new_name):
        return self.workspace.rename_conversation(old_name, new_name)

    def close_project(self):
        result = self.workspace.close_project()
        # Eine offene Rueckfrage gehoert zum geschlossenen Projekt.
        self.pending_project_confirmation = None
        return result

    def reset_conversation(self):
        return self.workspace.reset_conversation()

    def delete_conversation(self, name):
        return self.workspace.delete_conversation(name)

    # --- Seitenleiste der Web-Oberflaeche (Aktionen ueber IDs) ---

    def get_tree(self):
        return self.workspace.get_tree()

    def get_active(self):
        return self.workspace.get_active()

    def select_conversation(self, project_id, conversation_id):
        messages = self.workspace.select_conversation(
            project_id, conversation_id
        )
        # Eine offene Rueckfrage gehoert zur vorherigen Konversation.
        self.pending_project_confirmation = None
        return messages

    def select_project(self, project_id):
        changed = self.workspace.select_project(project_id)
        if changed:
            self.pending_project_confirmation = None
        return changed

    def add_project(self, name):
        project_id = self.workspace.add_project(name)
        # Das neue Projekt ist aktiv: alte Rueckfragen gelten nicht mehr.
        self.pending_project_confirmation = None
        return project_id

    def rename_project_by_id(self, project_id, new_name):
        self.workspace.rename_project_by_id(project_id, new_name)

    def delete_project_by_id(self, project_id):
        self.workspace.delete_project_by_id(project_id)
        self.pending_project_confirmation = None

    def add_conversation(self, title, project_id=None):
        conversation_id = self.workspace.add_conversation(title, project_id)
        if project_id is not None:
            self.pending_project_confirmation = None
        return conversation_id

    def rename_conversation_by_id(self, project_id, conversation_id, new_title):
        self.workspace.rename_conversation_by_id(
            project_id, conversation_id, new_title
        )

    def reset_conversation_by_id(self, project_id, conversation_id):
        self.workspace.reset_conversation_by_id(project_id, conversation_id)

    def delete_conversation_by_id(self, project_id, conversation_id):
        self.workspace.delete_conversation_by_id(project_id, conversation_id)

    def process_normal_message(self, message):
        # Momentaufnahme VOR den Hintergrund-Jobs: Die Antwort bekommt Memory und
        # Projekt-Kontext im Zustand vor dieser Nachricht (siehe DESIGN_PARALLEL.md).
        memory_context = self.get_memory_context()
        active_project = self.project_state.active_project

        project_context = (
            get_project_context(active_project[0])
            if active_project is not None
            else None
        )

        # Memory- und Projekt-Pruefung laufen gleichzeitig mit der Antwort.
        memory_job = None
        project_job = None

        if self.memory_enabled():
            memory_job = Job(self.memory.process, self.client, message)

        if active_project is not None:
            project_job = Job(self.process_project_context, message)

        try:
            self.conversation.add_message("user", message)

            if self.project_state.active_conversation is not None:
                save_message(
                    self.project_state.active_conversation[0],
                    "user",
                    message
                )

            answer = ask_jarvis(
                self.client,
                self.conversation,
                memory_context,
                project_context
            )
        finally:
            # Nach einer Nachricht darf nichts mehr im Hintergrund schreiben,
            # auch nicht, wenn die Antwort gescheitert ist.
            for job in (memory_job, project_job):
                if job is not None:
                    job.wait()

        self.conversation.add_message("assistant", answer)

        if self.project_state.active_conversation is not None:
            save_message(
                self.project_state.active_conversation[0],
                "assistant",
                answer
            )

        if memory_job is not None:
            try:
                memory_job.result()
            except Exception as error:
                # Memory ist Nebensache: ein Fehler dort darf die
                # eigentliche Antwort nicht verhindern.
                print(f"[memory] Konnte nichts speichern: {error}")

        project_result = None

        if project_job is not None:
            try:
                project_result = project_job.result()
            except Exception as error:
                # Ebenso die Projekt-Pruefung: Antwort ohne Rueckfrage.
                print(f"[projekt] Pruefung fehlgeschlagen: {error}")

        # Eine neue Nachricht macht jede alte offene Rueckfrage ungueltig.
        self.pending_project_confirmation = None
        confirmation_question = None

        if (
            project_result is not None
            and project_result.get("status") == "confirmation_required"
        ):
            self.pending_project_confirmation = {
                "project_id": active_project[0],
                "section": project_result["section"],
                "content": project_result["content"]
            }

            confirmation_question = build_confirmation_question(
                project_result["section"],
                project_result["content"]
            )

        # Die Rueckfrage gehoert nicht in den Chatverlauf, nur in die Anzeige.
        if confirmation_question is not None:
            answer = f"{answer}\n\n{confirmation_question}"

        return {
            "status": "response",
            "content": answer
        }

    def process_project_context(self, message):
        if self.project_state.active_project is None:
            return None

        return process_project_context(
            self.client,
            self.project_state.active_project[0],
            message
        )

    def handle_project_confirmation(self, message):
        pending = self.pending_project_confirmation

        if pending is None:
            return None

        # Eine Rueckfrage gilt nur fuer die direkt folgende Nachricht.
        # Egal was der User antwortet: danach ist sie verbraucht.
        self.pending_project_confirmation = None

        active_project = self.project_state.active_project

        if active_project is None or active_project[0] != pending["project_id"]:
            return None

        answer = normalize_answer(message)

        if answer in YES_ANSWERS:
            saved = add_to_project_section(
                pending["project_id"],
                pending["section"],
                pending["content"]
            )

            if not saved:
                return (
                    f"Das konnte ich nicht speichern, {get_address()}. "
                    "Vielleicht steht es schon im Project Context."
                )

            return (
                f"Verstanden, {get_address()}. "
                "Ich habe die Information in Project Context gespeichert."
            )

        if answer in NO_ANSWERS:
            return (
                f"Verstanden, {get_address()}. "
                "Ich habe diese Information nicht gespeichert."
            )

        return None

    def handle_command(self, command):
        if command["intent"] == "RESET_CONVERSATION":
            return self.reset_conversation()

        if command["intent"] == "OPEN_PROJECT":
            return self.open_project(
                command["project_name"]
            )

        if command["intent"] == "CLOSE_PROJECT":
            return self.close_project()

        if command["intent"] == "OPEN_CONVERSATION":
            return self.open_conversation(
                command["conversation_name"]
            )

        if command["intent"] == "RENAME_CONVERSATION":
            return self.rename_conversation(
                command["conversation_name"],
                command["new_conversation_name"]
            )

        if command["intent"] == "CREATE_CONVERSATION":
            return self.create_conversation(
                command["conversation_name"]
            )

        if command["intent"] == "CREATE_PROJECT":
            return self.create_project(
                command["project_name"]
            )

        return None

    def process_message(self, message):
        """Einziger Einstiegspunkt fuer CLI und GUI.

        Faengt Fehler ab (z.B. Netzwerkausfall bei der Modell-Anfrage). Ohne
        das wuerde das CLI abstuerzen und die GUI fuer immer auf
        "THINKING..." haengen bleiben, weil der Worker nie fertig meldet.
        Strg+C (KeyboardInterrupt) wird bewusst nicht abgefangen.
        """
        ai_log.start_message(message)

        try:
            return self._process_message(message)
        except Exception as error:
            traceback.print_exc()

            # Eine halb verarbeitete Nachricht darf keine Rueckfrage offen lassen
            self.pending_project_confirmation = None

            return {
                "status": "response",
                "content": (
                    f"{get_address()}, bei der Verarbeitung ist ein Fehler aufgetreten "
                    f"({type(error).__name__}: {str(error)[:200]}). "
                    "Bitte versuche es noch einmal."
                )
            }
        finally:
            ai_log.finish_message()

    def _process_message(self, message):

        confirmation_result = self.handle_project_confirmation(
            message
        )

        if confirmation_result is not None:
            return {
                "status": "response",
                "content": confirmation_result
            }

        # Ein einziger KI-Aufruf entscheidet: Befehl, Aufgabe oder Chat
        route = route_message(
            self.client,
            message,
            self.task_registry
        )

        if route["kind"] == "COMMAND":
            command = route["command"]

            if command["intent"] == "EXIT":
                return {
                    "status": "exit",
                    "content": f"Shutting down, {get_address()}"
                }

            command_result = self.handle_command(
                command
            )

            if command_result is not None:
                return {
                    "status": "response",
                    "content": command_result
                }

        if route["kind"] == "TASK":
            task = execute_registered_task(
                self.task_registry,
                route["task_type"],
                route["parameters"]
            )

            return {
                "status": "response",
                "content": respond_to_task(
                    self.client,
                    message,
                    task
                )
            }

        return self.process_normal_message(message)

    def get_background_results(self):
        return get_results()

    def process_background_result(self, result):
        if result["type"] == "TIMER_FINISHED":
            seconds = result["data"]["seconds"]

            if seconds < 60:
                return (
                    f"{get_address()}, der Timer ist nach {seconds} Sekunden abgelaufen."
                )

            minutes = seconds // 60
            return f"{get_address()}, der Timer ist nach {minutes} Minuten abgelaufen"

    def check_background_results(self):
        results = self.get_background_results()
        responses = []

        for result in results:
            response = self.process_background_result(result)

            if response is not None:
                responses.append(response)

        return responses
