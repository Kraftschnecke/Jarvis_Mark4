class ProjectState:
    def __init__(self):
        self.active_project = None
        self.active_conversation = None

    def set_project(self, project):
        self.active_project = project

    def set_conversation(self, conversation):
        self.active_conversation = conversation

    def clear(self):
        self.active_project = None
        self.active_conversation = None