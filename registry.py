from sensors.led import run_led_real
from sensors.ultrasonic import run_ultrasonic_real
from simulators.led_sim import led_sim
from simulators.button_sim import button_sim
try:
    from sensors.button import run_button_real
except ImportError:
    run_button_real = None
from simulators.pir_sim import pir_sim
try:
    from sensors.pir import run_pir_real
except ImportError:
    run_pir_real = None
from simulators.membrane_switch_sim import ms_sim
try:
    from sensors.membrane_switch import run_membrane_real
except ImportError:
    run_membrane_real = None
from simulators.buzzer_sim import buzzer_sim
try:
    from sensors.buzzer import run_buzzer_real
except ImportError:
    run_buzzer_real = None
from simulators.keyboard_sim import keyboard_sim
from simulators.ultrasonic_sim import ultrasonic_sim
from simulators.gyroscope_sim import gyro_simulator
from simulators.dht_sim import dht_simulator
from simulators._4sd_sim import run_4sd_simulator
SENSOR_REGISTRY = {
    "button": {
        "true": run_button_real,
        "sim": button_sim
    },
    "pir": {
        "true": run_pir_real,
        "sim": pir_sim
    },
    "membrane": { 
        "true": run_membrane_real, 
        "sim": ms_sim 
    },
    "keyboard": keyboard_sim,
    "ultrasonic":{
        "true":run_ultrasonic_real,
        "sim":ultrasonic_sim
    },
    "gyro": lambda sensor_code, delay, on_value, stop_event, settings: 
            gyro_simulator(delay, lambda a, g, p, s: on_value(sensor_code, s, {"accel": a, "gyro": g}), stop_event, None, settings),
    
    "dht": lambda sensor_code, delay, on_value, stop_event, settings:
            dht_simulator(delay, lambda h, t, p, s: on_value(sensor_code, s, {"temp": t, "hum": h}), stop_event, None, settings)
}
ACTUATOR_REGISTRY = {
    "led":{
        "true":run_led_real,
        "sim":led_sim
    },
    "buzzer": {
        "true": run_buzzer_real,
        "sim": buzzer_sim
    },
    "7segment": run_4sd_simulator 
}