from jarvis import Jarvis
from personality import get_address
from cli_input import start_input
from prompt_toolkit import print_formatted_text
import time


def run():
    jarvis = Jarvis()

    thread, result = start_input()

    while True:

        for response in jarvis.check_background_results():
            print_formatted_text(
                f"J.A.R.V.I.S. Background: {response}"
            )

        if not thread.is_alive():
            message = result.get("message")

            if message is None:
                print_formatted_text(f"J.A.R.V.I.S.: Shutting down, {get_address()}")
                break

            message = message.strip()

            if not message:
                # Nur Enter gedrueckt: nichts an das Modell schicken
                thread, result = start_input()
                continue

            response = jarvis.process_message(message)

            if response["status"] == "exit":
                print_formatted_text(
                    f"J.A.R.V.I.S.: {response['content']}"
                )
                break

            print_formatted_text(
                f"J.A.R.V.I.S.: {response['content']}"
            )

            thread, result = start_input()

        time.sleep(0.1)


try:
    run()
except KeyboardInterrupt:
    # Strg+C waehrend einer Anfrage oder im Leerlauf: sauber beenden
    print_formatted_text(f"\nJ.A.R.V.I.S.: Shutting down, {get_address()}")
