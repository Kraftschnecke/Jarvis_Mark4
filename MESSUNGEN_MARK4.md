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

## Messung 2: nach Step 2.3 (Router, erste Fassung)

Datum: 2026-10-20, gleiche Bedingungen. Unterschiede zu Messung 1: Nachricht 7 lautete
nur "Wir entscheiden uns für Python" (kürzer), und das `ja` zur Rückfrage wurde wieder
nicht geschickt.

| # | Nachricht | Aufrufe (vorher → jetzt) | Gesamt (vorher → jetzt) | davon KI (jetzt) |
|---|-----------|-------------------------:|------------------------:|-----------------:|
| 1 | Hallo, wie geht's? | 4 → 3 | 6.25 → 4.70 s | 4.70 s |
| 2 | Wie spät ist es? | 3 → 2 | 3.29 → 3.45 s | 3.45 s |
| 3 | Was ist 15 mal 23? | 3 → 2 | 5.71 → 3.48 s | 3.48 s |
| 4 | Ich trinke gerne Kaffee. | 4 → 3 | 6.47 → 4.72 s | 4.40 s |
| 5 | Öffne Projekt Webtest2 | 1 → 1 | 3.56 → 2.15 s | 1.58 s |
| 6 | Öffne Konversation Erste | 1 → 1 | 1.92 → 2.14 s | 1.57 s |
| 7 | Wir entscheiden uns für Python (Projekt offen) | 5 → 4 | 10.91 → 7.26 s | 6.59 s |
| 8 | Suche im Web nach dem Wetter in Växjö. | 3 → 2 | 6.03 → 6.35 s | 5.33 s |
| 9 | Erkläre mir kurz, wie ein Timer funktioniert. (Projekt offen) | 5 → 4 | 7.68 → 6.38 s | 5.72 s |
| 10 | Stelle einen Timer auf 10 Sekunden. | 3 → 2 | 3.71 → 2.51 s | 2.51 s |
| | **Summe** | **32 → 24** | **55.53 → 43.14 s (−22 %)** | **39.33 s** |

KI-Zeit gesamt: 49.91 → 39.33 s (−21 %). Eingabe-Tokens des Routers: ca. 927 statt
523 + 796 = 1319 bei den beiden alten Aufrufen (−30 %).

### Router im Vergleich zu den alten Aufrufen

| | alt | Router |
|---|---:|---:|
| Chat / Aufgabe (zwei Aufrufe zusammen) | ca. 2.77 s (1.61 + 1.16) | ca. 2.01 s im Durchschnitt (1.48 bis 2.83 s) |
| Befehl (ein Aufruf) | 1.36 bis 1.61 s | 1.57 bis 1.58 s |

Prüfung der Erkennung (`router_check.py`, 32 Beispielsätze, echtes Modell): alt 32 von 32,
Router 32 von 32, inklusive Grenzfälle und Injection-Satz.

### Was die Zahlen zeigen

1. **Der Router spart pro Chat- oder Aufgaben-Nachricht ca. 0.8 s** und eine Eingabe von ca. 400 Tokens.
   Befehle sind nicht langsamer geworden (in `router_check.py` wirkte es so, im Betrieb nicht).
2. **Die Antwort des Routers ist zu lang:** 67 bis 220 Ausgabe-Tokens, die alten
   Prüf-Aufrufe brauchten 10 bis 40. Der Router schreibt immer alle sieben Felder mit
   vielen `null`. Das kostet Zeit (Nachrichten 2 und 8: 2.3 und 2.8 s für den Router).
   → Versuch 2.3b (nur zutreffende Felder ausgeben), siehe unten: gescheitert.
3. **Die Zielwerte aus Messung 1 sind teilweise erreicht:** Befehle und Aufgaben brauchen
   1 bis 2 Aufrufe (Ziel erreicht). Eine Chat-Nachricht braucht noch 3 (ohne Projekt)
   bzw. 4 (mit Projekt) hintereinander laufende Aufrufe statt höchstens 2 und liegt bei
   4.7 bis 7.3 s statt unter 4 s. Der Rest ist Memory- und Projekt-Prüfung: Step 2.4.
4. **Außerhalb der KI** lagen die Nachrichten diesmal bei 3.81 s (vorher 5.62 s).
   "Öffne Projekt" brauchte nur noch 0.57 s statt 1.95 s. Das schwankt also stark
   (vielleicht war die Datenbank vorher "kalt"). Die Messung muss vor Step 2.5
   (Verbindungspool) wiederholt werden, bevor man daraus Schlüsse zieht.
5. Die Websuche (Nachricht 8) ist wegen der Router-Antwort mit 220 Tokens und der
   langen Antwort aus den Suchergebnissen (2261 Eingabe-Tokens) weiter die langsamste
   Aufgabe.

---

## Versuch 2.3b: kürzere Router-Antwort (gescheitert, zurückgenommen)

Idee: Der Router soll nur die zutreffenden Felder ausgeben (`{"kind": "CHAT"}` statt
sieben Feldern mit `null`), um Ausgabe-Tokens und Zeit zu sparen.

Ergebnis von `router_check.py` mit dem geänderten Prompt: **15 von 32 richtig**
(vorher 32 von 32). Das Modell wählte fast immer `CHAT`, auch bei "Öffne Projekt Jarvis"
und "Wie spät ist es?". Wahrscheinliche Ursache: "so kurz wie möglich" und das kürzeste
Beispiel (`CHAT`) lenken das Modell zur kürzesten Antwort. Zeit pro Satz: 1.93 s, also
kein Gewinn.

Entscheidung: Prompt wieder auf die 32/32-Fassung zurückgesetzt. Die Kürzung der Antwort
wird nicht weiterverfolgt, bevor die größeren Hebel (Step 2.4) umgesetzt sind. Wenn
später ein neuer Versuch gemacht wird, dann nur mit `router_check.py` als Abnahme.

Das Skript hat seinen Zweck erfüllt: Tests mit Fakes hätten diesen Fehler nicht gefunden.

---

## Messung 3: nach Step 2.4 (Memory- und Projekt-Prüfung parallel)

Datum: 2026-10-20, gleiche Bedingungen wie Messung 2 (Nachricht 7 wieder die kurze
Fassung, das `ja` wurde nicht geschickt). Im Zeit-Log ist "KI-Zeit summiert" jetzt oft
größer als "gesamt", weil Aufrufe gleichzeitig laufen.

| # | Nachricht | Aufrufe | Gesamt: M1 → M2 → M3 | KI-Zeit summiert (M3) |
|---|-----------|--------:|---------------------:|----------------------:|
| 1 | Hallo, wie geht's? | 4 → 3 → 3 | 6.25 → 4.70 → **3.91 s** | 5.06 s |
| 2 | Wie spät ist es? | 3 → 2 → 2 | 3.29 → 3.45 → **2.95 s** | 2.95 s |
| 3 | Was ist 15 mal 23? | 3 → 2 → 2 | 5.71 → 3.48 → **4.00 s** | 4.00 s |
| 4 | Ich trinke gerne Kaffee. | 4 → 3 → 3 | 6.47 → 4.72 → **3.38 s** | 4.40 s |
| 5 | Öffne Projekt Webtest2 | 1 → 1 → 1 | 3.56 → 2.15 → **2.11 s** | 1.57 s |
| 6 | Öffne Konversation Erste | 1 → 1 → 1 | 1.92 → 2.14 → **2.61 s** | 2.03 s |
| 7 | Wir entscheiden uns für Python (Projekt offen) | 5 → 4 → 4 | 10.91 → 7.26 → **4.21 s** | 6.85 s |
| 8 | Suche im Web nach dem Wetter in Växjö. | 3 → 2 → 2 | 6.03 → 6.35 → **6.73 s** | 5.62 s |
| 9 | Erkläre mir kurz, wie ein Timer funktioniert. (Projekt offen) | 5 → 4 → 4 | 7.68 → 6.38 → **5.22 s** | 6.76 s |
| 10 | Stelle einen Timer auf 10 Sekunden. | 3 → 2 → 2 | 3.71 → 2.51 → **2.65 s** | 2.65 s |
| | **Summe** | **32 → 24 → 24** | **55.53 → 43.14 → 37.77 s** | 41.89 s |

Gesamt gegenüber Messung 1: **−32 %** (−17.8 s); gegenüber Messung 2: −12 % (−5.4 s).

### Zielwerte (aus DESIGN_PARALLEL.md)

| Ziel | Messwerte | erreicht? |
|------|-----------|-----------|
| Chat ohne Projekt unter 3,5 s | 3.91 s (Router-Ausreißer 2.59 s), 3.38 s | teilweise |
| Chat mit Projekt unter 4,5 s | 4.21 s, 5.22 s (Antwort 2.86 s) | teilweise |

### Was die Zahlen zeigen

1. **Die Parallelisierung wirkt**, wo sie wirken soll: Nachricht 7 (Chat mit Projekt)
   fiel von 7.26 auf 4.21 s, Nachricht 4 von 4.72 auf 3.38 s.
2. **Was jetzt noch dauert:** Der Router ist mit durchschnittlich 1.89 s (1.43 bis 2.59 s)
   die Hälfte der Gesamtzeit (18.9 von 37.8 s). Danach kommt die Antwort (1.3 bis 3.3 s).
   Eine Chat-Nachricht besteht nur noch aus diesen zwei Wartezeiten
   (Rechnung Nachricht 7: Router 1.83 + parallel 1.68 = 3.51 s).
3. **Rest außerhalb der KI:** Bei Nachrichten mit offenem Projekt bleiben ca. 0.7 s übrig
   (Nachricht 7: 4.21 − 3.51), das sind die Datenbank-Zugriffe (Nachrichten speichern,
   Verbindung pro Funktion). Ohne offene Konversation ist dieser Rest praktisch 0.
   "Öffne Projekt" und "Öffne Konversation": 0.5 bis 0.6 s außerhalb der KI.
   → Step 2.5 (Verbindungspool) hat messbaren Spielraum.
4. **Streuung:** Der Router schwankt zwischen 1.4 und 2.6 s, ohne dass sich der Prompt
   ändert. Die Ausgabe-Tokens (73 bis 136) liegen deutlich über den alten Prüf-Aufrufen.
   Einzelne Messungen (z. B. Nachricht 3: Antwort 2.57 s bei 131 Ausgabe-Tokens) sagen wenig,
   erst die Summe über zehn Nachrichten.
5. **Langsamste Aufgabe bleibt die Websuche** (6.73 s): 2261 Eingabe-Tokens und 303
   Ausgabe-Tokens in der Antwort.

## Messung 4: nach Step 2.5 (Verbindungspool)

Gleiche zehn Nachrichten, `ja` nach der Python-Entscheidung (diese Nachricht ist nur
eine Rückfrage-Antwort ohne KI-Aufruf), danach zweimal "Hallo".

| # | Nachricht | KI-Aufrufe | Gesamt | Router | Rest außerhalb der KI* |
|---|-----------|-----------:|-------:|-------:|-----------------------:|
| 1 | Hallo, wie geht's? | 3 | 4.79 s | 2.20 s | 0.00 s |
| 2 | Wie spät ist es? | 2 | 3.61 s | 2.22 s | 0.00 s |
| 3 | Was ist 15 mal 23? | 2 | 4.44 s | 2.44 s | 0.01 s |
| 4 | Ich trinke gerne Kaffee. | 3 | 3.27 s | 1.58 s | 0.00 s |
| 5 | Öffne Projekt Webtest2 | 1 | 2.22 s | 2.02 s | 0.20 s |
| 6 | Öffne Konversation Erste | 1 | 1.89 s | 1.68 s | 0.21 s |
| 7 | Wir sollten uns entscheiden für Python | 4 | 3.82 s | 1.86 s | 0.14 s |
| 8 | Suche im Web nach dem Wetter in Växjö. | 2 | 6.08 s | 2.43 s | 0.79 s** |
| 9 | Erkläre mir kurz, wie ein Timer funktioniert. | 4 | 3.49 s | 1.54 s | 0.27 s |
| 10 | Stelle einen Timer auf 10 Sekunden. | 2 | 2.81 s | 1.76 s | 0.00 s |

Summe der zehn Nachrichten: **36.42 s, 24 KI-Aufrufe** (Messung 3: 37.77 s, 24 Aufrufe).

\* Gesamt minus (Router + längster der danach folgenden Aufrufe), bei parallelen
Aufrufen also minus den längsten. Werte um 0.00 sind Rundung.
\*\* Websuche: Das ist die Laufzeit des Such-Werkzeugs selbst, kein Datenbank-Anteil.

### Zielwerte (aus DESIGN_POOL.md)

| Ziel | Messung 4 | Erreicht |
|------|-----------|----------|
| Nachrichten mit Projekt unter 3,6 s | 3.82 s, 3.49 s | teilweise |
| "Öffne Projekt" unter 1,8 s | 2.22 s | nein |

### Was die Zahlen zeigen

1. **Der Datenbank-Anteil ist von ca. 0.5 bis 0.7 s auf ca. 0.15 bis 0.3 s gefallen**
   (Nachricht 7: 0.7 → 0.14 s, "Öffne Projekt": 0.5–0.6 → 0.20 s, "Öffne Konversation":
   0.5–0.6 → 0.21 s). Das ist der Gewinn des Pools.
2. **Die beiden verfehlten Zielwerte liegen am Router, nicht an der Datenbank.** Bei
   "Öffne Projekt" sind 2.02 von 2.22 s der Router-Aufruf (Messung 3: 1.57 s für dieselbe
   Nachricht). Bei Nachricht 7 dauerte das langsamste parallele Modell 1.82 s. Die Ziele
   waren mit der Streuung der KI-Aufrufe (±0.5 s) zu knapp gesetzt; der Pool hat sein
   eigenes Ziel (Rest außerhalb der KI) erreicht.
3. **Die Gesamtsumme sinkt nur um 1.35 s (3,6 %)**, weil in diesem Lauf der Router langsamer
   war (Mittel 1.97 s statt 1.89 s). Der Pool spart in den vier Nachrichten mit
   Datenbank-Anteil (5, 6, 7, 9) zusammen ca. 1.5 s (vorher ca. 2.4 s Rest, jetzt 0.82 s).
   Mehr gibt es dort nicht zu holen.
4. **Neue Reihenfolge in den Zeilen:** Bei den Nachrichten 7 und "Hallo" stehen die
   parallelen Aufrufe in wechselnder Reihenfolge (sie enden zu unterschiedlichen
   Zeitpunkten). Das ist erwartet.
5. **`ja` kostet 0.00 s und keinen KI-Aufruf.** Die Rückfrage-Antwort wird ohne Modell
   erkannt, wie geplant.
6. **Was bleibt:** Der Router (Mittel 1.97 s) ist jetzt der größte einzelne Posten, danach
   die Antwort. Weitere Ersparnis gibt es nur noch durch kürzere Router-Eingabe
   (Versuch 2.3b ist gescheitert), eine spekulative Antwort oder Streaming.

### Ideen für später (nicht beschlossen)

- Streaming (Step 2.7): Die Antwort erscheint, sobald das erste Wort da ist. Spart keine
  Gesamtzeit, verkürzt aber die gefühlte Wartezeit bei langen Antworten deutlich.
- "Spekulative" Antwort: `ask_jarvis` schon während des Routers starten und verwerfen,
  wenn es ein Befehl oder eine Aufgabe war. Würde Chat-Nachrichten um fast die Router-Zeit
  verkürzen, kostet aber bei jeder Aufgabe einen unnötigen Aufruf. Erst bewerten, wenn
  der Anteil von Chat-Nachrichten im Alltag bekannt ist.
