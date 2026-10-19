class TaskRegistry:
    def __init__(self):
        self.tasks = {}

    def register(self, task):
        self.tasks[task.task_type] = task

    def get(self, task_type):
        return self.tasks.get(task_type)

    def get_all(self):
        return self.tasks.values()
