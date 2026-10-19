class Conversation:
    def __init__(self):
        self.messages = []

    def add_message(self, role, content):
        self.messages.append({
            "role": role,
            "content": content
        })

    def clear(self):
        self.messages.clear()

    def load_messages(self, messages):
        self.messages = messages

    def get_messages(self):
        return self.messages