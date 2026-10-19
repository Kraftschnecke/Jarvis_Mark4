import threading

from prompt_toolkit import prompt


def start_input():
    result = {}

    def read_input():
        try:
            result["message"] = prompt("You: ")
        except (EOFError, KeyboardInterrupt):
            # Strg+D / Strg+C beim Tippen: als Abbruch melden statt Absturz
            result["message"] = None

    # daemon: ein haengender Eingabe-Thread darf das Beenden nicht blockieren
    thread = threading.Thread(
        target=read_input,
        daemon=True
    )
    thread.start()

    return thread, result
