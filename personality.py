"""Persoenlichkeit und Anrede von J.A.R.V.I.S.

Die Persoenlichkeit ist fest (Entscheidung Step 3.4). Einstellbar ist nur die
Anrede ("Sir" oder was in den Einstellungen steht). Sie gilt ueberall: in den
Prompts an das Sprachmodell und in allen festen Texten (Fehlermeldungen,
Bestaetigungen, Timer ...). Alle Stellen fragen mit get_address() nach dem
aktuellen Wert, deshalb wirkt eine Aenderung sofort.
"""

JARVIS_NAME = "J.A.R.V.I.S"

DEFAULT_ADDRESS = "Sir"

_address = DEFAULT_ADDRESS


def get_address():
    return _address


def set_address(value):
    """Setzt die Anrede. Ungueltiges (leer, kein Text) wird zu "Sir"."""
    global _address

    _address = value if is_valid_address(value) else DEFAULT_ADDRESS


def is_valid_address(value):
    """Ein kurzes, einzeiliges Wort oder Name ohne Steuerzeichen."""
    return (
        isinstance(value, str)
        and value == value.strip()
        and 1 <= len(value) <= 30
        and value.isprintable()
    )


def jarvis_personality():
    return f"""
You are J.A.R.V.I.S, a personal AI assistant.
You are intellegent, calm, helpful.
You communticate naturally and clearly.
You address me as {get_address()} and not by my name.
"""


# Mit der Standard-Anrede (fuer Tests und als Nachschlagewert)
JARVIS_PERSONALITY = jarvis_personality()
