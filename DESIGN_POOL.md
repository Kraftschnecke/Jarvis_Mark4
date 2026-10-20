# Design: Verbindungspool (Step 2.5)

Ziel: Nicht mehr für jede Datenbank-Funktion eine neue Verbindung zu Neon öffnen
(TLS + Anmeldung über das Netz), sondern Verbindungen aufheben und wiederverwenden.

Erwartung (aus Messung 3): Nachrichten mit offenem Projekt ca. 0,7 s schneller,
"Öffne Projekt/Konversation" ca. 0,3 bis 0,5 s schneller. Die erste Anfrage nach dem
Start bleibt gleich langsam (die erste Verbindung muss ja geöffnet werden).

## Entscheidung: eigene `db.py` statt `psycopg-pool`

| | psycopg-pool | eigene db.py |
|-|-|-|
| Neue Abhängigkeit | ja | nein |
| Verstehbar | Fremdcode | ca. 100 Zeilen, eine Datei |
| Funktionen, die wir brauchen | alle, plus viele, die wir nicht brauchen | genau die nötigen |

Wir brauchen: ausleihen, zurückgeben, Obergrenze, tote Verbindungen erkennen. Das ist
klein genug, um es selbst zu schreiben und zu verstehen. Ein Wechsel auf `psycopg-pool`
später ist leicht, weil nur `db.connect()` benutzt wird.

## Benutzung

```python
with db.connect() as connection:
    cursor = connection.cursor()
    cursor.execute(...)
```

Ende ohne Fehler: commit und zurück in den Pool. Fehler: rollback, Fehler wird weitergereicht.
`connection.commit()` und `connection.close()` gibt es im restlichen Code nicht mehr.

## Regeln

1. **Obergrenze 4** gleichzeitige Verbindungen (`MAX_CONNECTIONS`). Mehr braucht Jarvis nicht
   (Hauptthread + Memory-Job + Projekt-Job + Server). Ist alles belegt, wartet der Aufrufer
   bis zu 30 s, dann gibt es einen verständlichen Fehler.
2. **Eine Verbindung gehört immer nur einem Thread**, bis der Block endet.
3. **Neon trennt ruhende Verbindungen.** Eine Verbindung, die länger als 30 s unbenutzt war,
   wird vor der Benutzung mit `SELECT 1` geprüft. Ist sie tot, wird eine neue geöffnet; der
   Aufrufer merkt nichts.
4. **Nach einem Fehler** wird zurückgerollt. Klappt das nicht, wird die Verbindung geschlossen
   und nicht wieder benutzt.
5. **Kein Leck:** Der Platz wird in jedem Fall frei, auch wenn das Öffnen scheitert oder der
   Block mit Strg+C abgebrochen wird.

## Fachliche Änderung (bewusst)

`create_conversation` hat früher zwischendurch committet und dann gelesen. Jetzt passiert
beides in einer Transaktion. Das Ergebnis ist gleich, bei einem Fehler wird nichts halb gespeichert.

## Tests

`test/test_db.py` (Fakes, keine echte DB): Wiederverwendung, rollback, kaputte/getrennte
Verbindungen, Anklopfen, Obergrenze + Warten, kein Leck bei Fehlern, parallele Threads.
Gegenproben: vier absichtliche Fehler in `db.py` wurden alle erkannt.
`test_memory.py` und `test_project_db.py` angepasst (Verbindung bleibt offen, wird wiederverwendet).

## Messung 4

Gleiche zehn Nachrichten wie bisher (mit `ja` nach der Python-Entscheidung).
Zielwerte: Nachrichten mit Projekt unter 3,6 s, "Öffne Projekt" unter 1,8 s.

## Rückweg

Tag `mark4.vor-pool` auf dem Commit vor dem Umbau.
