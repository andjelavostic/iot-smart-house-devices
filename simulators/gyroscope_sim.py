import time
import random

max_raw = 32767

def generate_values():
    accel = [random.randint(-max_raw, max_raw) for _ in range(3)]
    gyro = [random.randint(-max_raw, max_raw) for _ in range(3)]
    accel_scaled = [a / 16384.0 for a in accel]
    gyro_scaled = [g / 131.0 for g in gyro]
    return accel_scaled, gyro_scaled

def gyro_simulator(sensor_code, delay, stop_event, on_value, settings):

    while not stop_event.is_set():
        accel, gyro = generate_values()
        
        val = {
            "accel": accel,
            "gyro": gyro
        }
        
        # pozivamo on_value (što je lambda u mainu) sa tačno 3 argumenta
        on_value(sensor_code, settings, val)
        
        time.sleep(delay)