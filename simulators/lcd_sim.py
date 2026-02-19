# lcd_sim.py
import time

def lcd_sim(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    Simulacija LCD-a.
    Ispisuje poruku na konzolu.
    """

    cols = settings.get("cols", 16) if settings else 16
    lines = settings.get("lines", 2) if settings else 2
    msg = settings.get("message", "Hello LCD") if settings else "Hello LCD"
    backlight = settings.get("backlight", True) if settings else True

    print(f"[{actuator_code}] LCD SIM started. Backlight: {backlight}")
    print("-" * (cols))
    print(msg)
    print("-" * (cols))

    try:
        while not stop_event.is_set():
            if settings and "message" in settings:
                msg = settings["message"]
                print(f"[{actuator_code}] LCD SIM updated message:")
                print("-" * cols)
                print(msg)
                print("-" * cols)

            if on_state_change:
                on_state_change(actuator_code, settings, msg)

            time.sleep(1)

    finally:
        print(f"[{actuator_code}] LCD SIM stopped")
