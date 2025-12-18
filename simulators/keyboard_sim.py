import time
import sys

def keyboard_sim(sensor_code, delay, on_value, stop_event, settings=None):
    print("Press 'b' to toggle buzzer ON/OFF")

    while not stop_event.is_set():
        key = sys.stdin.read(1)

        if key.lower() == "b":
            on_value(sensor_code, settings, "b")

        time.sleep(delay)
