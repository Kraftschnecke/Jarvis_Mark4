"""Startet alle Tests im Ordner test/ und zeigt eine Uebersicht.

Aufruf (im Projektordner):
    py run_tests.py          # kurze Uebersicht, Ausgabe nur bei Fehlern
    py run_tests.py -v       # zusaetzlich die Ausgabe jedes Tests

Jeder Test laeuft in einem eigenen Python-Prozess, damit sich die Tests nicht
gegenseitig beeinflussen. Kein Test spricht mit der echten Datenbank, der
OpenAI-API oder startet Programme: alles ist durch Fakes ersetzt.
Exit-Code 0 = alles gruen, 1 = mindestens ein Test ist fehlgeschlagen.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
TEST_DIR = PROJECT_DIR / "test"
SUCCESS_MARKER = "ALL TESTS PASSED"
TIMEOUT_SECONDS = 60


def run_test(path):
    started = time.time()

    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return False, f"Abbruch: nach {TIMEOUT_SECONDS} Sekunden keine Antwort", time.time() - started

    output = (completed.stdout or "") + (completed.stderr or "")
    passed = completed.returncode == 0 and SUCCESS_MARKER in output

    return passed, output.strip(), time.time() - started


def main():
    verbose = "-v" in sys.argv[1:]
    tests = sorted(TEST_DIR.glob("test_*.py"))

    if not tests:
        print(f"Keine Tests gefunden in {TEST_DIR}")
        return 1

    results = []

    for path in tests:
        passed, output, seconds = run_test(path)
        results.append((path.name, passed, output, seconds))

        status = "OK     " if passed else "FEHLER "
        print(f"{status}{path.name:<36}{seconds:5.1f}s")

        if verbose or not passed:
            for line in output.splitlines():
                print(f"        {line}")

    failed = [name for name, passed, _, _ in results if not passed]

    print()
    print(f"{len(results) - len(failed)} von {len(results)} Test-Dateien bestanden.")

    if failed:
        print("Fehlgeschlagen: " + ", ".join(failed))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
