# J.A.R.V.I.S. (Mark 4)

Persönlicher KI-Assistent: Python-Kern, OpenAI-Modell, Neon-PostgreSQL für
Erinnerungen, Projekte und Konversationen, Web-Oberfläche im Browser.

Stand, Roadmap und Entscheidungen: `PROJEKT_STATUS_MARK4.md`.

## Voraussetzungen

- Windows, Python 3.13 (Start mit `py`)
- Ein OpenAI-API-Key
- Eine Neon-PostgreSQL-Datenbank (Verbindungs-URL)
- Optional: Brave-Search-API-Key (nur für die Websuche)

## Einrichten

Im Projektordner:

```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
copy programs.example.json programs.json
```

1. `.env` öffnen und `OPENAI_API_KEY`, `DATABASE_URL` und `BRAVE_API_KEY` eintragen.
   Die `.env` gehört nie in Git.
2. `programs.json` öffnen und nur Programme eintragen, die Jarvis starten darf.
   Alles, was dort nicht steht (außer ein paar eingebauten Windows-Programmen),
   startet Jarvis nicht.
3. `settings.json` entsteht beim ersten Start von selbst. Der Text eines Projekts (`project.md`) liegt in der Datenbank; ansehen mit `py show_project.py` (Liste) bzw. `py show_project.py <ID>`.
   Die Tabellen in der Datenbank (Erinnerungen, Projekte, Konversationen, Nachrichten)
   legt Jarvis ebenfalls selbst an, eine leere Neon-Datenbank reicht.

## Starten

- Web-Oberfläche: `py server.py` oder Doppelklick auf `start_jarvis.bat`.
  Der Browser öffnet `http://127.0.0.1:8000`. Beenden mit Strg+C.
- Kommandozeile: `py main.py`

Der Server hört nur auf dem eigenen Rechner (`127.0.0.1`), er hat noch keinen Login.

## Tests

```
py run_tests.py        # kurze Übersicht
py run_tests.py -v     # mit Ausgabe jedes Tests
```

Die Tests brauchen weder Internet noch Datenbank noch API-Key.

Manuelle Abnahme: `ABNAHMETEST_CLI.md` und `ABNAHMETEST_WEB.md`.
