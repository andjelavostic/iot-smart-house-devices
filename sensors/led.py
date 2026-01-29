import RPi.GPIO as GPIO
import time

def run_led_real(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    Prava LED dioda preko GPIO pina.
    settings mora da sadrži:
      - pin (npr. 18)
      - state (True / False)
    """

    pin = settings.get("pin")
    if pin is None:
        print(f"[{actuator_code}] ERROR: LED pin nije definisan")
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)

    last_state = None
    print(f"[{actuator_code}] LED GPIO aktivna na pinu {pin}")

    try:
        while not stop_event.is_set():
            state = settings.get("state", False)

            if state != last_state:
                GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
                print(f"[{actuator_code}] LED {'ON' if state else 'OFF'}")

                if on_state_change:
                    on_state_change(actuator_code, settings, state)

                last_state = state

            time.sleep(0.1)

    finally:
        GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup(pin)
