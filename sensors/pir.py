import RPi.GPIO as GPIO
import time

def run_pir_real(sensor_code, settings, on_state_change, stop_event):
    pin = settings['pin']
    GPIO.setup(pin, GPIO.IN)

    def motion_callback(channel):
        print(f"[{sensor_code}] REAL PIR motion detected!")
        on_state_change(sensor_code, settings, True)

    GPIO.add_event_detect(pin, GPIO.RISING, callback=motion_callback)

    while not stop_event.is_set():
        time.sleep(1)

    GPIO.remove_event_detect(pin)