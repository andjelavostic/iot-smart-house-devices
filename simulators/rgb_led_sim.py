import time

def rgb_sim(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    Simulacija RGB LED.
    Samo printa boje u konzolu ili prati settings["color"].
    """
    print(f"[{actuator_code}] RGB SIM started")

    try:
        while not stop_event.is_set():
            color = settings.get("color", [0,0,0])  # koristi isto polje iz settings
            print(f"[{actuator_code}] Simulated color: {color}")
            if on_state_change:
                on_state_change(actuator_code, settings, color)
            time.sleep(0.5)
    finally:
        print(f"[{actuator_code}] RGB SIM stopped")
