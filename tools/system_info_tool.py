import platform
import psutil
from tools.tool_result import ToolResult

def get_system_info():
    memory = psutil.virtual_memory()

    return ToolResult(
        success=True,
        data={
        "os": platform.system(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "python-version": platform.python_version(),
        "architecture": platform.architecture(),
        "cpu-cores": psutil.cpu_count(logical=False),
        "logical-cpus": psutil.cpu_count(logical=True),
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "ram_avaible_gb": round(memory.available / (1024 ** 3), 2)
        })
