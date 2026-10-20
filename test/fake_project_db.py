"""Gemeinsame Test-Hilfe: eine Datenbank im Speicher statt Neon.

Ersetzt die Funktionen aus project.py, die workspace.py benutzt.
Wird von test_workspace.py und test_server.py verwendet.
"""

import itertools


class FakeProjectDB:
    def __init__(self):
        self._ids = itertools.count(1)
        self.projects = {}        # id -> name
        self.conversations = {}   # id -> (project_id, title)
        self.messages = {}        # conversation id -> [{"role", "content"}]
        self.files = []

    # --- Hilfen fuer Tests ---
    def add_project(self, name):
        pid = next(self._ids)
        self.projects[pid] = name
        return pid

    def add_conversation(self, pid, title, messages=None):
        cid = next(self._ids)
        self.conversations[cid] = (pid, title)
        self.messages[cid] = list(messages or [])
        return cid

    # --- Ersatz fuer project.py ---
    def get_projects(self):
        return [(pid, name, None, None, None) for pid, name in self.projects.items()]

    def get_conversations(self, pid):
        rows = [(cid, title, None, None)
                for cid, (p, title) in self.conversations.items() if p == pid]
        return sorted(rows, key=lambda r: -r[0])

    def create_project(self, name, description=None):
        return self.add_project(name)

    def create_conversation(self, pid, title):
        cid = self.add_conversation(pid, title)
        return (cid, title, None, None)

    def load_conversation_messages(self, cid):
        return list(self.messages.get(cid, []))

    def rename_project(self, pid, name):
        self.projects[pid] = name

    def delete_project(self, pid):
        for cid in [c for c, (p, _) in self.conversations.items() if p == pid]:
            self.delete_conversation(cid)
        del self.projects[pid]

    def rename_conversation(self, cid, title):
        pid, _ = self.conversations[cid]
        self.conversations[cid] = (pid, title)

    def reset_conversation(self, cid):
        self.messages[cid] = []

    def delete_conversation(self, cid):
        self.conversations.pop(cid, None)
        self.messages.pop(cid, None)

    def search_projects(self, term):
        return [p for p in self.get_projects() if term and term.lower() in p[1].lower()]

    def get_conversation(self, pid, title):
        for cid, (p, t) in self.conversations.items():
            if p == pid and t.lower() == title.lower():
                return (cid, t, None, None)
        return None

    def install(self, workspace_module):
        w = workspace_module
        w.get_projects = self.get_projects
        w.get_conversations = self.get_conversations
        w.create_project = self.create_project
        w.create_conversation = self.create_conversation
        w.load_conversation_messages = self.load_conversation_messages
        w.rename_project = self.rename_project
        w.delete_project = self.delete_project
        w.rename_conversation = self.rename_conversation
        w.reset_project_conversation = self.reset_conversation
        w.delete_project_conversation = self.delete_conversation
        w.search_projects = self.search_projects
        w.get_conversation = self.get_conversation
        w.ensure_project_context = lambda pid, name: self.files.append((pid, name))
