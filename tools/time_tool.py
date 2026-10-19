from datetime import datetime
from tools.tool_result import ToolResult

def get_current_time():
    return ToolResult(
        success=True,
        data=datetime.now().strftime("%H:%M:%S")
    )


def get_current_date():
    return ToolResult(
        success=True,
        data=datetime.now().strftime("%d.%m.%Y")
    )