import time
import random

KEYS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#", "A", "B", "C", "D"]

def generate_values(correct_pin="1234", probability=0.2):
    while True:
        # 20% šanse da pošalje ispravan PIN
        if random.random() < probability:
            yield correct_pin
        else:
            length = random.randint(3, 5)
            code = "".join(random.choice(KEYS) for _ in range(length))
            yield code

def ms_sim(sensor_code, delay, on_value, stop_event, settings=None):
    gen = generate_values()
    while not stop_event.is_set():
        time.sleep(delay)
        code = next(gen)
        print(f"[{sensor_code}] Membrane input: {code}")
        on_value(sensor_code, settings, code)  
