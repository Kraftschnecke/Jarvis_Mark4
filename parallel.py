"""Kleine Hilfe: eine Funktion in einem eigenen Thread laufen lassen (Step 2.4).

Benutzt von Jarvis.process_normal_message: Die Memory-Pruefung und die
Projekt-Pruefung laufen gleichzeitig mit der Antwort. Design und Begruendung:
DESIGN_PARALLEL.md

    job = Job(funktion, argument1, argument2)   # startet sofort
    ... andere Arbeit ...
    job.wait()      # wartet, bis der Thread fertig ist (wirft nie einen Fehler)
    job.result()    # Ergebnis; hat die Funktion einen Fehler geworfen, wird er hier erneut geworfen
"""

import threading


class Job:
    def __init__(self, function, *arguments):
        self._result = None
        self._error = None

        # Daemon-Thread: Strg+C beendet das Programm auch dann, wenn der Thread
        # gerade noch auf eine Antwort wartet.
        self._thread = threading.Thread(
            target=self._run,
            args=(function, arguments),
            daemon=True
        )
        self._thread.start()

    def _run(self, function, arguments):
        try:
            self._result = function(*arguments)
        except Exception as error:
            self._error = error

    def wait(self):
        # In kurzen Schritten warten statt mit einem einzigen join(): So bleibt
        # Strg+C auch waehrend des Wartens wirksam (unter Windows).
        while self._thread.is_alive():
            self._thread.join(0.2)

    def result(self):
        self.wait()

        if self._error is not None:
            raise self._error

        return self._result
