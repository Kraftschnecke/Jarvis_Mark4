"""Zeit-Log fuer die Anfragen an das Sprachmodell (Mark 4, Step 2.1).

Zweck: messen, bevor etwas beschleunigt wird. Fuer jede Nachricht wird
ausgegeben, wie viele KI-Aufrufe sie gebraucht hat, wie lange jeder dauerte
und wie viele Tokens (Eingabe / Ausgabe) dabei verbraucht wurden.

Einschalten: in der .env  JARVIS_TIMING=1  setzen. Ausgeschaltet (Standard)
wird nichts umgebaut und nichts gemessen.

So funktioniert es:
- wrap(client) packt den OpenAI-Client in einen Huellen-Client. Dessen
  responses.create() misst die Zeit, ruft den echten Client auf und merkt sich
  das Ergebnis. Die Aufrufstellen im restlichen Code bleiben unveraendert.
- Der Name eines Aufrufs ist die Funktion, die ihn gemacht hat, z.B.
  "router.route_message".
- start_message() / finish_message() klammern eine Nachricht (siehe
  Jarvis.process_message). finish_message() gibt die Zusammenfassung aus.
"""

import sys
import threading
import time

# Ausgabe-Funktion. Tests ersetzen sie, um die Zeilen abzufangen.
emit = print

_lock = threading.Lock()
_current = None

# Wird erst durch wrap() eingeschaltet. Solange es aus ist, tun start_message()
# und finish_message() nichts.
_enabled = False


def _caller_label(depth):
    """Name der Funktion, die den KI-Aufruf gemacht hat: 'modul.funktion'."""
    try:
        frame = sys._getframe(depth)
        module = frame.f_globals.get("__name__", "?")
        return f"{module}.{frame.f_code.co_name}"
    except ValueError:
        return "unbekannt"


def _tokens(response):
    """(Eingabe-Tokens, Ausgabe-Tokens) aus der Antwort, sonst (None, None)."""
    usage = getattr(response, "usage", None)

    return (
        getattr(usage, "input_tokens", None),
        getattr(usage, "output_tokens", None)
    )


def start_message(text):
    """Beginnt die Messung einer Nachricht."""
    global _current

    if not _enabled:
        return

    with _lock:
        _current = {
            "text": text,
            "started": time.perf_counter(),
            "calls": []
        }


def record_call(label, seconds, input_tokens=None, output_tokens=None, failed=False):
    """Merkt sich einen KI-Aufruf der gerade laufenden Nachricht."""
    with _lock:
        if _current is None:
            return

        _current["calls"].append({
            "label": label,
            "seconds": seconds,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "failed": failed
        })


def finish_message():
    """Beendet die Messung und gibt die Zusammenfassung aus."""
    global _current

    with _lock:
        current, _current = _current, None

    if current is None:
        return

    emit(format_summary(current, time.perf_counter() - current["started"]))


def _count(value):
    return "?" if value is None else str(value)


def format_summary(current, total_seconds):
    """Baut den Ausgabetext fuer eine Nachricht (mehrere Zeilen)."""
    calls = current["calls"]
    ai_seconds = sum(call["seconds"] for call in calls)
    text = " ".join(current["text"].split())

    if len(text) > 50:
        text = text[:47] + "..."

    lines = [
        f'[TIMING] "{text}" -> {len(calls)} KI-Aufrufe, '
        f'{total_seconds:.2f} s gesamt (davon KI {ai_seconds:.2f} s)'
    ]

    for number, call in enumerate(calls, start=1):
        failed = "  FEHLER" if call["failed"] else ""
        lines.append(
            f'[TIMING]   {number}. {call["label"]:<40} {call["seconds"]:5.2f} s'
            f'   Tokens ein/aus: {_count(call["input_tokens"])}/'
            f'{_count(call["output_tokens"])}{failed}'
        )

    return "\n".join(lines)


class _TimedResponses:
    def __init__(self, responses):
        self._responses = responses

    def create(self, *args, **kwargs):
        label = _caller_label(2)
        started = time.perf_counter()

        try:
            response = self._responses.create(*args, **kwargs)
        except Exception:
            record_call(label, time.perf_counter() - started, failed=True)
            raise

        input_tokens, output_tokens = _tokens(response)
        record_call(
            label, time.perf_counter() - started, input_tokens, output_tokens
        )

        return response


class TimedClient:
    """Huelle um den OpenAI-Client, die nur responses.create() misst."""

    def __init__(self, client):
        self._client = client
        self.responses = _TimedResponses(client.responses)

    def __getattr__(self, name):
        # Alles andere geht unveraendert an den echten Client
        return getattr(self._client, name)


def wrap(client):
    """Schaltet die Messung ein und gibt den Client mit Zeitmessung zurueck."""
    global _enabled

    _enabled = True

    return TimedClient(client)
