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

    GPIO.setmode(GPIO.BCM)
    GPIO.setup([red_pin, green_pin, blue_pin], GPIO.OUT)

    last_color = [None, None, None] # Za praćenje promene

    def set_hardware_color(color):
        r, g, b = color
        GPIO.output(red_pin, GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(green_pin, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(blue_pin, GPIO.HIGH if b else GPIO.LOW)

    print(f"[{actuator_code}] RGB REAL started")

    try:
        while not stop_event.is_set():
            # Uzmi boju koju je process_logic upisao u settings
            current_color = settings.get("color", [0, 0, 0])
            
            # Postavi na pinove samo ako se boja razlikuje od prethodne
            if current_color != last_color:
                set_hardware_color(current_color)
                last_color = current_color
                
                # Opciono: javi main-u da je hardver uspešno postavljen
                if on_state_change:
                    on_state_change(actuator_code, settings, current_color)
            
            sleep(0.5) # 0.1s je sasvim dovoljno za hardver
    finally:
        GPIO.cleanup([red_pin, green_pin, blue_pin])