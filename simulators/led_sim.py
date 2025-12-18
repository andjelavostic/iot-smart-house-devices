import time
import random

def generate_led_state(delay, initial=False):
    """
    Generator koji simulira paljenje/gasenje LED.
    Nasumično menja stanje svakih `delay` sekundi.
    """
    state = initial
    while True:
        time.sleep(delay)
        new_state = random.choice([True, False])
        if new_state != state:
            state = new_state
            yield state

def led_sim(actuator_code, delay, on_state_change, stop_event, settings=None):
    """
    LED simulator poput button_sim: menja stanje nasumično
    i poziva callback svaki put kad se stanje promeni.
    """
    for state in generate_led_state(delay, initial=settings.get("state", False)):
        if stop_event.is_set():
            break

        if state:
            print(f"[{actuator_code}] LED ON")
        else:
            print(f"[{actuator_code}] LED OFF")

        if settings is not None:
            settings["state"] = state  # ažurira settings

        # poziva callback da glavni program reaguje
        if on_state_change:
            on_state_change(actuator_code, settings, state)
