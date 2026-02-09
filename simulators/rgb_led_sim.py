import time

def rgb_sim(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    Simulacija RGB LED.
    Samo printa boje u konzolu.
    """
    print(f"[{actuator_code}] RGB SIM started")

    colors = [
        ("OFF", (0,0,0)),
        ("WHITE", (1,1,1)),
        ("RED", (1,0,0)),
        ("GREEN", (0,1,0)),
        ("BLUE", (0,0,1)),
        ("YELLOW", (1,1,0)),
        ("PURPLE", (1,0,1)),
        ("CYAN", (0,1,1)),
    ]

    try:
        while not stop_event.is_set():
            for name, state in colors:
                if stop_event.is_set():
                    break
                print(f"[{actuator_code}] Simulated color: {name}")
                if on_state_change:
                    on_state_change(actuator_code, settings, state)
                time.sleep(1)
    finally:
        print(f"[{actuator_code}] RGB SIM stopped")