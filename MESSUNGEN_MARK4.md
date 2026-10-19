# Messungen Mark 4

Gemessen mit dem Zeit-Log (`JARVIS_TIMING=1`, siehe `ai_log.py`). Dieses Dokument
sammelt die Zahlen "vorher" und "nachher", damit jede Beschleunigung belegt ist.

---

## Messung 1: Ausgangszustand (Stand Mark 3, Step 2.1)

Datum: 2026-10-20. Web-Oberfläche, Memory an, Rechner in Schweden (Neon-Datenbank
und OpenAI-Server sind weiter weg, das macht jeden Aufruf etwas langsamer).
Zehn Nachrichten nacheinander, ein Projekt mit einer Konversation offen.

| # | Nachricht | KI-Aufrufe | Gesamt | davon KI | Rest (DB, Web, ...) |
|---|-----------|-----------:|-------:|---------:|--------------------:|
| 1 | Hallo, wie geht's? | 4 | 6.25 s | 6.25 s | 0.00 s |
| 2 | Wie spät ist es? | 3 | 3.29 s | 3.29 s | 0.00 s |
| 3 | Was ist 15 mal 23? | 3 | 5.71 s | 5.71 s | 0.00 s |
| 4 | Ich trinke gerne Kaffee. | 4 | 6.47 s | 6.15 s | 0.32 s |
| 5 | Öffne Projekt Webtest2 | 1 | 3.56 s | 1.61 s | 1.95 s |
| 6 | Öffne Konversation Erste | 1 | 1.92 s | 1.36 s | 0.56 s |
| 7 | Wir entscheiden uns für Python ... (Projekt offen) | 5 | 10.91 s | 9.90 s | 1.01 s |
| 8 | Suche im Web nach dem Wetter in Växjö. | 3 | 6.03 s | 4.97 s | 1.06 s |
| 9 | Erkläre mir kurz, wie ein Timer funktioniert. (Projekt offen) | 5 | 7.68 s | 6.97 s | 0.71 s |
| 10 | Stelle einen Timer auf 10 Sekunden. | 3 | 3.71 s | 3.70 s | 0.01 s |
| | **Summe** | **32** | **55.53 s** | **49.91 s** | **5.62 s** |

### Pro Art von Aufruf

| Aufruf | Anzahl | Zeit gesamt | Durchschnitt | Eingabe-Tokens (je Aufruf) | Wofür |
|--------|-------:|------------:|-------------:|---------------------------:|-------|
| `command.detect_command` | 10 | 16.13 s | 1.61 s | ca. 525 | Ist es ein Befehl (Projekt öffnen ...)? |
| `task_recognizer.recognize_task` | 8 | 9.28 s | 1.16 s | ca. 800 | Passt eine Aufgabe (Zeit, Rechnen ...)? |
| `memory.analyze` | 4 | 6.46 s | 1.62 s | ca. 345 | Gibt es etwas zu merken? |
| `project_analyzer.analyze_project_message` | 2 | 3.10 s | 1.55 s | 269 | Gehört etwas ins Projekt? |
| `brain.respond_to_task` | 4 | 5.76 s | 1.44 s | 277 bis 2173 | Antwort aus einem Aufgaben-Ergebnis |
| `brain.ask_jarvis` | 4 | 9.17 s | 2.29 s | 140 bis 613 | Die eigentliche Antwort im Chat |

### Was die Zahlen zeigen

1. **Nur 30 % der KI-Zeit gehen in die Antwort** (`respond_to_task` + `ask_jarvis`:
   14.93 s von 49.91 s). Die anderen 70 % (35 s) sind Vorarbeit: Befehl erkennen,
   Aufgabe erkennen, Memory prüfen, Projekt prüfen.
2. **Jeder Aufruf kostet ungefähr eine Sekunde, egal wie klein er ist.** Die
   Prüf-Aufrufe geben nur 10 bis 40 Tokens aus und brauchen trotzdem 1 bis 2 s.
   Die Zeit steckt also in Wartezeit pro Aufruf, nicht in der Textlänge. Deshalb
   zählt vor allem die **Anzahl hintereinander laufender Aufrufe**.
3. **Eine normale Chat-Nachricht braucht 4 Aufrufe, mit offenem Projekt 5**
   (6 bis 11 s). Eine Nachricht mit 5 Aufrufen dauerte 7.7 bis 10.9 s.
4. **Die beiden Prüf-Aufrufe vorne (Befehl, Aufgabe) sind die teuersten Eingaben:**
   zusammen 11 641 von 18 009 Eingabe-Tokens (65 %), weil jedes Mal die ganze
   Befehls- bzw. Aufgabenliste mitgeschickt wird.
5. **Datenbank:** "Öffne Projekt" brauchte 1.95 s außerhalb der KI. Das passt zu
   "jede Datenbankfunktion baut eine eigene Verbindung auf" (Step 2.4).
   Die Websuche brauchte ca. 1 s außerhalb der KI (Brave).
6. Nicht gemessen: `ja`/`nein` auf eine Rückfrage (Nachricht 7 meiner Liste). Sie sollte
   0 KI-Aufrufe brauchen und kann bei der nächsten Messung mitlaufen.

### Zielwerte für Step 2.3 (Vorschlag)

- Normale Chat-Nachricht: höchstens **2 hintereinander laufende** Wartezeiten
  (vorher 4 bis 5), Gesamtzeit unter 4 s (vorher 6 bis 11 s).
- Befehle und Aufgaben: 1 bis 2 Aufrufe (vorher 3 bis 5).
- Gleiche zehn Nachrichten wie oben, gleiche Bedingungen, Ergebnis hier als
  "Messung 2" eintragen.

---

## Messung 2: nach Step 2.3

_noch nicht gemessen_
