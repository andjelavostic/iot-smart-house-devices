import time

def led_sim(
    actuator_code,
    delay,
    stop_event,
    settings=None
):
    """
    LED ne generiše stanje sama.
    Čeka da se settings['state'] promeni.
    """

    last_state = None

    while not stop_event.is_set():
        time.sleep(delay)

        if settings is None:
            continue

        state = settings.get("state")

        # reaguje samo ako se stanje promenilo
        if state != last_state:
            last_state = state

            if state:
                print(f"[{actuator_code}] LED ON")
            else:
                print(f"[{actuator_code}] LED OFF")
