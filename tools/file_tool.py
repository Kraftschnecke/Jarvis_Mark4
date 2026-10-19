import os
import re
from pathlib import Path

from tools.tool_result import ToolResult

# Dateien, die beim Oeffnen Code ausfuehren koennten. Programme startet
# Jarvis ausschliesslich ueber die Freigabeliste (programs.json).
BLOCKED_EXTENSIONS = {
    ".exe", ".com", ".bat", ".cmd", ".msi", ".msp", ".scr", ".pif",
    ".ps1", ".psm1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".hta", ".lnk", ".url", ".reg", ".jar", ".cpl", ".dll", ".msc",
    ".inf", ".application", ".appref-ms", ".gadget"
}

URI_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:(//|\\\\)")


def _error(message):
    return ToolResult(success=False, error=message)


def open_file(path):
    if not isinstance(path, str) or not path.strip():
        return _error("Es wurde kein Dateipfad angegeben.")

    path = path.strip()

    # Keine Web-Adressen, keine Netzwerkpfade (\\server\freigabe)
    if URI_PATTERN.match(path) or path.startswith(("\\\\", "//")):
        return _error(
            "Ich oeffne nur lokale Dateien, keine Web- oder Netzwerkadressen."
        )

    file_path = Path(path).expanduser()

    if not file_path.exists():
        return _error(f"Die Datei oder der Ordner existiert nicht: {path}")

    # Windows ignoriert Leerzeichen und Punkte am Namensende
    # ("tool.exe." ist trotzdem eine exe), und Verknuepfungen zeigen
    # irgendwohin. Deshalb wird der Pfad und sein aufgeloestes Ziel geprueft.
    for candidate in (file_path, file_path.resolve()):
        extension = Path(candidate.name.rstrip(" .")).suffix.lower()

        if extension in BLOCKED_EXTENSIONS:
            return _error(
                f"Aus Sicherheitsgruenden oeffne ich keine Programmdateien "
                f"({extension}) als Datei. Programme starte ich nur, wenn "
                f"sie in programs.json freigegeben sind."
            )

    try:
        os.startfile(str(file_path))
        return ToolResult(
            success=True,
            data=str(file_path)
        )
    except Exception as error:
        return _error(str(error))
