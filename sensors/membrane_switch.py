try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
import time

"""def run_membrane_real(sensor_code,delay, on_value, stop_event,settings):
    ROW_PINS = settings['rows']    
    COL_PINS = settings['cols']    
    
    KEYPAD = [
        ["1", "2", "3", "A"],
        ["4", "5", "6", "B"],
        ["7", "8", "9", "C"],
        ["*", "0", "#", "D"]
    ]

    for row_pin in ROW_PINS:
        GPIO.setup(row_pin, GPIO.OUT)
    for col_pin in COL_PINS:
        GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def get_key():
        for i, row_pin in enumerate(ROW_PINS):
            GPIO.output(row_pin, GPIO.HIGH)
            for j, col_pin in enumerate(COL_PINS):
                if GPIO.input(col_pin) == GPIO.HIGH:
                    while GPIO.input(col_pin) == GPIO.HIGH: # Debounce
                        time.sleep(0.05)
                    GPIO.output(row_pin, GPIO.LOW)
                    return KEYPAD[i][j]
            GPIO.output(row_pin, GPIO.LOW)
        return None

    print(f"[{sensor_code}] REAL Membrane Switch ready.")
    
    while not stop_event.is_set():
        key = get_key()
        if key:
            print(f"[{sensor_code}] Key pressed: {key}")
            on_value(sensor_code, settings, key)
        time.sleep(0.1)
"""

def run_membrane_real(sensor_code, delay, on_value, stop_event, settings):
    ROW_PINS = settings['rows']    
    COL_PINS = settings['cols']    
    
    KEYPAD = [
        ["1", "2", "3", "A"],
        ["4", "5", "6", "B"],
        ["7", "8", "9", "C"],
        ["*", "0", "#", "D"]
    ]

    for row_pin in ROW_PINS:
        GPIO.setup(row_pin, GPIO.OUT)
    for col_pin in COL_PINS:
        GPIO.setup(col_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def get_key():
        for i, row_pin in enumerate(ROW_PINS):
            GPIO.output(row_pin, GPIO.HIGH)
            for j, col_pin in enumerate(COL_PINS):
                if GPIO.input(col_pin) == GPIO.HIGH:
                    while GPIO.input(col_pin) == GPIO.HIGH:  # debounce
                        time.sleep(0.05)
                    GPIO.output(row_pin, GPIO.LOW)
                    return KEYPAD[i][j]
            GPIO.output(row_pin, GPIO.LOW)
        return None

    print(f"[{sensor_code}] REAL Membrane Switch ready.")

    pin_buffer = ""  # ovde čuvamo unesene tastere

    while not stop_event.is_set():
        key = get_key()
        if key:
            print(f"[{sensor_code}] Key pressed: {key}")

            # samo brojevi za PIN
            if key in "0123456789ABCD":
                pin_buffer += key

            # clear s tasterom '*'
            if key == "*":
                pin_buffer = ""

            # ako smo unijeli 4 znaka → šaljemo PIN
            if len(pin_buffer) == 4:
                print(f"[{sensor_code}] PIN entered: {pin_buffer}")
                on_value(sensor_code, settings, pin_buffer)
                pin_buffer = ""  # reset buffer

        time.sleep(0.1)
