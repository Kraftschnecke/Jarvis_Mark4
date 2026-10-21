from timer import (
    start_timer, convert_to_seconds, list_timers, cancel_timer, clean_name,
    format_duration, TimerError,
)
import widgets
from tools.volume_tool import set_volume
from tools.time_tool import get_current_time, get_current_date
from tools.process_tool import get_running_programs
from tools.file_tool import open_file
from tools.program_tool import find_program, launch_program
from tools.system_info_tool import get_system_info
from tools.web_search_tool import search_web
from tools.tool_result import ToolResult
import ast
import operator

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv
}

UNARY_OPERATORS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos
}


def calculate_expression(node):
    # bool ist in Python auch ein int ("True + 1"), das soll nicht gehen
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value

    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](
            calculate_expression(node.operand)
        )

    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left = calculate_expression(node.left)
        right = calculate_expression(node.right)

        return OPERATORS[type(node.op)](left, right)

    raise ValueError("Invalid mathematical expression")


WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def describe_day(iso_date):
    """'2026-10-23' -> 'Freitag, 23.10.2026' (so liest Jarvis das Datum auch vor)."""
    from datetime import date
    day = date.fromisoformat(iso_date)
    return f"{WEEKDAYS[day.weekday()]}, {day.day:02d}.{day.month:02d}.{day.year}"


def execute_action(action):
    if action.name == "get_current_time":
        return get_current_time()

    if action.name == "get_current_date":
        return get_current_date()

    if action.name == "calculate":
        expression = action.parameters["expression"]
        tree = ast.parse(expression, mode="eval")

        return calculate_expression(tree.body)

    if action.name == "get_system_info":
        return get_system_info()
    
    if action.name == "open_file":
        return open_file(action.parameters["path"])

    if action.name == "get_running_programs":
        return get_running_programs()

    if action.name == "set_volume":
        return set_volume(action.parameters["percentage"])

    if action.name == "find_program":
        return find_program(action.parameters["program"])

    if action.name == "open_program":
        return launch_program(action.parameters["path"])

    if action.name == "search_web":
        return search_web(action.parameters["query"])

    if action.name == "start_timer":
        value = action.parameters["value"]
        unit = action.parameters["unit"]
        seconds = convert_to_seconds(value, unit)
        name = clean_name(action.parameters.get("name"))
        try:
            start_timer(seconds, name)
        except TimerError as error:
            return ToolResult(success=False, error=str(error))
        return ToolResult(success=True, data={"seconds": seconds, "name": name})

    if action.name == "list_timers":
        timers = [
            {"number": number, "name": t["name"], "remaining": format_duration(t["remaining"])}
            for number, t in enumerate(list_timers(), start=1)
        ]
        return ToolResult(success=True, data={"timers": timers} if timers else {"timers": [], "info": "Es läuft kein Timer."})

    if action.name == "cancel_timer":
        try:
            cancelled = cancel_timer(action.parameters.get("name"))
        except TimerError as error:
            return ToolResult(success=False, error=str(error))
        return ToolResult(success=True, data={"cancelled": cancelled})

    if action.name == "add_calendar_event":
        store = widgets.default_store()
        raw_time = action.parameters.get("time")
        at = raw_time.strip() if isinstance(raw_time, str) else ""
        if at.lower() in ("ganztaegig", "ganztägig", "all-day", "all day", "none", "null", "-"):
            at = ""
        try:
            event = store.add_event(action.parameters.get("title"), action.parameters.get("date"), at)
        except ValueError as error:
            return ToolResult(success=False, error=str(error))
        return ToolResult(success=True, data={
            "title": event["title"], "date": describe_day(event["date"]),
            "time": event["time"] or "ganztägig",
        })

    if action.name == "list_calendar_events":
        store = widgets.default_store()
        wanted = action.parameters.get("date")
        if isinstance(wanted, str) and wanted.strip().lower() in ("naechste", "nächste", "upcoming", "next"):
            events = store.upcoming_events(10)
        elif isinstance(wanted, str) and widgets._valid_date(wanted.strip()):
            events = store.events_on(wanted.strip())
        else:
            return ToolResult(success=False, error="Das Datum habe ich nicht verstanden.")
        shown = [{"date": describe_day(e["date"]), "time": e["time"] or "ganztägig", "title": e["title"]}
                 for e in events]
        return ToolResult(success=True, data={"events": shown} if shown else {"events": [], "info": "Keine Termine."})

    raise ValueError(f"Unknown action: {action.name}")
