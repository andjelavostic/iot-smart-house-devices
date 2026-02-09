try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

import time
from datetime import datetime

def run_ir_real(sensor_code, delay, on_value, stop_event, settings=None):
    """
    Real IR sensor runner.
    settings mora da sadrži:
      - pin
      - button_map (dict sa hex -> ime dugmeta)
    """
    if GPIO is None:
        print(f"[{sensor_code}] ERROR: RPi.GPIO nije dostupan")
        return

    pin = settings.get("pin")
    button_map = settings.get("button_map", {})

    if pin is None:
        print(f"[{sensor_code}] ERROR: pin nije definisan")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN)
    print(f"[{sensor_code}] IR REAL started (pin={pin})")

    def getBinary():
        num1s = 0
        binary = 1
        command = []
        previousValue = 0
        value = GPIO.input(pin)

        while value:
            time.sleep(0.0001)
            value = GPIO.input(pin)

        startTime = datetime.now()
        while not stop_event.is_set():
            if previousValue != value:
                now = datetime.now()
                pulseTime = now - startTime
                startTime = now
                command.append((previousValue, pulseTime.microseconds))
            if value:
                num1s += 1
            else:
                num1s = 0
            if num1s > 10000:
                break
            previousValue = value
            value = GPIO.input(pin)

        for (typ, tme) in command:
            if typ == 1:
                if tme > 1000:
                    binary = binary * 10 + 1
                else:
                    binary *= 10
        if len(str(binary)) > 34:
            binary = int(str(binary)[:34])
        return binary

    def convertHex(binaryValue):
        tmpB2 = int(str(binaryValue),2)
        return hex(tmpB2)

    try:
        while not stop_event.is_set():
            inData = convertHex(getBinary())
            if inData in button_map:
                name = button_map[inData]
                if on_value:
                    on_value(sensor_code, settings, name)
                print(f"[{sensor_code}] Button pressed: {name}")
            time.sleep(delay)
    finally:
        GPIO.cleanup([pin])
        print(f"[{sensor_code}] IR REAL stopped")
