import random
import time

def generate_state(delay, initial=False):
    state = initial
    while True:
        time.sleep(delay)
        new_state = random.choice([True, False])
        if new_state != state:
            state = new_state
            yield state

def button_sim(
    sensor_code,
    delay,
    on_state_change,
    stop_event,
    settings=None
):
    for state in generate_state(delay):
        if stop_event.is_set():
            break

        if state:
            print(f"[{sensor_code}] Button PRESSED")
        else:
            print(f"[{sensor_code}] Button RELEASED")
        on_state_change(sensor_code, settings, state)
