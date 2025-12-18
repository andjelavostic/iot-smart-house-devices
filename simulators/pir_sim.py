import random
import time

def pir_sim(
    sensor_code,
    delay,
    on_state_change,
    stop_event,
    settings=None
):
    while not stop_event.is_set():
        time.sleep(delay)

        motion = random.choice([True, False])
        print(f"[{sensor_code}] PIR motion: {motion}")
        on_state_change(sensor_code, settings, motion)



