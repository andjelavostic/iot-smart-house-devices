import time
import random


max_raw = 32767


def generate_values():
    accel = [random.randint(-max_raw, max_raw) for _ in range(3)]
    gyro = [random.randint(-max_raw, max_raw) for _ in range(3)]
    accel_scaled = [a / 16384.0 for a in accel]
    gyro_scaled = [g / 131.0 for g in gyro]
    return accel_scaled, gyro_scaled

def gyro_simulator(delay, callback, stop_event, publish_event, settings):
    while True:
        accel, gyro = generate_values()
        callback(accel, gyro, publish_event, settings)
        if stop_event.is_set():
            break
        time.sleep(delay)
