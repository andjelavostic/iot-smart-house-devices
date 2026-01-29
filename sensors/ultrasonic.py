import RPi.GPIO as GPIO
import time

def run_ultrasonic_real(sensor_code, delay, on_value, stop_event, settings=None):
    """
    Pravi HC-SR04 ultrazvučni senzor.
    settings mora da sadrži:
      - trig_pin
      - echo_pin
    """

    trig = settings.get("trig_pin")
    echo = settings.get("echo_pin")

    if trig is None or echo is None:
        print(f"[{sensor_code}] ERROR: TRIG/ECHO pin nije definisan")
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(trig, GPIO.OUT)
    GPIO.setup(echo, GPIO.IN)

    GPIO.output(trig, False)
    time.sleep(0.2)

    print(f"[{sensor_code}] Ultrasonic REAL started (TRIG={trig}, ECHO={echo})")

    try:
        while not stop_event.is_set():

            # Trigger pulse
            GPIO.output(trig, True)
            time.sleep(0.00001)
            GPIO.output(trig, False)

            timeout = time.time() + 0.04

            # čekamo ECHO HIGH
            while GPIO.input(echo) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    pulse_start = None
                    break

            # čekamo ECHO LOW
            while GPIO.input(echo) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    pulse_end = None
                    break

            if pulse_start is None or pulse_end is None:
                time.sleep(delay)
                continue

            pulse_duration = pulse_end - pulse_start

            # Brzina zvuka: 34300 cm/s
            distance = (pulse_duration * 34300) / 2
            distance = round(distance, 2)

            if settings is not None:
                settings["distance"] = distance

            if on_value:
                on_value(sensor_code, settings, distance)

            print(f"[{sensor_code}] Distance: {distance} cm")

            time.sleep(delay)

    finally:
        GPIO.cleanup([trig, echo])
        print(f"[{sensor_code}] Ultrasonic stopped")
