try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
import time


def run_button_real(sensor_code,
    delay,
    on_state_change,
    stop_event,
    settings):
    pin = settings['pin']
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    last_state = GPIO.input(pin)

    while not stop_event.is_set():
        current_state = GPIO.input(pin)
        

        is_pressed = (current_state == GPIO.LOW)
        
        if is_pressed != (last_state == GPIO.LOW):
            if is_pressed:
                print(f"[{sensor_code}] REAL Button PRESSED")
            else:
                print(f"[{sensor_code}] REAL Button RELEASED")
            
            on_state_change(sensor_code, settings, is_pressed)
            last_state = current_state
            
        time.sleep(0.1) 