import psutil
from tools.tool_result import ToolResult


def get_running_programs():
    programs = []

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]
            if name and name not in programs:
                programs.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return ToolResult(
        success=True,
        data=programs
    )