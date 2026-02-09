# lcd_real.py
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

import time
from LCD_model import LCD # tvoja klasa iz lab vežbi

def run_lcd_real(sensor_code, delay, on_value, stop_event, settings=None):
    """
    Runner za pravi LCD na Raspberry Pi.
    settings može da sadrži:
        - message: string koji se prikazuje
        - backlight: True/False
        - cols, lines: dimenzije (default 16x2)
    """

    cols = settings.get("cols", 16) if settings else 16
    lines = settings.get("lines", 2) if settings else 2
    msg = settings.get("message", "Hello LCD") if settings else "Hello LCD"
    backlight = settings.get("backlight", True) if settings else True

    # inicijalizacija LCD-a
    lcd = LCD(pin_rs=settings.get("pin_rs"), pin_e=settings.get("pin_e"), pins_db=settings.get("pins_db"), GPIO=GPIO)
    lcd.begin(cols, lines)
    if backlight:
        lcd.message(msg)

    print(f"[{sensor_code}] LCD REAL started with message:\n{msg}")

    try:
        while not stop_event.is_set():
            # update poruka ako settings menja message
            if settings and "message" in settings:
                lcd.clear()
                lcd.message(settings["message"])
            if on_value:
                # za LCD on_value možemo obavestiti da je prikazano
                on_value(sensor_code, settings, settings.get("message") if settings else msg)
            time.sleep(delay)

    finally:
        lcd.clear()
        print(f"[{sensor_code}] LCD stopped")
