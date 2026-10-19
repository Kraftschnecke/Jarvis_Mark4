from pathlib import Path
import shutil


def get_project_folder(project_id):
    return Path("projects") / str(project_id)


def create_project_folder(project_id):
    folder = get_project_folder(project_id)
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def get_project_file(project_id):
    return get_project_folder(project_id) / "project.md"


def create_project_file(project_id, project_name):
    create_project_folder(project_id)

    file = get_project_file(project_id)

    if not file.exists():
        file.write_text(
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

    return file


def delete_project_file(project_id):
    folder = get_project_folder(project_id)

    if folder.exists():
        shutil.rmtree(folder)


def get_project_context(project_id):
    file = get_project_file(project_id)

    if not file.exists():
        return None

    return file.read_text()


def save_project_context(project_id, content):
    file = get_project_file(project_id)

    file.write_text(content)

    return file


def update_project_section(project_id, section, content):
    project_context = get_project_context(project_id)

    if project_context is None:
        return False

    heading = f"## {section}"

    if heading not in project_context:
        return False

    start = project_context.index(heading)

    end = project_context.find("\n##", start + len(heading))

    new_section = f"{heading}\n\n{content}\n"

    if end == -1:
        update_context = project_context[:start] + new_section
    else:
        update_context = project_context[:start] + new_section + project_context[end:]

    file = get_project_file(project_id)
    file.write_text(update_context)

    return True


def add_to_project_section(project_id, section, content):
    project_context = get_project_context(project_id)

    if project_context is None:
        return False

    heading = f"## {section}"

    if heading not in project_context:
        return False

    start = project_context.index(heading)
    end = project_context.find("\n## ", start + len(heading))

    if end == -1:
        end = len(project_context)

    section_content = project_context[start + len(heading):end]

    if content in section_content:
        return False
    
    new_section = (
        f"{heading}\n\n"
        f"{section_content.strip()}\n"
        f" - {content}\n"
    )

    if end == len(project_context):
        update_context = project_context[:start] + new_section
    else:
        update_context = (
            project_context[:start]
            + new_section
            +project_context[end:]
        )

    file = get_project_file(project_id)
    file.write_text(update_context)

    return True

