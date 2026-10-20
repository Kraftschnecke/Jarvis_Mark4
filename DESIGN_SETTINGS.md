# Entscheidungen: ungenutzte Einstellungen (Step 3.4)

Vorher gab es 12 Einstellungen, von denen nur drei etwas bewirkten. Jetzt gibt es nur noch
Einstellungen, die wirklich funktionieren.

| Einstellung | Entscheidung | Begründung |
|-------------|--------------|------------|
| Address (Anrede) | **funktioniert jetzt** | Gilt in den Prompts und in allen festen Texten |
| Accent color | **funktioniert jetzt**: `J.A.R.V.I.S. Blue` oder `British Racing Green`, wählbar wie Hell/Dunkel | Wunsch von Moritz |
| Personality | entfernt | Jarvis hat eine feste Persönlichkeit |
| Name | entfernt | "J.A.R.V.I.S." ist die Identität |
| Language | entfernt | Jarvis antwortet in der Sprache des Nutzers |
| Confirmations | entfernt | Rückfragen kommen mit den Risikostufen (Phase 4); Sicherheit soll nicht abschaltbar sein |
| UI scale | entfernt | Doppelt zur Schriftgröße |
| Voice (4 Einstellungen) | entfernt, kommt mit Phase 6 zurück | Es gibt noch keine Stimme |
| Startup behavior | entfernt, **Idee für später** | Rechte Seitenleiste, die beim Öffnen anzeigt, was geöffnet ist |

Übrig: Theme, Accent color, Font size, Address, Memory enabled.
Die Seiten General und Voice gibt es nicht mehr.

## Wie die Anrede funktioniert

- `personality.py` speichert die Anrede (`get_address()`). Jede Stelle, die "Sir" sagt, fragt dort
  nach dem aktuellen Wert. Eine Änderung wirkt deshalb sofort, ohne Neustart.
- Gültig: ein einzeiliger Text ohne Steuerzeichen, 1 bis 30 Zeichen, ohne Leerzeichen an den Rändern.
  Der Wert landet im System-Prompt, deshalb sind Zeilenumbrüche nicht erlaubt.
- Ungültiger Wert in `settings.json` (von Hand kaputt gemacht): Jarvis nimmt `Sir`.
- Die Anrede steht auch in der Begrüßung der Weboberfläche.

## Alte settings.json

Beim Laden werden Schlüssel verworfen, die es nicht mehr gibt (`ui_scale`, `voice`, `name`, ...).
Gültige Werte (Theme, Schriftgröße, Anrede, Memory an/aus) bleiben erhalten.
Ein alter Wert `accent_color: "Custom"` bleibt in der Datei stehen; die Seite zeigt dann Blau, bis du
eine der beiden Farben wählst.

## Tests

`test/test_settings.py` (neu), erweitert: `test_server.py`, `test_brain.py`, `test_project_confirmation.py`.
Fünf Gegenproben erkannt (Länge, Zeilenumbruch, feste Anrede, alte Schlüssel, sofortige Wirkung).
Browser-Check mit Playwright (Seiten, Farbwechsel hell/dunkel, kein Aufblitzen, Anrede, Fehlerfall).
