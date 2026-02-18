try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

from time import sleep

def run_rgb_real(actuator_code, stop_event, settings=None, on_state_change=None):
    if GPIO is None:
        print(f"[{actuator_code}] ERROR: RPi.GPIO nije dostupan")
        return

    red_pin = settings.get("red_pin")
    green_pin = settings.get("green_pin")
    blue_pin = settings.get("blue_pin")

    if not all([red_pin, green_pin, blue_pin]):
        print(f"[{actuator_code}] ERROR: Nedostaju pinovi")
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(red_pin, GPIO.OUT)
    GPIO.setup(green_pin, GPIO.OUT)
    GPIO.setup(blue_pin, GPIO.OUT)

    def set_color(r, g, b):
        GPIO.output(red_pin, GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(green_pin, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(blue_pin, GPIO.HIGH if b else GPIO.LOW)
        if on_state_change:
            on_state_change(actuator_code, settings, [r,g,b])  # LISTA

    print(f"[{actuator_code}] RGB REAL started (R={red_pin}, G={green_pin}, B={blue_pin})")

    try:
        while not stop_event.is_set():
            color = settings.get("color", [0,0,0])
            set_color(*color)
            sleep(0.05)
    finally:
        GPIO.cleanup([red_pin, green_pin, blue_pin])
        print(f"[{actuator_code}] RGB REAL stopped")


