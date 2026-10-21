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

---

# Step 5.2: Plan ausführen (`plan_executor.py`)

`execute_plan(plan, registry, approved=(), should_abort=None, max_steps=6, max_seconds=120)` arbeitet einen
geprüften Plan Schritt für Schritt ab und gibt einen `PlanRun` zurück (Status je Schritt, Gesamtstatus,
Fehlertext). Jeder Schritt läuft über `task_executor.execute_task`, also durch dieselben Risikostufen (4.2)
und ins selbe Aktionsprotokoll (4.3) wie jede einzelne Aufgabe.

## Grenzen
| Grenze | Verhalten |
|--------|-----------|
| Schrittlimit | mehr als `max_steps` (Standard 6): Plan wird gar nicht begonnen (`BLOCKED`) |
| Zeitlimit | Gesamtdauer über `max_seconds` (Standard 120 s), geprüft vor jedem Schritt: `ABORTED` |
| Abbruch | `should_abort()` wird vor jedem Schritt gefragt. `True` oder ein Fehler darin: `ABORTED`, im Zweifel wird nicht ausgeführt |
| Fehler | ein fehlgeschlagener Schritt beendet den Plan (`FAILED`); der Rest ist `SKIPPED`. Nie "trotzdem weiter" |
| Ungültiger Plan | auch ein von Hand gebauter Plan läuft noch einmal durch `parse_plan` (`BLOCKED`) |

Status eines Plans: `COMPLETED`, `FAILED`, `ABORTED`, `BLOCKED`. Status eines Schritts: `COMPLETED`, `FAILED`, `BLOCKED`, `SKIPPED`.

## Ergebnis eines Schritts für den nächsten (`{"from_step": n}`)
Weitergegeben wird nur ein **einfacher Wert**: Text (bis 500 Zeichen, ohne Steuer-/Unsichtbar-Zeichen) oder eine Zahl.
Eine **Liste oder ein Objekt wird nie weitergegeben**. Das ist die wichtigste Regel gegen Prompt Injection (4.1):
Die Websuche liefert eine Liste von Treffern, also kann Text aus dem Internet nicht zum Dateipfad, Programmnamen
oder Suchbegriff eines späteren Schritts werden.

## Risikostufen im Plan (zusammen mit 4.2)
- **Verboten** läuft nie. Ist es vorab erkennbar, läuft gar nichts, nicht einmal die harmlosen Schritte davor.
- **confirm** läuft nur, wenn die Schrittnummer in `approved` steht **und** der Wert schon vor dem Start feststand.
  Ein Wert, der erst aus einem früheren Schritt kommt, wurde dir nie gezeigt: Ein solcher Plan wird nicht begonnen.
- `confirmable_steps(plan, registry)` liefert die Nummern, die du vorab freigeben kannst. Step 5.3 zeigt sie dir an.
- Zweite Sicherung: Der Executor prüft jeden Schritt unmittelbar vor der Ausführung noch einmal mit den echten Werten.

## Ausprobieren (echter Rechner, echte Aktionen)
```
py run_plan.py "Starte Notepad und sag mir die Uhrzeit"
py run_plan.py "Stelle einen Timer auf 1 Minute und sag mir das Datum"
```
Es erscheint der Plan, dann `Ausfuehren? (ja/nein)`. Bei `nein` passiert nichts. Danach stehen die Schritte
unter Settings > Activity.

## Noch nicht enthalten
- Anschluss an den normalen Chat und das Web, Anzeige vor dem Start mit Knöpfen, Abbrechen-Knopf: Step 5.3.
- Eine zusammenfassende Antwort von Jarvis nach dem Plan: Step 5.3.

---

# Step 5.3: Plan im Chat und im Web

## Ablauf
```
Nachricht -> Router (ein Aufruf): COMMAND | TASK | PLAN | CHAT
PLAN      -> Planer (zweiter Aufruf, nur hierfür) -> parse_plan -> Vorab-Prüfung
          -> Plan wird ANGEZEIGT  (status "plan")        <- erst jetzt weiß der Nutzer, was kommt
          -> "Plan ausführen" / "ja"  -> execute_plan -> Zusammenfassung von Jarvis
          -> "Abbrechen" / "nein"     -> nichts passiert
```
- **PLAN nur bei klar mehreren Aufgaben nacheinander.** Reicht eine Aufgabe, bleibt es `TASK`. Im Zweifel `CHAT`.
- **Zusätzlicher Modell-Aufruf nur für PLAN-Nachrichten.** Alle anderen Nachrichten kosten weiter einen Router-Aufruf.
  Der Plan selbst kommt vom Planer (5.1), nicht vom Router, damit der Router-Prompt klein bleibt.
- **Jeder Plan wird vor dem Start gezeigt**, auch ein ganz harmloser. Schritte, die dein Ja brauchen, sind markiert.
- **Vorab abgelehnt**, ohne Rückfrage, mit fester Antwort: Pläne mit verbotenem Schritt, Pläne mit einem Rückfrage-Schritt,
  dessen Wert erst aus einem früheren Schritt kommt (kann dir vorher nicht gezeigt werden), und ungültige Pläne.

## Freigabe
- Dein "Plan ausführen" (oder `ja` im Chat/CLI) gibt genau die angezeigten Rückfrage-Schritte frei (`confirmable_steps`).
  Alles andere entscheidet weiter `risk.py` unmittelbar vor jedem Schritt.
- Gleiche Regeln wie bei Einzelaktionen (4.2): Nummer des Plans muss stimmen, einmal benutzbar, 300 s gültig,
  jede andere Nachricht und jeder Wechsel von Projekt/Konversation verwirft den Plan, nur echtes JSON-`true` führt aus.
- Abgelehnt: Schritte, die eine Rückfrage gebraucht hätten, stehen als "von dir abgelehnt" im Aktionsprotokoll (4.3).
  Verbotene Schritte stehen als "verboten" drin.

## Stopp
- Während ein Plan läuft, zeigt das Web "Plan läuft …" und einen **Stopp**-Knopf. Er setzt nur einen Merker; der Plan
  hält **vor dem nächsten Schritt** an (ein laufender Schritt wird nicht mitten drin zerschnitten).
- Technik: `/api/plan/abort` läuft bewusst **ohne** die Sperre, die der laufende Plan hält, sonst käme der Stopp nie an.
  Der Merker gilt nur für diesen Lauf.

## Zusammenfassung
`respond_to_plan` (brain.py) fasst den Lauf zusammen, wie `respond_to_task` bei Einzelaufgaben: Ergebnisse und Fehlertexte
stehen als unvertraute Daten im Prompt (4.1). Die Antwort ist nur Text. Sie fließt in keinen Router, kein Memory, keine
Ausführung. Das prüft `test_plan_chat.py` mit einem Modell, das jede Anweisung befolgt.

## Neue/geänderte Dateien
`plan_view.py` (Anzeige), `plan_executor.find_blocker` (Vorab-Prüfung, auch für die Anzeige), `router.py` (Art PLAN),
`brain.respond_to_plan`, `jarvis.py` (`run_plan_request`, `confirm_plan`, `abort_plan`), `server.py`
(`/api/plan/confirm`, `/api/plan/abort`), `web/app.js` + `style.css` (Knöpfe, Stopp).

## Bekannte Grenzen
- Der Stopp wirkt zwischen den Schritten. Ein einzelner langsamer Schritt (z. B. Websuche mit Timeout) läuft zu Ende.
- Der Router muss "mehrere Aufgaben" erkennen. Erkennt er es nicht, wird nur die erste Aufgabe erledigt (TASK).
  Das ist die sichere Richtung. Prompt und Beispiel lassen sich später nachschärfen.
- Ein Plan hat höchstens 6 Schritte und läuft höchstens 120 Sekunden.
