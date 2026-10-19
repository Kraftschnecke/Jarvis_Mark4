"""Projekt- und Konversationsverwaltung.

Hier steht, welches Projekt und welche Konversation gerade offen sind und wie
man sie oeffnet, anlegt, umbenennt, zuruecksetzt und loescht. Die Klasse kennt
weder das Sprachmodell noch Tasks oder Memory: sie arbeitet nur mit der
Datenbank (project.py), der lokalen project.md (project_context.py) und dem
Gespraechsverlauf im Speicher.
"""

from conversation import Conversation
from project_state import ProjectState
from project_context import create_project_file
from project import (
    search_projects,
    get_conversations,
    create_conversation,
    load_conversation_messages,
    get_conversation,
    rename_conversation,
    create_project,
    get_projects,
    rename_project,
    delete_project
)
from project import reset_conversation as reset_project_conversation
from project import delete_conversation as delete_project_conversation


class WorkspaceError(Exception):
    """Eine Aktion ist nicht moeglich. Der Text ist fuer den Nutzer gedacht."""


def clean_name(value, what):
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceError(f"{what} darf nicht leer sein.")

    value = value.strip()

    if len(value) > 100:
        raise WorkspaceError(f"{what} ist zu lang (maximal 100 Zeichen).")

    return value


class Workspace:
    def __init__(self):
        self.project_state = ProjectState()
        self.conversation = Conversation()

    def open_project(self, name):
        projects = search_projects(name)

        if len(projects) == 0:
            return "I couldn't find a matching project, Sir."

        if len(projects) > 1:
            result = "I found multiple matching projects, Sir.\n"

            for project in projects:
                result += f"- {project[1]}\n"

            return result

        self.project_state.set_project(projects[0])

        # Das Projekt liegt in der Cloud-DB, die project.md lokal. Fehlt die
        # Datei (z.B. anderer Rechner), wird sie aus der Vorlage angelegt.
        # Eine vorhandene Datei bleibt unveraendert.
        create_project_file(projects[0][0], projects[0][1])

        conversations = get_conversations(
            self.project_state.active_project[0]
        )

        if len(conversations) == 0:
            self.project_state.set_conversation(
                create_conversation(
                    self.project_state.active_project[0],
                    "Neue Unterhaltung"
                )
            )

            self.conversation.clear()

            return (
                f"I opened the project {self.project_state.active_project[1]} "
                f"and started a new conversation, Sir."
            )

        if len(conversations) == 1:
            self.project_state.set_conversation(conversations[0])

            self.conversation.load_messages(
                load_conversation_messages(
                    self.project_state.active_conversation[0]
                )
            )

            return (
                f"I opened the project {self.project_state.active_project[1]} "
                f" and the conversation "
                f"{self.project_state.active_conversation[1]}, Sir."
            )

        result = (
            f"I found the project {self.project_state.active_project[1]}, Sir.\n"
            "Available conversations:\n"
        )

        for i, conversation_item in enumerate(
            conversations,
            start=1
        ):
            result += f"{i}. {conversation_item[1]}\n"

        return result

    def create_project(self, name, description=None):
        project_id = create_project(
            name,
            description
        )

        return f"I created the project {name} with ID: {project_id}, Sir."

    def open_conversation(self, name):
        if self.project_state.active_project is None:
            return "No project is currently active, Sir"

        conversation = get_conversation(
            self.project_state.active_project[0],
            name
        )

        if conversation is None:
            return "I couldn't find that conversation, Sir."

        self.project_state.set_conversation(conversation)

        self.conversation.load_messages(
            load_conversation_messages(
                self.project_state.active_conversation[0]
            )
        )

        return (
            f"I opened the conversation "
            f"{self.project_state.active_conversation[1]}, Sir."
        )

    def create_conversation(self, name):
        if self.project_state.active_project is None:
            return "No project is currently active, Sir"

        self.project_state.set_conversation(
            create_conversation(
                self.project_state.active_project[0],
                name
            )
        )

        self.conversation.clear()

        return (
            f"I created a new conversation "
            f"{name} in {self.project_state.active_project[1]}, Sir."
        )

    def get_conversations(self):
        if self.project_state.active_project is None:
            return []

        return get_conversations(
            self.project_state.active_project[0]
        )

    def get_conversation(self, name):
        if self.project_state.active_project is None:
            return None

        return get_conversation(
            self.project_state.active_project[0],
            name
        )

    def rename_conversation(self, old_name, new_name):
        if self.project_state.active_project is None:
            return "No project is currently active, Sir."

        conversation = self.get_conversation(old_name)

        if conversation is None:
            return "I couldn't find that conversation, Sir."

        rename_conversation(
            conversation[0],
            new_name
        )

        self.project_state.set_conversation(
            (
                conversation[0],
                new_name,
                conversation[2],
                conversation[3]
            )
        )

        return (
            f"I renamed the conversation "
            f"from {old_name} to {new_name}, Sir."
        )

    def close_project(self):
        if self.project_state.active_project is None:
            return "No project is currently active, Sir"

        project_name = self.project_state.active_project[1]

        self.project_state.clear()
        self.conversation.clear()

        return (
            f"Closing project {project_name}, Sir"
        )

    def reset_conversation(self):
        if self.project_state.active_conversation is None:
            return "No conversation is currently active, Sir"

        reset_project_conversation(
            self.project_state.active_conversation[0]
        )

        self.conversation.clear()

        return "Conversation reset, Sir"

    def delete_conversation(self, name):
        if self.project_state.active_project is None:
            return "No project is currently active, Sir."

        conversation = self.get_conversation(name)

        if conversation is None:
            return "I couldn't find that conversation, Sir."

        delete_project_conversation(
            conversation[0]
        )

        if (
            self.project_state.active_conversation is not None
            and self.project_state.active_conversation[0] == conversation[0]
        ):
            self.project_state.active_conversation = None
            self.conversation.clear()

        return f"I deleted the conversation {name}, Sir."

    # ------------------------------------------------------------------
    # Aktionen ueber IDs (fuer die Seitenleiste der Web-Oberflaeche).
    # Die Methoden oben arbeiten mit Namen, wie man sie im Chat sagt.
    # Hier ist immer klar, welches Element gemeint ist, auch wenn zwei
    # Konversationen denselben Titel haben. Fehler kommen als
    # WorkspaceError mit einem lesbaren Text.
    # ------------------------------------------------------------------

    def get_tree(self):
        """Alle Projekte mit ihren Konversationen, fuer die Seitenleiste."""
        tree = []

        for project in sorted(get_projects(), key=lambda p: p[1].lower()):
            tree.append({
                "id": project[0],
                "name": project[1],
                "conversations": [
                    {"id": conversation[0], "title": conversation[1]}
                    for conversation in get_conversations(project[0])
                ]
            })

        return tree

    def get_active(self):
        project = self.project_state.active_project
        conversation = self.project_state.active_conversation

        return {
            "project_id": project[0] if project else None,
            "conversation_id": conversation[0] if conversation else None
        }

    def _find_project(self, project_id):
        for project in get_projects():
            if project[0] == project_id:
                return project

        raise WorkspaceError("Dieses Projekt gibt es nicht mehr.")

    def _find_conversation(self, project_id, conversation_id):
        for conversation in get_conversations(project_id):
            if conversation[0] == conversation_id:
                return conversation

        raise WorkspaceError("Diese Konversation gibt es nicht mehr.")

    def _name_is_taken(self, name, except_id=None):
        return any(
            project[1].lower() == name.lower() and project[0] != except_id
            for project in get_projects()
        )

    def select_conversation(self, project_id, conversation_id):
        """Macht Projekt und Konversation aktiv. Gibt den Verlauf zurueck."""
        project = self._find_project(project_id)
        conversation = self._find_conversation(project_id, conversation_id)

        self.project_state.set_project(project)
        create_project_file(project[0], project[1])

        messages = load_conversation_messages(conversation[0])

        self.project_state.set_conversation(conversation)
        self.conversation.load_messages(messages)

        return messages

    def select_project(self, project_id):
        """Macht ein Projekt aktiv (ohne Konversation).

        Gibt True zurueck, wenn das Projekt gewechselt wurde. Ist es schon
        aktiv, bleibt alles wie es ist (auch die offene Konversation).
        """
        project = self._find_project(project_id)
        active = self.project_state.active_project

        if active is not None and active[0] == project_id:
            return False

        self.project_state.set_project(project)
        self.project_state.set_conversation(None)
        self.conversation.clear()
        create_project_file(project[0], project[1])

        return True

    def add_project(self, name):
        """Legt ein Projekt an und macht es aktiv."""
        name = clean_name(name, "Der Projektname")

        if self._name_is_taken(name):
            raise WorkspaceError("Ein Projekt mit diesem Namen gibt es schon.")

        project_id = create_project(name)
        self.select_project(project_id)

        return project_id

    def rename_project_by_id(self, project_id, new_name):
        project = self._find_project(project_id)
        new_name = clean_name(new_name, "Der Projektname")

        if self._name_is_taken(new_name, except_id=project_id):
            raise WorkspaceError("Ein Projekt mit diesem Namen gibt es schon.")

        rename_project(project_id, new_name)

        active = self.project_state.active_project

        if active is not None and active[0] == project_id:
            self.project_state.set_project((project_id, new_name) + tuple(project[2:]))

    def delete_project_by_id(self, project_id):
        self._find_project(project_id)

        delete_project(project_id)

        active = self.project_state.active_project

        if active is not None and active[0] == project_id:
            self.project_state.clear()
            self.conversation.clear()

    def add_conversation(self, title, project_id=None):
        """Neue Konversation, sofort aktiv und leer.

        Ohne project_id im aktiven Projekt, sonst wird dieses Projekt aktiv.
        """
        title = clean_name(title, "Der Titel")

        if project_id is not None:
            self.select_project(project_id)

        project = self.project_state.active_project

        if project is None:
            raise WorkspaceError("Oeffne zuerst ein Projekt.")

        self.project_state.set_conversation(
            create_conversation(project[0], title)
        )
        self.conversation.clear()

        return self.project_state.active_conversation[0]

    def rename_conversation_by_id(self, project_id, conversation_id, new_title):
        conversation = self._find_conversation(project_id, conversation_id)
        new_title = clean_name(new_title, "Der Titel")

        rename_conversation(conversation_id, new_title)

        active = self.project_state.active_conversation

        if active is not None and active[0] == conversation_id:
            self.project_state.set_conversation(
                (conversation_id, new_title) + tuple(conversation[2:])
            )

    def reset_conversation_by_id(self, project_id, conversation_id):
        self._find_conversation(project_id, conversation_id)

        reset_project_conversation(conversation_id)

        active = self.project_state.active_conversation

        if active is not None and active[0] == conversation_id:
            self.conversation.clear()

    def delete_conversation_by_id(self, project_id, conversation_id):
        self._find_conversation(project_id, conversation_id)

        delete_project_conversation(conversation_id)

        active = self.project_state.active_conversation

        if active is not None and active[0] == conversation_id:
            self.project_state.active_conversation = None
            self.conversation.clear()
