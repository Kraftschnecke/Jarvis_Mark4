# Step 5.1: Planformat

## Idee
Ein Plan ist **kein Text, den Jarvis ausführt**, sondern eine geprüfte Liste von Schritten.
Jeder Schritt ist genau eine bekannte Aufgabe (Task aus der Registry) mit Parametern.

```json
{
  "goal": "Notepad starten und die Uhrzeit sagen",
  "steps": [
    {"task_type": "START_PROGRAM", "parameters": {"program": "notepad"}},
    {"task_type": "GET_TIME", "parameters": {}}
  ]
}
```

Ein Parameter ist ein Text, eine Zahl oder ein Verweis auf das Ergebnis eines früheren Schritts:
`{"from_step": 1}` (Zählung ab 1).

## Zwei Dateien
- `plan.py`: das Format und **das einzige Tor** `parse_plan()`. Rohe Modell-Antwort rein, geprüfter `Plan`
  oder `PlanError` mit verständlicher Begründung raus. Außerdem `plan_risk()` (höchste Stufe aller Schritte, aus 4.2).
- `planner.py`: `create_plan(client, message, registry)` fragt das Modell nach einem Vorschlag und schickt ihn
  durch `parse_plan()`. Ergebnis: `(plan, None)` oder `(None, Grund)`. **Führt nichts aus.**

## Regeln (alle getestet)
| Regel | Warum |
|-------|-------|
| höchstens 6 Schritte, mindestens 1 | ein Plan, der sich ins Unendliche verlängert, ist kein Plan |
| nur registrierte Aufgaben, sonst Fehler | nie raten, nie die "ähnlichste" Aufgabe nehmen |
| nur Parameter, die die Aufgabe kennt, und alle gesetzt | ein erfundener Parameter (z. B. `path`) ist ein Warnzeichen |
| Parameter, die in der Aufgabe aus dem Vorergebnis kommen (Pfad bei `START_PROGRAM`), darf der Plan nicht setzen | sonst könnte das Modell am Freigabe-Mechanismus vorbei einen Pfad einschleusen |
| Werte: Text bis 500 Zeichen ohne Steuer-/Unsichtbar-Zeichen, endliche Zahl, oder `from_step` | keine verschachtelten Objekte, kein Code |
| `from_step` nur auf einen **früheren** Schritt | keine Zyklen, kein Blick in die Zukunft |
| zusätzliche Felder (z. B. `reasoning`) werden nicht übernommen | im Plan steht nur, was geprüft wurde |

## Zusammenspiel mit 4.1 und 4.2
- Die Antwort des Modells ist **unvertraute Eingabe**. Ungültiges wird verworfen, nie "repariert".
- Die Risikostufen gelten weiter: `plan_risk()` zeigt vorab, ob ein Plan Rückfrage braucht oder verboten ist.
  Ist ein Wert erst aus einem früheren Schritt bekannt (z. B. der Pfad bei `OPEN_FILE`), kann das vorab nicht
  entschieden werden: Der Plan gilt dann mindestens als `confirm`, und Step 5.2 prüft den Schritt **unmittelbar
  vor der Ausführung** noch einmal (der Executor tut das ohnehin).
- Der Planer ist **noch nicht** an den Chat angeschlossen: Nachrichten laufen wie bisher über den Router.
  Der Anschluss (und das Anzeigen vor dem Start) ist Step 5.3.

## Ausprobieren mit dem echten Modell (ohne etwas auszuführen)
```
py show_plan.py "Starte Notepad und sag mir die Uhrzeit"
py show_plan.py "Suche das Wetter in Växjö und stelle einen Timer auf 5 Minuten"
py show_plan.py "Formatiere meine Festplatte"        <- erwartet: kein Plan
```

## Bekannte Grenzen
- Das Modell kann einen *gültigen*, aber unsinnigen Plan vorschlagen (z. B. falsche Reihenfolge). Deshalb wird
  der Plan in 5.3 vor dem Start angezeigt.
- Verweise (`from_step`) liefern das Ergebnis des Schritts als Ganzes; ob es zum Parameter passt (Text, Zahl),
  entscheidet erst die Aufgabe bei der Ausführung (5.2).
