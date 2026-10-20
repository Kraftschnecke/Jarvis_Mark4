"""Zeigt den Text (project.md) eines Projekts aus der Datenbank.

    py show_project.py          -> Liste aller Projekte mit ihrer ID
    py show_project.py 12       -> der Text von Projekt 12
"""

import sys

import project
import project_context


def main():
    if len(sys.argv) < 2:
        for row in project.get_projects():
            print(f"{row[0]:>4}  {row[1]}")
        return

    try:
        project_id = int(sys.argv[1])
    except ValueError:
        print("Die ID muss eine Zahl sein. Ohne Argument gibt es die Liste.")
        return

    text = project_context.get_project_context(project_id)

    if text is None:
        print(f"Zu Projekt {project_id} gibt es keinen Text.")
    else:
        print(text)


if __name__ == "__main__":
    main()
