import time

def led_sim(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    LED simulator koji reaguje na promena settings['state'].
    Ispisuje LED ON/OFF kad se stanje promeni i poziva callback.
    """
    last_state = None

    while not stop_event.is_set():
        state = settings.get("state", False)

        if state != last_state:
            print(f"[{actuator_code}] LED {'ON' if state else 'OFF'}")
            on_state_change(actuator_code, settings, state)
            last_state = state

