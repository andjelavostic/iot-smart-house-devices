import time

def run_4sd_simulator(actuator_code, stop_event, settings, on_state_change):
    last_displayed_value = None

    while not stop_event.is_set():

        current_val = settings.get("value", "00:00")

        if current_val != last_displayed_value:
            print(f"--- DISPLEJ [{actuator_code}] ---")
            print(f"|  {current_val}  |")
            print("----------------------")
            
            on_state_change(actuator_code, settings, current_val)
            last_displayed_value = current_val

        time.sleep(1)