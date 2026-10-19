# Mark 3 -- Abnahmetest der Web-Oberfläche

Dauer: ca. 20 Minuten. Der CLI-Test (`ABNAHMETEST_CLI.md`) hat Jarvis selbst geprüft. Hier geht es
um das, was die Oberfläche zusätzlich tut. Die automatischen Tests prüfen den Server mit Fakes,
dieser Test prüft Browser, echte Datenbank und echtes Modell zusammen.

## So gehst du vor

- Hake `[x]` bei OK. Bei Abweichung: kurz notieren, was passiert ist.
- Zeilen mit **(KI)**: Das Sprachmodell entscheidet. Erst wenn es **zweimal** falsch ist, zählt es als Fehler.
- Reihenfolge einhalten, spätere Abschnitte bauen auf früheren auf.

## Vorbereitung

- [ ] `py run_tests.py` zeigt `13 von 13 Test-Dateien bestanden.`
- [ ] Alte Reste gelöscht: Ordner `gui/`, `theme_manager.py`, `settings.py`, `project_structure.py/.json`.
- [ ] Start per Doppelklick auf `start_jarvis.bat` (oder `py server.py`). Der Browser öffnet `http://localhost:8000`.
- [ ] Optional: Testprojekt `Abnahmetest` aus dem CLI-Test ist noch da (sonst legst du in B ein neues an).

---

## A. Start und Chat

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| A1 | Seite öffnet sich | Dunkles Design, links Sidebar, rechts `Guten Tag, Sir. Wie kann ich helfen?`, Status `READY` | [ ] |
| A2 | `Was ist die Hauptstadt von Schweden?` + Enter | Während der Antwort `THINKING...`, dann Stockholm | [ ] |
| A3 | Text mit Shift+Enter über zwei Zeilen schreiben, dann Enter | Zwei Zeilen werden gesendet, Eingabefeld wird wieder klein | [ ] |
| A4 | nur Leerzeichen und Enter | Nichts wird gesendet | [ ] |
| A5 | `Schreibe mir **fett** und <b>html</b>` (KI) | `**fett**` wird fett, `<b>html</b>` bleibt sichtbarer Text (kein HTML) | [ ] |
| A6 | Seite mit F5 neu laden | Chat ist leer (ohne Projekt wird nichts gespeichert), Jarvis läuft weiter | [ ] |

## B. Sidebar: Projekte

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| B1 | Sidebar ansehen | Alle Projekte aus der Datenbank, alphabetisch. `New Conversation` ist grau | [ ] |
| B2 | `New Project`, Name `Webtest` | Projekt erscheint, ist blau (aktiv) und aufgeklappt, Zeile `＋ Neue Konversation` | [ ] |
| B3 | `New Project` mit demselben Namen in Kleinbuchstaben | Meldung im Dialog: `Ein Projekt mit diesem Namen gibt es schon.`, Dialog bleibt offen | [ ] |
| B4 | Abbrechen, dann ein anderes Projekt anklicken | Das andere Projekt ist aktiv, der Chat wird geleert | [ ] |
| B5 | Dasselbe (aktive) Projekt nochmal anklicken | Klappt zu/auf, Konversation und Chat bleiben | [ ] |
| B6 | Auf Projekt `Webtest` mit der Maus gehen, `＋` klicken, Titel `Erste` | Konversation `Erste` ist angelegt und aktiv, Chat zeigt die Begrüßung | [ ] |
| B7 | `⋯` am Projekt → `Rename Project` → `Webtest 2` | Name ändert sich in der Liste | [ ] |

## C. Konversationen und Verlauf

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| C1 | In `Erste`: `Merke dir das Wort Kaktus für diesen Chat.` | Normale Antwort | [ ] |
| C2 | `New Conversation` (oben), Titel `Zweite`, dort `Wie heißt das Wort von vorhin?` | Jarvis kennt hier keinen Verlauf aus `Erste` | [ ] |
| C3 | `Erste` anklicken | Der Verlauf von vorhin erscheint wieder, `Erste` ist blau | [ ] |
| C4 | Frage in `Erste`: `Welches Wort sollte ich mir merken?` | Kaktus | [ ] |
| C5 | Während Jarvis antwortet (lange Frage senden): Sidebar ansehen | Sidebar ist ausgegraut, nicht klickbar | [ ] |
| C6 | `⋯` an `Zweite` → `Rename` → `Zweite neu` | Titel ändert sich | [ ] |
| C7 | `⋯` an `Erste` → `Reset` → bestätigen | Chat leer (Begrüßung), Konversation bleibt in der Liste | [ ] |
| C8 | Rechtsklick auf `Zweite neu` → `Delete` → bestätigen | Konversation verschwindet | [ ] |
| C9 | Server beenden (Strg+C im Fenster), neu starten, Seite laden, Projekt und `Erste` anklicken | Nach C7 leer, nichts von früher (Reset ist gespeichert) | [ ] |
| C10 | (KI) In `Erste`: `Unser Ziel ist ein Roboter, der Socken sortiert.` | Antwort **und** darunter die Rückfrage `(ja / nein)`. Mit `ja` wird gespeichert | [ ] |
| C11 | Im Chat: `Öffne Projekt Abnahmetest` | Antwort steht im Chat, die Sidebar markiert danach das Projekt, und das Chatfenster zeigt den gespeicherten Verlauf der geöffneten Konversation (nicht den alten Chat) | [ ] |

## D. Einstellungen

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| D1 | Unten links `Settings` | Fenster mit 6 Kategorien, `General` offen, alles grau mit `Not available yet` | [ ] |
| D2 | Appearance → Theme `Light` | Sofort helles Design | [ ] |
| D3 | Seite mit F5 neu laden | Bleibt hell, ohne kurzes dunkles Aufblitzen | [ ] |
| D4 | Font size `18` (Tab drücken) | Schrift wird größer. Danach `99` → Fehlermeldung, Schrift bleibt | [ ] |
| D5 | Theme `System` | Folgt dem Windows-Design | [ ] |
| D6 | Theme zurück auf `Dark`, Font size `13` | Wie am Anfang | [ ] |
| D7 | Memory → `Memory enabled` ausschalten, dann im Chat nach deinem Lieblingstier fragen | Jarvis weiß es nicht. Danach wieder einschalten, dann weiß er es | [ ] |
| D8 | About | Version `Mark 3`, Python und Windows-Version stehen da | [ ] |
| D9 | Esc oder `Schließen` | Fenster geht zu | [ ] |

## E. Timer und Hintergrund

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| E1 | `Starte einen Timer für 10 Sekunden.` | Bestätigung | [ ] |
| E2 | sofort: `Was ist die Hauptstadt von Norwegen?` | Oslo | [ ] |
| E3 | nach ca. 10 Sekunden, ohne etwas zu tun | Von selbst erscheint eine blaue Blase `HINTERGRUND: Sir, der Timer ist nach 10 Sekunden abgelaufen.` | [ ] |
| E4 | Zweites Browserfenster mit derselben Adresse öffnen | Zeigt dieselben Projekte (der Chat ist pro Fenster) | [ ] |

## F. Fehlerfälle und Sicherheit

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| F1 | Server mit Strg+C beenden, im Browser etwas senden | Rote Meldung `Keine Verbindung ...`, Status `OFFLINE`. Nach Neustart und Senden geht es wieder | [ ] |
| F2 | WLAN aus, im Chat `Hallo` | Jarvis antwortet mit der Fehlermeldung (`Sir, bei der Verarbeitung ...`), Seite läuft weiter. WLAN wieder an | [ ] |
| F3 | Adresse `http://127.0.0.1:8000` statt localhost | Funktioniert | [ ] |
| F4 | Adresse `http://localhost:8000/../server.py` und `http://localhost:8000/.env` | Beides zeigt nur `Nicht gefunden` (kein Dateiinhalt!) | [ ] |
| F5 | Von einem anderen Gerät im WLAN `http://<IP deines Laptops>:8000` | Nicht erreichbar (der Server lauscht nur auf dem Laptop selbst) | [ ] |

## G. Schmales Fenster

| # | Aktion | Erwartet | OK |
|---|--------|----------|----|
| G1 | Browserfenster auf Handybreite ziehen (unter ca. 700 px) | Sidebar verschwindet, oben links erscheint `☰` | [ ] |
| G2 | `☰` klicken, Konversation wählen | Sidebar fährt aus und nach der Wahl wieder zu | [ ] |
| G3 | Settings im schmalen Fenster | Kategorien stehen oben nebeneinander, alles bedienbar | [ ] |

---

## Aufräumen

- [ ] Testprojekte `Webtest 2` (und ggf. `Abnahmetest`) löschen: `⋯` → Delete Project.
- [ ] Axolotl- und Pizza-Eintrag aus dem Memory entfernen, falls noch nicht geschehen.
- [ ] Theme auf `Dark`, Font size `13`, Memory an.

## Ergebnis

Anzahl der Abweichungen: ____

Schick mir für jede Abweichung die Nummer (z.B. `C5`), was du getan hast und was passiert ist.
Bei Fehlern im Browser hilft ein Screenshot oder die Ausgabe im Server-Fenster.
