try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
import time

def run_buzzer_real(actuator_code, stop_event, settings, on_state_change):
    pin = settings['pin']
    GPIO.setup(pin, GPIO.OUT)
    
    pwm = GPIO.PWM(pin, 1000) #1000Hz frekv
    last_state = None

    print(f"[{actuator_code}] REAL Buzzer ready on pin {pin}.")

    try:
        while not stop_event.is_set():
            state = settings.get("state", False)

            if state != last_state:
                if state:
                    print(f"[{actuator_code}] REAL Buzzer ON")
                    pwm.start(50) 
                else:
                    print(f"[{actuator_code}] REAL Buzzer OFF")
                    pwm.stop()
                
                on_state_change(actuator_code, settings, state)
                last_state = state

            time.sleep(0.1)
    finally:
        pwm.stop()
        GPIO.cleanup(pin)