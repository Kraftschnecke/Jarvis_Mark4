from task import Task
from action import Action


def create_get_time_task():
    task = Task(
        "GET_TIME",
        "Aktuelle Uhrzeit ermitteln"
    )

    task.add_action(
        Action("get_current_time")
    )

    return task


def create_search_web_task():
    task = Task(
        "SEARCH_WEB",
        "Eine Websuche durchführen"
    )

    task.add_action(
        Action(
            "search_web",
            {"query": None}
        )
    )

    return task


def create_get_date_task():
    task = Task(
        "GET_DATE",
        "Aktuelles Datum ermitteln"
    )

    task.add_action(
        Action("get_current_date")
    )

    return task


def create_calculate_task():
    task = Task(
        "CALCULATE",
        "Eine mathematische Berechnung durchführen"
    )

    task.add_action(
        Action(
            "calculate",
            {"expression": None}
        )
    )

    return task


def create_get_system_info_task():
    task = Task(
        "GET_SYSTEM_INFO",
        "Informationen über das aktuelle System ermitteln"
    )

    task.add_action(
        Action(
            "get_system_info"
        )
    )

    return task


def create_open_file_task():
    task = Task(
        "OPEN_FILE",
        "Eine Datei auf dem Computer öffnen"
    )

    task.add_action(
        Action(
            "open_file",
            {"path": None}
        )
    )

    return task


def create_get_running_programs_task():
    task = Task(
        "GET_RUNNING_PROGRAMS",
        "Laufende Programme auf dem Computer ermitteln"
    )

    task.add_action(
        Action(
            "get_running_programs"
        )
    )

    return task


def create_set_volume_task():
    task = Task(
        "SET_VOLUME",
        "Die Systemlautstärke einstellen"
    )

    task.add_action(
        Action(
            "set_volume",
            {"percentage": None}
        )
    )

    return task


def create_find_program_task():
    task = Task(
        "FIND_PROGRAM",
        "Ein Programm auf dem Computer finden"
    )

    task.add_action(
        Action(
            "find_program",
            {"program": None}
        )
    )

    return task


def create_start_program_task():
    task = Task(
        "START_PROGRAM",
        "Ein Programm auf dem Computer öffnen oder starten"
    )

    task.add_action(
        Action(
            "find_program",
            {"program": None}
        )
    )

    task.add_action(
        Action(
            "open_program",
            {
                "path": {
                    "source": "previous_result"
                }
            }
        )
    )

    return task


def create_start_timer_task():
    task = Task(
        "START_TIMER",
        "Einen Timer starten"
    )
    task.add_action(
        Action(
            "start_timer",
            {
                "value": {
                    "description": "Die Dauer des Timers als Zahl",
                    "type": "number"
                },
                "unit": {
                    "description": "Die Zeiteinheit, z.B.: seconds, minutes oder hours",
                    "type": "string"
                }
            }
        )
    )
    return task


def register_all_tasks(registry):
    registry.register(create_get_time_task())
    registry.register(create_get_date_task())
    registry.register(create_calculate_task())
    registry.register(create_get_system_info_task())
    registry.register(create_open_file_task())
    registry.register(create_get_running_programs_task())
    registry.register(create_set_volume_task())
    registry.register(create_find_program_task())
    registry.register(create_start_program_task())
    registry.register(create_start_timer_task())
    registry.register(create_search_web_task())
