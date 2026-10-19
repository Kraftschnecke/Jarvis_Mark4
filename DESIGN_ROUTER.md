# Design: Router (Step 2.2)

Ziel: Aus den zwei Prüf-Aufrufen am Anfang jeder Nachricht (`detect_command`,
`recognize_task`) wird **ein** Aufruf. Das spart pro Nachricht ca. 1,2 bis 1,6 s
und bei Aufgaben-Nachrichten außerdem ca. 800 Eingabe-Tokens
(Zahlen: `MESSUNGEN_MARK4.md`).

## Heute

```
Nachricht
  1. detect_command()   -> Befehl? (Projekt öffnen, Reset, Exit ...)   [KI-Aufruf]
  2. recognize_task()   -> Aufgabe? (Zeit, Rechnen, Websuche ...)      [KI-Aufruf]
  3. sonst: normaler Chat (Memory, Projekt-Analyse, Antwort)
```

## Neu

```
Nachricht
  1. route_message()    -> COMMAND, TASK oder CHAT                     [ein KI-Aufruf]
  2. COMMAND -> handle_command()   (unverändert)
     TASK    -> execute_registered_task() + respond_to_task()   (unverändert)
     CHAT    -> process_normal_message()                         (unverändert)
```

Alles hinter dem Router bleibt, wie es ist. Nur die Entscheidung "was ist das für
eine Nachricht" wird in einem Schritt getroffen.

## Neue Datei `router.py`

Funktion `route_message(client, message, task_registry)` gibt immer ein Dict
mit dieser festen Form zurück:

```python
{
    "kind": "COMMAND" | "TASK" | "CHAT",
    "command": {"intent": ..., "project_name": ..., "conversation_name": ...,
                "new_conversation_name": ...},     # nur bei COMMAND sinnvoll
    "task_type": "GET_TIME" | ... | None,          # nur bei TASK
    "parameters": {...}                            # nur bei TASK
}
```

Das Modell antwortet mit diesem JSON (ein Objekt):

```json
{
  "kind": "COMMAND",
  "intent": "OPEN_PROJECT",
  "project_name": "Jarvis",
  "conversation_name": null,
  "new_conversation_name": null,
  "task_type": null,
  "parameters": {}
}
```

`router.py` baut daraus die feste Form oben. Der restliche Code sieht nie das
rohe Modell-JSON.

## Der Prompt

- Die Befehlsliste und die Regeln aus `command.py` ziehen um (inhaltlich
  unverändert, damit sich die Erkennung nicht verschlechtert).
- Die Aufgabenliste wird **kürzer**: statt des ganzen JSON mit `actions` pro Aufgabe
  nur eine Zeile je Aufgabe, z. B.
  `SEARCH_WEB: Eine Websuche durchführen (Parameter: query)`.
  Das spart etwa die Hälfte der heutigen 800 Tokens.
- Vorrang, wie heute: Wenn klar ein Befehl gemeint ist, `COMMAND`. Sonst, wenn eine
  Aufgabe passt, `TASK`. Sonst `CHAT`. Im Zweifel `CHAT`.

## Sicherheit (gilt wie heute)

Die Antwort des Modells ist unvertraute Eingabe. `router.py` prüft sie:

1. Kaputtes oder fehlendes JSON -> `CHAT` (wie heute bei `detect_command`).
2. `kind` ist keiner der drei Werte -> `CHAT`.
3. `COMMAND`: `intent` muss in `VALID_INTENTS` stehen und darf nicht
   `NORMAL_MESSAGE` sein, sonst -> `CHAT`.
4. `TASK`: `task_type` muss im `TaskRegistry` registriert sein, sonst -> `CHAT`.
5. `parameters` muss ein Dict sein, sonst leer. Wie heute übernimmt
   `execute_registered_task` nur Parameter, die die Aufgabe kennt, und überschreibt nie
   Werte, die aus der vorherigen Action kommen.
6. Das Modell kann nur zwischen den bekannten Befehlen und Aufgaben wählen. Neue
   Fähigkeiten entstehen dadurch nicht, und `programs.json` bleibt die einzige
   Quelle für startbare Programme.

## Was sich im Code ändert

| Datei | Änderung |
|-------|----------|
| `router.py` | neu: `route_message` + Prüfregeln |
| `jarvis.py` | `_process_message` ruft `route_message` statt `detect_command` + `recognize_task` |
| `command.py` | nur noch `VALID_INTENTS` (der Prompt zieht nach `router.py`) |
| `task_recognizer.py` | wird gelöscht (der Prompt zieht nach `router.py`) |
| Tests | `test_llm_json.py`, `test_config.py` und die Tests, die `detect_command` / `recognize_task` ersetzen, werden auf den Router umgestellt; neue `test/test_router.py` |

Die alten Funktionen bleiben bis zur Router-Prüfung (unten) im Git-Verlauf
erreichbar (Tag `mark4-vor-router` auf dem Commit vor dem Umbau).

## Prüfung mit dem echten Modell: `router_check.py`

Tests mit Fakes beweisen nur den Code, nicht die Erkennung. Deshalb gibt es ein
kleines Skript `router_check.py` mit ca. 30 Beispielsätzen (Deutsch und Englisch,
Tippfehler, Grenzfälle) und dem erwarteten Ergebnis. Es ruft den echten Router auf
und zeigt eine Tabelle OK / FALSCH. Es kostet ein paar Cent und läuft nur von Hand.

Ablauf: erst mit dem alten Verfahren laufen lassen (Tag `mark4-vor-router`),
dann mit dem Router. Der Router darf nicht schlechter sein als vorher.

Beispiele: "Öffne Projekt Jarvis" (COMMAND), "mach mal die Lautstärke auf 30"
(TASK SET_VOLUME), "wie spät?" (TASK GET_TIME), "Ich öffne morgen ein Konto"
(CHAT, kein Befehl), "Was bedeutet Projekt?" (CHAT), "Schalte dich ab" (COMMAND EXIT).

## Erwartetes Ergebnis

| Nachricht | Aufrufe vorher | Aufrufe nachher |
|-----------|---------------:|----------------:|
| Chat ohne Projekt | 4 | 3 |
| Chat mit Projekt | 5 | 4 |
| Aufgabe (Zeit, Rechnen, Suche, Timer) | 3 | 2 |
| Befehl (Projekt öffnen ...) | 1 | 1 |

Gesamtzeit: ca. 1,2 bis 1,6 s weniger pro Nachricht, die nicht ein Befehl ist.
Der große Rest (Memory- und Projekt-Prüfung, 2 bis 3 s) wird erst im nächsten
Schritt (Parallelisierung) angegangen.

## Entscheidung und Änderung der Roadmap

Entschieden: **erst der Router**, danach neu messen, **dann** die Parallelisierung
von Memory- und Projekt-Prüfung als eigener Schritt. Damit bleibt jede Änderung
einzeln messbar und einzeln rückgängig zu machen.

Die Schritte 2.2 bis 2.6 in `PROJEKT_STATUS_MARK4.md` lauten dann:

- 2.2 Design Router (dieses Dokument)
- 2.3 Router umsetzen, `router_check.py`, Messung 2
- 2.4 Memory- und Projekt-Prüfung parallel zur Antwort, Messung 3
- 2.5 Verbindungspool für die Datenbank
- 2.6 Gesprächsverlauf begrenzen / zusammenfassen
- 2.7 (optional) Streaming
