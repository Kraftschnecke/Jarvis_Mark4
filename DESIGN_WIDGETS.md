# Design: Seitenleiste mit Widgets (Etappe C)

## Idee
Rechts neben dem Chat sitzt eine Leiste mit drei Feldern. Jedes Feld wird in den
Einstellungen (Seite **Widgets**) einzeln gewählt oder mit `Off` ausgeblendet.

| Feld | Auswahl | Standard |
|------|---------|----------|
| oben | Off, Clock, Date, Calendar | Clock |
| Mitte | Off, Notes, Goals | Notes |
| unten | Off, Edmonton Oilers, Adler Mannheim | Off |

Unten ist standardmäßig aus, damit ohne dein Zutun nichts ins Internet geht.

## Wer macht was
- `web/widgets.js`: reine Hilfsfunktionen (Uhrzeit, Datum, Kalenderraster, Spielanzeige), mit Node prüfbar.
- `web/app.js`: zeichnet die Felder, nur mit `textContent` (nie `innerHTML`), damit Notizen, Ziele und Teamnamen nie als HTML wirken.
- `widgets.py`: `WidgetStore` (Notizen und Ziele in `widgets.json`), `HockeyFeed` (Spielplan der NHL).
- `server.py`: `GET /api/widgets`, `POST /api/widgets/notes`, `POST /api/widgets/goals`, `GET /api/hockey`.

## Entscheidungen
- **Notizen und Ziele** liegen in einer Datei auf deinem Rechner, nicht in der Datenbank: klein, einfach zu verstehen, kein Netz nötig. Speichern per Datei-Austausch (erst Nebendatei, dann umbenennen), damit ein Absturz nichts halb schreibt.
- **Ziele gelten nur für heute**: am nächsten Tag beginnt die Liste leer (das Datum wird mit gespeichert).
- **Grenzen**: Notiz 5000 Zeichen, höchstens 20 Ziele à 200 Zeichen. Der Server prüft das, nicht nur die Seite.
- **Spielplan holt nur der Server** (Adresse fest `https://api-web.nhle.com/`, nur https, 8 Sekunden Zeitlimit, Größenlimit). Der Browser ruft nie selbst ins Internet. Ergebnis 5 Minuten zwischengespeichert; ohne Netz kommt der letzte Stand mit Hinweis, sonst eine Meldung.
- **Auswahl, nicht freie Eingabe**: das Team kommt aus einer festen Liste (`widgets.TEAMS`). Ein manipulierter Wert in `settings.json` führt nie zu einem Abruf.
- **Aktuelles Spiel** = laufendes, sonst das letzte beendete. Dazu die nächsten vier.
- **Kein Gastmodus**: Gäste sehen keine Leiste, die Adressen sind für sie gesperrt.
- **Schmale Fenster** (unter ca. 1200 Pixel): Leiste ausgeblendet.

## Offen / ehrlich
- **Weitere NHL-Teams**: in `widgets.TEAMS` und `settings_manager.CHOICES` ergänzen.
- **Die NHL-Schnittstelle konnte ich in meiner Umgebung nicht aufrufen** (kein Netz). Das Format ist nach der öffentlich bekannten Form (`club-schedule-season`) gebaut und in den Tests nachgestellt, aber erst dein Test (C8, C9) zeigt, ob es zur echten Antwort passt. `parse_games` überspringt Unpassendes statt abzustürzen. Zeigt das Feld `Keine Spiele gefunden.`, schick mir bitte den Text von `https://api-web.nhle.com/v1/club-schedule-season/EDM/now` (die ersten ca. 40 Zeilen).
- Der Kalender kennt nur eigene Termine (keine Verbindung zu Google Kalender o. Ä.; das wäre Mark 5). Keine Erinnerungen und keine Wiederholungen (jeden Montag): bewusst nicht in Etappe C.

## Etappe C2

**Adler Mannheim.** Die Adler bieten auf ihrer Spielplan-Seite offiziell „Download Spielplan“ an: eine iCal-Datei (`https://adler-mannheim.de/saison/spielplan/iCal.ics`). Der Server liest sie (`parse_ics`), 5 Minuten zwischengespeichert, gleiche Sicherheitsregeln wie bei der NHL (feste Hosts, nur https, Weiterleitungen nur auf erlaubte Hosts).
- Titel `Heim vs. Gast`, Beginn mit Zeitzone Europe/Berlin. Die Umrechnung auf UTC (`berlin_to_utc`) kennt die EU-Sommerzeit selbst, ohne `tzdata` (das fehlt unter Windows oft).
- **Keine Ergebnisse**: die Datei enthält nur Paarungen und Termine. Ein Spiel zählt 3 Stunden nach Beginn als beendet, bis dahin als „läuft gerade“. Das „letzte Spiel“ erscheint darum ohne Ergebnis.
- Auch Champions-Hockey-League- und Testspiele stehen darin (alles, was die Adler in ihren Kalender stellen). Fremde Zeitzonen und ganztägige Einträge werden übersprungen.
- Eine Quelle für **Ergebnisse** wäre die HTML-Seite der DEL (`penny-del.org/spiele`). Sie hat keine Datenschnittstelle, ihr Aufbau kann sich jederzeit ändern. Bewusst nicht eingebaut; Entscheidung bei dir.

**Kalender-Termine.** Neue Liste `events` in `widgets.json` (Titel höchstens 100 Zeichen, Datum, optional Uhrzeit, höchstens 500; Termine älter als 31 Tage werden beim Speichern aufgeräumt; höchstens 5 Jahre voraus). Tag anklicken, Termin eintragen, mit × löschen.
- **Per Jarvis**: `ADD_CALENDAR_EVENT` (Titel, Datum JJJJ-MM-TT, Uhrzeit oder „ganztägig“) und `LIST_CALENDAR_EVENTS` (ein Tag oder „nächste“). Der Router bekommt dafür das heutige Datum samt Wochentag, damit „morgen“ und „Freitag“ stimmen. Jarvis nennt in der Antwort Wochentag und Datum, damit du Fehler sofort siehst; löschen geht per Klick.
- Risikostufe `safe` (schreibt nur in `widgets.json`, per Klick umkehrbar), steht wie alles im Aktionsprotokoll. Ungültiges (31.02., 25:00) gibt eine Fehlermeldung und speichert nichts. **Im Gastmodus gibt es beide Aufgaben nicht.**
- Nach jeder Nachricht und jede Minute lädt die Seite Termine und Ziele neu, damit Einträge von Jarvis (und der Tageswechsel) ohne F5 erscheinen.
- Seite und Jarvis-Aufgaben teilen sich ein Schloss auf die Datei, damit sich nichts überschreibt.

**Tägliche Ziele.** Jedes Ziel hat ein `daily`-Kennzeichen (↻). Am nächsten Tag bleiben nur tägliche Ziele, wieder als „nicht erledigt“; einmalige verschwinden. Das ↻ am Eingabefeld gilt nur für den nächsten Eintrag, ein Klick auf das ↻ am Ziel wechselt später.

**Aufklappen bei schmalem Fenster** (unter ca. 1200 Pixel): ein 🧩-Knopf in der Kopfzeile klappt die Leiste von rechts auf (Esc, Klick daneben oder nochmal 🧩 schließt). Ohne aktive Widgets und im Gastmodus gibt es den Knopf nicht.
