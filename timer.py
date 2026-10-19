import time
import threading
from background_tasks import submit_result


def start_timer(seconds):
    thread = threading.Thread(
        target=run_timer,
        args=(seconds,),
        daemon=True
    )
    thread.start()
    return thread


def run_timer(seconds):
    time.sleep(seconds)
    submit_result({
        "type": "TIMER_FINISHED",
        "data": {
            "seconds": seconds
        }
    })


def convert_to_seconds(value, unit):
    if unit == "seconds":
        return value
    elif unit == "minutes":
        return value * 60
    elif unit == "hours":
        return value * 3600
    else:
        raise ValueError(f"Unknown time unit: {unit}")