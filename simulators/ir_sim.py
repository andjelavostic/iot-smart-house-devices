import time
import random

def ir_sim(sensor_code,delay,on_value, stop_event, settings=None):
    """
    Simulacija IR senzora.
    Generiše pritiske dugmadi iz button_map.
    """
    button_map = settings.get("button_map", {}) if settings else {}
    buttons = list(button_map.values()) if button_map else ["POWER", "COLOR_BLUE", "COLOR_RED","COLOR_PURPLE","COLOR_GREEN"]

    print(f"[{sensor_code}] IR SIM started")
    try:
        while not stop_event.is_set():
            pressed = random.choice(buttons)
            if on_value:
                on_value(sensor_code, settings, pressed)
            print(f"[{sensor_code}] Simulated button: {pressed}")
            time.sleep(delay)
    finally:
        print(f"[{sensor_code}] IR SIM stopped")

