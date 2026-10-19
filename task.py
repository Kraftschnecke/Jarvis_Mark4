class Task:
    def __init__(self, task_type, goal):
        self.task_type = task_type
        self.goal = goal
        self.status = "PENDING"
        self.actions = []
        self.result = None
        self.error = None

    def add_action(self, action):
        self.actions.append(action)