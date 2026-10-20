# Mark 3 -- Step 27: CLI-Abnahmetest

Dauer: ca. 30 bis 40 Minuten. Du gehst einmal durch alles, was Jarvis im Alltag können soll,
und prüfst, ob es klappt. Die automatischen Tests (`py run_tests.py`) prüfen die Logik mit Fakes.
Dieser Test prüft das, was sie nicht sehen: echtes Modell, echte Datenbank, echtes Windows.

## So gehst du vor

- Tippe die Zeilen unter **Eingabe** genau so ein (in der Spalte als Code).
- Vergleiche mit **Erwartet**. Hake `[x]` bei OK. Bei Abweichung: kurz notieren, was passiert ist.
- Zeilen mit **(KI)**: Das Sprachmodell entscheidet, was es daraus macht. Weicht es ab, formuliere
  einmal um oder wiederhole. Erst wenn es **zweimal** falsch ist, zählt es als Fehler.
- Reihenfolge einhalten: Spätere Abschnitte bauen auf früheren auf.

## Vorbereitung

- [ ] `py run_tests.py` zeigt `13 von 13 Test-Dateien bestanden.`
- [ ] `.env` ist ausgefüllt (`OPENAI_API_KEY`, `DATABASE_URL`, `BRAVE_API_KEY`).
- [ ] `settings.json` liegt im Projektordner direkt neben `main.py` (`Jarvis_Mark3\settings.json`). Darin `"memory": { "enabled": true }`.
- [ ] Testdatei angelegt: `C:\Users\morit\Desktop\jarvis_test.txt` mit dem Text `Hallo vom Abnahmetest`.
- [ ] Aktuelle Windows-Lautstärke gemerkt: ______ %
- [ ] Optional: Neon-Konsole (SQL Editor) in einem Browserfenster offen.

Start: `py main.py`

---

## A. Grundfunktion

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| A1 | `Hallo, wer bist du?` | Antwortet als J.A.R.V.I.S. und sagt "Sir" | [ ] |
| A2 | `Was ist die Hauptstadt von Schweden?` | Stockholm | [ ] |
| A3 | `Und wie viele Einwohner hat sie ungefähr?` | Bezieht sich auf Stockholm (Gesprächskontext) | [ ] |
| A4 | nur **Enter** drücken | Nichts passiert, neuer `You:`-Prompt | [ ] |
| A5 | `asdkjh qwe poiu` | Normale Antwort oder Rückfrage, kein Absturz | [ ] |

## B. Memory

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| B1 | `Mein Lieblingstier ist der Axolotl.` | Normale Antwort | [ ] |
| B2 | `Was ist mein Lieblingstier?` | Axolotl | [ ] |
| B3 | `exit`, dann `py main.py` neu starten | `Shutting down, Sir`, danach läuft Jarvis wieder | [ ] |
| B4 | `Was ist mein Lieblingstier?` | Axolotl (Memory überlebt den Neustart) | [ ] |
| B5 | Optional, Neon: `SELECT key, value, type FROM memories;` | Eintrag mit "Axolotl", type `preference` oder `fact` | [ ] |
| B6 | `exit`. In `settings.json` `"enabled": false` setzen. `py main.py`. Dann: `Was ist mein Lieblingstier?` | Jarvis weiß es **nicht** (Memory aus) | [ ] |
| B7 | `Mein Lieblingsessen ist Lasagne.` | Normale Antwort | [ ] |
| B8 | `exit`. `"enabled": true` zurücksetzen. `py main.py`. Dann: `Was ist mein Lieblingstier?` | Axolotl wieder bekannt | [ ] |
| B9 | `Was ist mein Lieblingsessen?` | Weiß es **nicht** (war ausgeschaltet, nichts gespeichert) | [ ] |

## C. Projekte und Konversationen

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| C1 | `Erstelle ein Projekt Abnahmetest` | `I created the project Abnahmetest with ID: <n>, Sir.` -- ID notieren: ____ | [ ] |
| C2 | `Öffne ein Projekt` (ohne Namen) | `I couldn't find a matching project, Sir.` | [ ] |
| C3 | `Öffne Projekt abnahmetest` (klein geschrieben) | Projekt geöffnet, neue Unterhaltung gestartet | [ ] |
| C4 | `Erstelle Konversation Test A` | `I created a new conversation Test A in Abnahmetest, Sir.` | [ ] |
| C5 | `Das ist meine erste Nachricht in Test A.` | Normale Antwort | [ ] |
| C6 | `Benenne Konversation Test A um in Test B` | `I renamed the conversation from Test A to Test B, Sir.` | [ ] |
| C7 | `Öffne Konversation Neue Unterhaltung`, dann `Was war meine erste Nachricht hier?` | Geöffnet. Jarvis kennt hier keine frühere Nachricht | [ ] |
| C8 | `Öffne Konversation Test B`, dann `Was war meine erste Nachricht in dieser Unterhaltung?` | Bezieht sich auf "Das ist meine erste Nachricht in Test A." | [ ] |
| C9 | `exit`, `py main.py`, dann `Öffne Projekt Abnahmetest` | Liste mit 2 Konversationen (Test B und Neue Unterhaltung) | [ ] |
| C10 | `Öffne Konversation Test B`, dann `Worüber haben wir gesprochen?` | Verlauf ist nach dem Neustart wieder da | [ ] |
| C11 | `Setze die Konversation zurück`, dann `Was war meine erste Nachricht?` | `Conversation reset, Sir`. Danach weiß Jarvis nichts mehr davon | [ ] |

## D. Projektkontext und Rückfrage

Projekt `Abnahmetest` und eine Konversation müssen offen sein (nach C11 der Fall).
Den Text zum Prüfen zeigt `py show_project.py <ID aus C1>` (in einem zweiten Terminal).

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| D1 | (KI) `Unser Ziel ist ein Roboter, der Socken sortiert.` | Normale Antwort **und** darunter: `Sir, soll ich das im Project Context unter "Goal" festhalten? ... (ja / nein)` | [ ] |
| D2 | `ja` | `Verstanden, Sir. Ich habe die Information in Project Context gespeichert.` | [ ] |
| D3 | `py show_project.py <ID>` ausführen | Unter `## Goal` steht ein Eintrag zum Socken-Roboter | [ ] |
| D4 | (KI) `Wir sollten Python für die Steuerung nehmen.`, dann `nein` | Rückfrage (Decisions). Nach `nein`: `... nicht gespeichert`. Im Text von `show_project.py` steht es **nicht** | [ ] |
| D5 | (KI) `Wir sollten Rust für die Steuerung nehmen.`, dann statt ja/nein: `Wie spät ist es?`, danach `ja` | Zeit wird genannt. Das spätere `ja` speichert **nichts** (Rückfrage ist verfallen) | [ ] |
| D6 | (KI) `Die Sockenerkennung ist fertig.` | Wird **ohne Rückfrage** gespeichert (steht danach unter `## Current Status` oder `## Progress`, beides ist richtig) | [ ] |
| D7 | `Was ist unser Projektziel?` | Nennt den Socken-Roboter (Projektkontext wird genutzt) | [ ] |
| D8 | `Schließe das Projekt`, dann `Was ist unser Projektziel?` | `Closing project Abnahmetest, Sir`. Danach weiß Jarvis es nicht | [ ] |

## E. Tasks

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| E1 | `Wie spät ist es?` | Korrekte Uhrzeit | [ ] |
| E2 | `Welches Datum haben wir heute?` | Heutiges Datum | [ ] |
| E3 | `Was ist 12 mal 7 minus 4?` | 80 | [ ] |
| E4 | `Was ist minus 5 plus 3?` | -2 | [ ] |
| E5 | `Was ist 10 geteilt durch 0?` | Freundliche Fehlermeldung, kein Absturz | [ ] |
| E6 | `Gib mir Infos über meinen Computer.` | Passende Angaben (System, Prozessor, Speicher) | [ ] |
| E7 | `Welche Programme laufen gerade?` | Plausible Liste (z.B. python.exe, explorer.exe) | [ ] |
| E8 | `Stelle die Lautstärke auf 30 Prozent.` | Windows-Lautstärke steht wirklich auf 30 % | [ ] |
| E9 | `Stelle die Lautstärke auf 50 Prozent.` | Windows-Lautstärke steht auf 50 %. Danach auf deinen Wert von oben zurückstellen | [ ] |

## F. Programme und Dateien

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| F1 | `Starte Notepad.` | Notepad öffnet sich | [ ] |
| F2 | (KI) `Öffne den Editor.` | Notepad öffnet sich (wird wie "Starte Notepad" behandelt) | [ ] |
| F3 | `Starte Chrome.` (nur wenn Chrome **nicht** in `programs.json` steht) | Nichts startet. Jarvis sagt, dass er das Programm nicht kennt / nicht freigegeben ist | [ ] |
| F4 | Eigenes Spiel in `programs.json` eintragen (Vorlage: `programs.example.json`, Pfade mit `/`), `py main.py` neu, dann `Starte <Name>` | Das Spiel startet | [ ] |
| F5 | `Öffne die Datei C:\Users\morit\Desktop\jarvis_test.txt` | Datei öffnet sich, Text `Hallo vom Abnahmetest` | [ ] |
| F6 | `Öffne die Datei C:\Windows\System32\calc.exe` | Rechner startet **nicht**. Jarvis erklärt, dass er Programmdateien nicht als Datei öffnet | [ ] |
| F7 | `Öffne die Datei C:\gibt\es\nicht.txt` | Freundliche Fehlermeldung, kein Absturz | [ ] |

## G. Web

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| G1 | `Suche im Web: Wer ist aktuell Bundeskanzler von Deutschland?` | Antwort aus den Suchergebnissen, in eigenen Worten (keine Rohdaten) | [ ] |
| G2 | `Suche im Web nach: qwxzvbnm4711fjkdl` | Ehrliche Antwort, dass nichts Brauchbares gefunden wurde | [ ] |

## H. Timer und Hintergrund

| # | Eingabe | Erwartet | OK |
|---|---------|----------|----|
| H1 | `Starte einen Timer für 10 Sekunden.` | Bestätigung, dass der Timer läuft | [ ] |
| H2 | sofort danach: `Was ist die Hauptstadt von Norwegen?` | Oslo -- Jarvis bleibt während des Timers bedienbar | [ ] |
| H3 | nach etwa 10 Sekunden, **ohne etwas einzugeben** | Von selbst erscheint: `J.A.R.V.I.S. Background: Sir, der Timer ist nach 10 Sekunden abgelaufen.` | [ ] |

## I. Fehlerfälle

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| I1 | Internet trennen (WLAN aus oder Kabel raus), dann `Hallo` | `Sir, bei der Verarbeitung ist ein Fehler aufgetreten (...). Bitte versuche es noch einmal.` Jarvis läuft weiter | [ ] |
| I2 | Internet wieder an, `Hallo` | Normale Antwort | [ ] |
| I3 | **Strg+C** am leeren `You:`-Prompt (nichts tippen, keine Anfrage am Laufen) | Programm beendet sich mit `Shutting down, Sir`, ohne Traceback. Auch Strg+C mitten in einer Anfrage darf nur diese Zeile zeigen | [ ] |
| I4 | `py main.py`, dann `exit` | `Shutting down, Sir`, Eingabeaufforderung kommt zurück | [ ] |

---

## Aufräumen

- [ ] Windows-Lautstärke wieder auf deinen Wert gestellt.
- [ ] Memory-Testeintrag entfernen: im Neon SQL Editor erst `SELECT key, value FROM memories;`, dann den Axolotl-Eintrag mit `DELETE FROM memories WHERE key = '<der key>';` löschen. Falls Lasagne dort steht (B7 hätte nichts speichern dürfen), melde mir das.
- [ ] Das Projekt `Abnahmetest` kannst du im GUI-Test (Step 28) wieder löschen.

## Ergebnis

Anzahl der Abweichungen: ____

Schick mir für jede Abweichung: die Nummer (z.B. `D5`), was du eingegeben hast und was Jarvis geantwortet
oder getan hat. Damit finde ich die Ursache.
