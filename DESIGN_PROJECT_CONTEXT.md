# Design: project.md in der Datenbank (Step 3.1)

Ziel: Der Text je Projekt (`projects/<id>/project.md`) liegt in der Cloud-Datenbank.
Fertig, wenn das Löschen des lokalen Ordners `projects/` nichts ändert.

## Entscheidung: eigene Tabelle

```
project_contexts (project_id PK -> projects.id, content TEXT, updated_at)
```

Eine Spalte in `projects` wäre einfacher, aber `get_projects()` macht `SELECT *` und der
Code liest die Zeilen nach Position. Der lange Text würde dann bei jeder Projektliste mit
geladen. Eine eigene Tabelle lässt alles andere unverändert.

## Was sich ändert

| Vorher (Datei) | Jetzt (Datenbank) |
|----------------|-------------------|
| `create_project_file` | `ensure_project_context` (legt nur an, wenn es noch keinen gibt) |
| `delete_project_file` | `delete_project_context`, beim Projekt-Löschen in derselben Transaktion |
| `get_project_context` / `save_project_context` | gleiche Namen, gleiche Bedeutung |
| `update_project_section` / `add_to_project_section` | gleiche Namen; lesen + schreiben in **einer** Transaktion mit `FOR UPDATE` |
| Ordner `projects/` | nicht mehr nötig |

Der Markdown-Text und die Abschnittslogik sind unverändert (nur verschoben).

## Einmalige Übernahme (`migrate_local_files`)

Beim Start: Für jede Datei `projects/<id>/project.md`, deren Projekt es in der Datenbank
gibt und für die dort noch kein Text steht, wird der Inhalt übernommen.

- Ein vorhandener Datenbank-Text wird **nie** überschrieben (`ON CONFLICT DO NOTHING`).
- Die lokalen Dateien werden **nicht gelöscht**. Danach kannst du `projects/` selbst löschen.
- Ein Fehler bei einer Datei stoppt weder den Start noch die anderen Dateien.
- Zweiter Start: nichts mehr zu tun, keine Ausgabe.

## Folgen

- Jede Nachricht mit offenem Projekt liest den Text aus der Datenbank (eine Abfrage über den
  Pool, ca. 0,05 bis 0,1 s statt Datei lesen). Das passiert vor den KI-Aufrufen.
- Anderer Rechner = gleicher Text (vorher fehlte er und wurde aus der Vorlage neu angelegt).
- Ansehen: `py show_project.py` (Liste) und `py show_project.py <ID>`.

## Tests

`test/test_project_context.py` (Fake-Datenbank): Vorlage, nicht überschreiben, Eintrag
hinzufügen / nicht doppelt / falscher Abschnitt, Abschnitt ersetzen, eine Transaktion mit
`FOR UPDATE`, löschen, Öffnen legt den Text an, Übernahme (nur bekannte Projekte, nie
überschreiben, kaputte Datei, zweiter Lauf). Vier Gegenproben erkannt.

## Rückweg

Tag `mark4.vor-projektdb` auf dem Commit vor dem Umbau. Die alten Dateien bleiben bis zu
deinem Löschen erhalten.
