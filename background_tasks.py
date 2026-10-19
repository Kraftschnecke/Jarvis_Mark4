from queue import Queue

result_queue = Queue()


def submit_result(result):
    result_queue.put(result)


def get_result():
    if result_queue.empty():
        return None

    return result_queue.get()


def get_results():
    results = []

    while True:
        result = get_result()

        if result is None:
            break

        results.append(result)

    return results