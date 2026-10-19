import json
import re


def _extract_json_text(text):
    """Holt den JSON-Teil aus einer LLM-Antwort.

    Das Modell antwortet manchmal mit ```json ... ``` oder mit zusaetzlichem
    Text vor/nach dem JSON. Hier wird alles bis auf das erste
    {...}-Objekt entfernt.
    """
    if not isinstance(text, str):
        return None

    text = text.strip()

    # Code-Fences entfernen: ```json ... ``` oder ``` ... ```
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        return None

    return text[start:end + 1]


def parse_llm_json(text, default):
    """Wandelt eine LLM-Antwort in ein dict um.

    Gibt bei jedem Fehler (kein JSON, kaputtes JSON, kein Objekt)
    eine Kopie von `default` zurueck, statt eine Exception zu werfen.
    Fehlende Keys werden aus `default` aufgefuellt, damit der aufrufende
    Code sich auf die Struktur verlassen kann.
    """
    json_text = _extract_json_text(text)

    if json_text is None:
        print(f"[llm_json] Kein JSON gefunden in: {text!r}")
        return dict(default)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as error:
        print(f"[llm_json] Ungueltiges JSON ({error}): {text!r}")
        return dict(default)

    if not isinstance(data, dict):
        print(f"[llm_json] JSON ist kein Objekt: {text!r}")
        return dict(default)

    for key, value in default.items():
        data.setdefault(key, value)

    return data
