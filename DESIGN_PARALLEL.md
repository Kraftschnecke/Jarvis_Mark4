# Design: Memory- und Projekt-Prüfung parallel zur Antwort (Step 2.4)

Ziel: Bei einer normalen Chat-Nachricht laufen die Memory-Prüfung und die
Projekt-Prüfung **gleichzeitig mit der Antwort** statt davor. Die Wartezeit ist dann
die des längsten dieser Aufrufe statt der Summe.

Zahlen aus Messung 2 (`MESSUNGEN_MARK4.md`): Router 1,6 bis 2,3 s, danach nacheinander
Memory 0,9 bis 1,3 s, Projekt 1,1 bis 2,0 s, Antwort 1,2 bis 2,0 s.

## Heute (`process_normal_message` in `jarvis.py`)

```
Router                                   (1 Aufruf)
  1. memory.process(message)             (1 Aufruf + DB schreiben)
  2. process_project_context(message)    (1 Aufruf + project.md schreiben)
  3. Nachricht in Verlauf + DB speichern
  4. ask_jarvis(...)                     (1 Aufruf, liest Memory + project.md)
  5. Antwort in Verlauf + DB speichern
  6. Rückfrage ("Soll ich das speichern?") an die Antwort hängen
```

## Neu

```
Router                                   (1 Aufruf)
  Memory und Projekt-Kontext als Text VORHER lesen (Momentaufnahme)
  Nachricht in Verlauf + DB speichern
  gleichzeitig:  [Thread A] memory.process(message)
                 [Thread B] process_project_context(message)
                 [Haupt]    ask_jarvis(...)
  warten, bis A und B fertig sind          (immer, auch wenn die Antwort scheitert)
  Antwort in Verlauf + DB speichern
  Rückfrage anhängen
```

Es kommen keine zusätzlichen KI-Aufrufe dazu, nur die Reihenfolge ändert sich.

Erwartung: Chat ohne Projekt ca. 3,1 s statt 4,7 s, Chat mit Projekt ca. 4 s statt
6,4 bis 7,3 s.

## Was sich fachlich ändert (bewusst)

1. **Die Antwort sieht Memory und `project.md` im Zustand vor dieser Nachricht.** Eine
   Tatsache aus genau dieser Nachricht ("Ich heiße Moritz") steht noch nicht im Memory,
   wenn die Antwort entsteht. Das ist unkritisch: Die Nachricht selbst steht im
   Gesprächsverlauf, den die Antwort sowieso bekommt. Ab der nächsten Nachricht ist alles
   im Memory und in `project.md`.
2. **Ein Fehler in der Projekt-Prüfung stoppt die Antwort nicht mehr.** Heute führt er zur
   Fehlermeldung statt zur Antwort. Neu wird er in die Konsole geschrieben, die Antwort
   kommt ohne Rückfrage. Das entspricht schon heute dem Verhalten bei Memory-Fehlern.
3. Alles andere bleibt: Die Rückfrage gilt nur für die nächste Nachricht, wird nicht im
   Verlauf gespeichert, und `ja`/`nein` brauchen keinen KI-Aufruf.

## Technik

Neue kleine Datei `parallel.py`:

```python
job = Job(funktion, argumente)   # startet sofort in einem eigenen Thread
job.wait()                       # wartet; wirft keinen Fehler
job.result()                     # Ergebnis, oder wirft den Fehler des Threads erneut
```

- Der Thread ist ein **Daemon-Thread**: Strg+C beendet das Programm auch dann,
  wenn gerade ein Aufruf läuft (wie `cli_input.py` und `timer.py`).
- Wer wartet: `process_normal_message` ruft `wait()` für beide Jobs in einem
  `finally`, damit nach einer Nachricht nie noch ein Schreibvorgang aus der
  vorherigen Nachricht läuft.
- Die Wartezeit hat eine Obergrenze durch die Timeouts der Modell-Aufrufe (60 s).

### Warum das sicher ist (geprüft im Code)

| Frage | Antwort |
|-------|---------|
| Greifen zwei Threads auf dasselbe zu? | Thread A schreibt in `memory.memories` und in die Tabelle `memories`; Thread B schreibt `project.md`. Der Hauptthread liest beides erst **vorher** als Text und danach nicht mehr bis zum `wait()`. |
| Datenbank | Jede Funktion öffnet ihre eigene Verbindung (so lange, bis Step 2.5 kommt). Gleichzeitig offene Verbindungen sind bei Neon kein Problem. |
| OpenAI-Client | Der Client ist für mehrere Threads gedacht. |
| `ai_log` | schützt seine Liste mit einem Lock; die Namen der Aufrufe kommen aus den Funktionen, nicht aus dem Thread. Die Summe "KI-Zeit" kann jetzt größer sein als die Gesamtzeit, das wird in der Ausgabe so benannt. |
| Zwei Nachrichten gleichzeitig? | Der Server bearbeitet Nachrichten nacheinander (`message_lock`), das CLI sowieso. Projekt und Konversation ändern sich also nicht, während die Threads laufen. |
| Reihenfolge im Verlauf und in der DB | Nur der Hauptthread schreibt Nachrichten (Nutzer vor der Antwort). Unverändert. |

## Tests (`test/test_parallel.py` und Anpassungen)

1. `Job`: Ergebnis, Fehler, `wait()` wirft nicht, Daemon-Thread.
2. **Gleichzeitigkeit beweisen:** Die Fakes für Memory, Projekt und Antwort warten
   gegenseitig auf einander (jede meldet "ich laufe" und wartet auf die beiden anderen,
   mit Timeout). Nacheinander ausgeführt würde der Test scheitern.
3. Die Antwort bekommt die **Momentaufnahme** (Memory und Projekt-Text ohne die Fakten
   dieser Nachricht).
4. Nach `process_message` sind Memory- und Projekt-Schreibvorgang fertig (kein
   Nachläufer), auch wenn `ask_jarvis` einen Fehler wirft.
5. Fehler in Memory oder Projekt-Prüfung: Antwort kommt trotzdem, Fehler in der Konsole.
6. Rückfrage wird angehängt, `pending_project_confirmation` stimmt, ohne Projekt
   kein Projekt-Job, bei ausgeschaltetem Memory kein Memory-Job.
7. Gegenprobe: Den Code absichtlich wieder nacheinander laufen lassen, Test 2 muss
   scheitern.

## Messung 3

Gleiche zehn Nachrichten wie bisher, diesmal mit `ja` nach der Python-Entscheidung.
Zielwerte: Chat ohne Projekt unter 3,5 s, Chat mit Projekt unter 4,5 s.

## Rückweg

Tag `mark4.vor-parallel` auf dem Commit vor dem Umbau.
