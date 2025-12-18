import time

def buzzer_sim(actuator_code, stop_event, settings, on_state_change):

    last_state = None

    while not stop_event.is_set():
        state = settings.get("state", False)

        # samo ako se stanje promijenilo
        if state != last_state:
            print(f"[{actuator_code}] Buzzer {'ON' if state else 'OFF'}")
            on_state_change(actuator_code, settings, state)
            last_state = state

        if state:
            try:
                import winsound
                winsound.Beep(1000, 200)
            except ImportError:
                import os
                os.system("echo -e '\a'")
        else:
            time.sleep(0.1)

