# Step 4.2: Risikostufen und Rückfrage

## Idee
Jede Action hat eine Stufe (`risk.py`):

| Stufe | Bedeutung | Beispiele |
|-------|-----------|-----------|
| `safe` | läuft sofort | Uhrzeit, Datum, Rechnen, Systeminfo, laufende Programme, Programm suchen, Websuche, Timer, Lautstärke |
| `confirm` | erst fragen, nur nach "Ja" ausführen | `open_program` (Programm starten), `open_file` (Datei öffnen) |
| `forbidden` | nie, auch nicht auf Nachfrage | jede Action ohne Eintrag in der Tabelle; `open_file` auf Programmdateien (.exe, .bat, .ps1 ...), Web- und Netzwerkadressen |

Eine Task ist so riskant wie ihre riskanteste Action. `START_PROGRAM` (erst
`find_program`, dann `open_program`) ist deshalb `confirm`, und zwar als Ganzes:
vor dem "Ja" läuft auch die harmlose erste Action nicht.

## Warum so
- **Standard ist Nein.** Wer eine neue Action baut, muss sie einstufen. Der Test
  `test_risk.py` schlägt an, wenn eine Action im Executor nicht in der Tabelle steht.
- **Die Stufe hängt nur von Name und Parametern ab**, nie von dem, was das Modell sagt.
- **Durchgesetzt am Executor** (`task_executor.execute_task`), der einzigen Stelle,
  an der Actions laufen. `confirmed=True` muss bewusst übergeben werden; verbotene
  Tasks laufen auch dann nicht. Geprüft wird vor der ersten Action, nie halb ausgeführt.
- **Verboten fragt nicht erst.** Eine Frage "darf ich trojaner.exe öffnen?" wäre
  ein Angebot, das keinen Sinn hat. Jarvis sagt mit festem Text Nein (kein Modell dabei).
- Die Tool-Prüfungen aus Mark 3 (Freigabeliste `programs.json`, Dateiendungen) bleiben
  als zweite Schicht bestehen.

## Ablauf
1. Router erkennt eine Aufgabe (`run_task` in `jarvis.py`), Task wird vorbereitet, Stufe bestimmt.
2. `confirm`: Jarvis merkt sich die Task (`pending_action`, Zufalls-Nummer, 120 s gültig)
   und antwortet mit Status `confirmation`. Das Web zeigt Knöpfe **Ausführen** / **Abbrechen**,
   das CLI zeigt die Frage; dort antwortest du `ja` oder `nein`.
3. Antwort per Knopf: `POST /api/confirm {id, approve}`. Nur `approve: true` (echtes JSON-true)
   führt aus; alles andere zählt als Nein. Die Nummer muss zur offenen Rückfrage passen.
4. Antwort per Chat (`ja` / `nein`) geht nicht durch den Router.

## Wann eine Rückfrage verfällt
- Sie ist nach der ersten Antwort verbraucht (ein Klick = eine Ausführung).
- Jede andere Nachricht verwirft sie, ebenso ein Wechsel von Projekt oder Konversation.
- Eine neue Rückfrage ersetzt die alte (die alte Nummer gilt dann nicht mehr).
- Nach 120 Sekunden.

## Zusammenspiel mit 4.1 (Prompt Injection)
Eine Rückfrage entsteht nur aus **deiner** Nachricht über den Router. Text aus dem
Web kommt nie dorthin (4.1). Selbst wenn eine Antwort "ja" enthielte: Es gibt keine
offene Rückfrage, die sie beantworten könnte, und ein "ja" im Modelltext ist keine
Nutzer-Nachricht.

## Bekannte Grenzen
- Die Rückfrage zeigt Ziel und Parameter (z. B. den Dateipfad), nicht den Inhalt der Datei.
- Lautstärke ist `safe`: sofort wieder änderbar. Bei Bedarf einfach auf `confirm` stellen (eine Zeile in `risk.py`).
- Alle Entscheidungen laufen durch `risk.task_risk`: Step 4.3 (Aktionsprotokoll) hängt sich dort ein.
