"""Projekt-Kontext ("project.md") in der Datenbank (Mark 4, Step 3.1).

Vorher lag der Text als Datei projects/<id>/project.md auf dem Rechner. Jetzt
steht er in der Tabelle project_contexts (eine Zeile je Projekt) und ist damit
auf jedem Rechner derselbe.

Der Text selbst ist unveraendert: Markdown mit den Abschnitten "## Goal",
"## Decisions" usw. Alle Funktionen behalten ihre Namen und Bedeutung, nur der
Speicherort wechselt.

Schreibzugriffe (neuer Eintrag, Abschnitt ersetzen) lesen und schreiben in
EINER Transaktion mit "FOR UPDATE": Zwei gleichzeitige Aenderungen
ueberschreiben sich nicht gegenseitig.
"""

from pathlib import Path

import db

# Der alte Speicherort, nur noch fuer die einmalige Uebernahme (migrate_local_files)
LEGACY_DIR = Path("projects")


def template(project_name):
    return (
        f"# {project_name}\n\n"
        "## Goal\n\n"
        "Not defined yet.\n"
        "## Description\n\n"
        "Not defined yet.\n\n"
        "## Current Status\n\n"
        "No project information available yet.\n\n"
        "## Important Information\n\n"
        "None yet.\n\n"
        "## Decisions\n\n"
        "None yet.\n\n"
        "## Progress\n\n"
        "No progress recorded yet.\n\n"
        "## Open Topics\n\n"
        "None yet.\n\n"
        "## Next Steps\n\n"
        "None yet.\n"
    )


def ensure_project_context(project_id, project_name):
    """Legt den Kontext aus der Vorlage an, falls es noch keinen gibt.

    Ein vorhandener Text bleibt unveraendert.
    """
    with db.connect() as connection:
        connection.cursor().execute(
            """
            INSERT INTO project_contexts (project_id, content)
            VALUES (%s, %s)
            ON CONFLICT (project_id) DO NOTHING
            """,
            (project_id, template(project_name))
        )


def delete_project_context(project_id):
    with db.connect() as connection:
        connection.cursor().execute(
            "DELETE FROM project_contexts WHERE project_id = %s",
            (project_id, )
        )


def get_project_context(project_id):
    """Der Text, oder None, wenn es keinen gibt."""
    with db.connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT content FROM project_contexts WHERE project_id = %s",
            (project_id, )
        )

        row = cursor.fetchone()

    return None if row is None else row[0]


def save_project_context(project_id, content):
    """Ersetzt den ganzen Text (legt ihn an, falls er fehlt)."""
    with db.connect() as connection:
        connection.cursor().execute(
            """
            INSERT INTO project_contexts (project_id, content)
            VALUES (%s, %s)
            ON CONFLICT (project_id)
            DO UPDATE SET content = EXCLUDED.content,
                          updated_at = CURRENT_TIMESTAMP
            """,
            (project_id, content)
        )


def _replace_section(project_context, section, content):
    """Neuer Text mit ersetztem Abschnitt, oder None, wenn es ihn nicht gibt."""
    heading = f"## {section}"

    if heading not in project_context:
        return None

    start = project_context.index(heading)

    end = project_context.find("\n##", start + len(heading))

    new_section = f"{heading}\n\n{content}\n"

    if end == -1:
        return project_context[:start] + new_section

    return project_context[:start] + new_section + project_context[end:]


def _append_to_section(project_context, section, content):
    """Neuer Text mit einem Eintrag mehr, oder None (Abschnitt fehlt / Eintrag schon da)."""
    heading = f"## {section}"

    if heading not in project_context:
        return None

    start = project_context.index(heading)
    end = project_context.find("\n## ", start + len(heading))

    if end == -1:
        end = len(project_context)

    section_content = project_context[start + len(heading):end]

    if content in section_content:
        return None

    new_section = (
        f"{heading}\n\n"
        f"{section_content.strip()}\n"
        f" - {content}\n"
    )

    if end == len(project_context):
        return project_context[:start] + new_section

    return project_context[:start] + new_section + project_context[end:]


def _edit(project_id, change):
    """Liest den Text, wendet change(text) an und schreibt das Ergebnis.

    Gibt True zurueck, wenn geschrieben wurde. Liefert change() None (oder gibt
    es keinen Text), wird nichts geaendert und False zurueckgegeben.
    """
    with db.connect() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT content FROM project_contexts
            WHERE project_id = %s
            FOR UPDATE
            """,
            (project_id, )
        )

        row = cursor.fetchone()

        if row is None:
            return False

        new_text = change(row[0])

        if new_text is None:
            return False

        cursor.execute(
            """
            UPDATE project_contexts
            SET content = %s, updated_at = CURRENT_TIMESTAMP
            WHERE project_id = %s
            """,
            (new_text, project_id)
        )

    return True


def update_project_section(project_id, section, content):
    return _edit(
        project_id,
        lambda text: _replace_section(text, section, content)
    )


def add_to_project_section(project_id, section, content):
    return _edit(
        project_id,
        lambda text: _append_to_section(text, section, content)
    )


def _read_legacy(file):
    """Liest eine alte project.md.

    Mark 3 hat die Dateien ohne Encoding-Angabe geschrieben; unter Windows ist
    das cp1252 (Umlaute sind dann KEIN gueltiges UTF-8). Deshalb: erst UTF-8,
    sonst cp1252.
    """
    data = file.read_bytes()

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _replace_untouched_template(cursor, project_id, text):
    """Ersetzt einen Datenbank-Text, der noch die reine Vorlage ist. 1 = ersetzt."""
    cursor.execute(
        """
        SELECT c.content, p.name
        FROM project_contexts c
        JOIN projects p ON p.id = c.project_id
        WHERE c.project_id = %s
        """,
        (project_id, )
    )

    row = cursor.fetchone()

    if row is None or row[0] != template(row[1]) or text == row[0]:
        return 0

    cursor.execute(
        """
        UPDATE project_contexts
        SET content = %s, updated_at = CURRENT_TIMESTAMP
        WHERE project_id = %s
        """,
        (text, project_id)
    )

    return 1


def migrate_local_files():
    """Uebernimmt vorhandene projects/<id>/project.md einmalig in die Datenbank.

    - Nur fuer Projekte, die es in der Datenbank gibt.
    - Ein schon vorhandener Datenbank-Text wird NIE ueberschrieben - ausser er
      ist noch die unveraenderte Vorlage (dann geht nichts verloren).
    - Die lokalen Dateien bleiben liegen (werden nicht geloescht); danach kann
      der Ordner projects/ von Hand geloescht werden.
    - Ein Fehler bei einer Datei stoppt weder den Start noch die anderen.

    Gibt die Anzahl der uebernommenen Dateien zurueck.
    """
    if not LEGACY_DIR.is_dir():
        return 0

    migrated = 0

    for folder in sorted(LEGACY_DIR.iterdir()):
        file = folder / "project.md"

        if not folder.name.isdigit() or not file.is_file():
            continue

        try:
            text = _read_legacy(file)

            with db.connect() as connection:
                cursor = connection.cursor()

                cursor.execute(
                    """
                    INSERT INTO project_contexts (project_id, content)
                    SELECT id, %s FROM projects WHERE id = %s
                    ON CONFLICT (project_id) DO NOTHING
                    """,
                    (text, int(folder.name))
                )

                if cursor.rowcount and cursor.rowcount > 0:
                    migrated += 1
                else:
                    migrated += _replace_untouched_template(
                        cursor, int(folder.name), text
                    )
        except Exception as error:
            print(f"[projekt] {file} nicht uebernommen: {error}")

    if migrated:
        print(
            f"[projekt] {migrated} project.md in die Datenbank uebernommen "
            "(der Ordner projects/ wird nicht mehr gebraucht)."
        )

    return migrated
