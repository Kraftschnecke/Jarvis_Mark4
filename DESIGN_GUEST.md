# Gastmodus (Step 6b)

Ziel: Jemand anderes (z. B. dein Bruder) soll Jarvis ausprobieren können, **ohne dass er
irgendetwas auf deinem Rechner tun oder sehen kann**. Vorbereitung für Mark 5 („Go online“).

Start: `py server.py --guest` (optional `--port 8001`, damit dein normaler Jarvis daneben
laufen kann). Der Gastmodus ist **nicht aus der Weboberfläche schaltbar**: es gibt keine
Einstellung dafür (Test prüft das).

## Grundidee: nicht „verboten“, sondern „nicht vorhanden“

Im Gastmodus gibt es **kein** normales Jarvis-Objekt. Es wird nur `GuestJarvis` (guest.py)
gebaut, ohne Datenbank, Gedächtnis, Projekte, Plan-Ausführung oder Aktionsprotokoll. Der
Test `test_guest.py` blockiert den Import von `db`, `memory`, `project`, `workspace`, `jarvis`
und `psycopg`: Der Gastmodus läuft trotzdem.

| Kann der Gast … | Antwort |
|---|---|
| plaudern | ja, ohne dein Gedächtnis, nichts wird gespeichert |
| Uhrzeit, Datum, Rechnen, Websuche | ja (nur diese 4 Aufgaben, alle „safe“) |
| Programme, Dateien, Lautstärke, Timer | nein, die Aufgaben sind nicht einmal registriert |
| Befehle („Öffne Projekt …“, Reset, Beenden), Pläne | nein, feste Absage ohne weiteren KI-Aufruf |
| Einstellungen ändern, Stimme von OpenAI nutzen | nein (kostet dich Geld) |
| Erinnerungen, Projekte, Aktionsprotokoll, deine Timer sehen | nein |

## Mehrere Schichten

1. **Server-Liste:** Im Gastmodus beantwortet der Server nur `GET /api/settings`
   (Standardwerte mit `guest: true`), `GET /api/background` (immer leer) und
   `POST /api/message`. Alles andere unter `/api/` ist 403. Der Test prüft jede Adresse einzeln
   und dass die verbotenen Anfragen Jarvis nie erreichen.
2. **Eigener Jarvis:** `GuestJarvis` kennt nur 4 Aufgaben. Ein Router, der etwas anderes
   behauptet (auch kaputte Typen wie eine Liste), wird abgelehnt.
3. **Harmlosigkeit wird geprüft:** Beim Start prüft `build_guest_registry`, dass jede Gast-Aufgabe
   `safe` ist. Sonst startet der Gastmodus gar nicht. Zusätzlich wird vor jeder Ausführung noch einmal
   geprüft.
4. **Eigener Prompt:** Der Chat bekommt den Hinweis, dass er nichts auf dem Computer tun kann und
   das nie behaupten soll.
5. **Eigene Einstellungen:** wegwerfbare Datei mit Standardwerten. Deine `settings.json` wird nicht gelesen.
6. **Deine Hintergrundmeldungen** (z. B. ein ablaufender Timer) werden nicht abgeholt und nicht gezeigt.

## Schutz vor Kosten und Missbrauch

- Höchstens 500 Zeichen pro Nachricht und 30 Nachrichten in 10 Minuten. Abgelehnte Nachrichten
  kosten nichts (kein KI-Aufruf).
- Die Stimme von OpenAI ist gesperrt (`/api/speak` → 403).
- Fehlermeldungen enthalten keine Schlüssel oder Interna.

## Bekannte Grenzen (kommen mit Mark 5)

- **Alle Gäste teilen sich eine Unterhaltung**, solange der Server läuft (höchstens 40 Nachrichten).
  Getrennte Sitzungen pro Besucher gehören zum Login.
- **Kein Login, kein HTTPS.** Der Server hört weiter nur auf 127.0.0.1 (dein Rechner). Von außen
  erreichbar wird er erst in Mark 5, mit Login, HTTPS und Tunnel/Hosting. Bis dahin ist der Gastmodus
  die Grundlage, nicht die Freigabe.
- Websuche kostet nichts, ein Gast kann aber das Suchkontingent verbrauchen (durch die Nachrichten-Grenze begrenzt).

## Geprüft

`test/test_guest.py` (Aufgaben, Router-Austricksen, Limits, Fehler, Import-Sperre),
`test/test_server_guest.py` (jede Adresse), Browser-Prüfung (Oberfläche ohne Seitenleiste und Einstellungen,
keine Fehlermeldungen, HTML in Antworten wird nicht ausgeführt) und Gegenproben.
