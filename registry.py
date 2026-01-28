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
from simulators.buzzer_sim import buzzer_sim
from simulators.keyboard_sim import keyboard_sim
from simulators.ultrasonic_sim import ultrasonic_sim


SENSOR_REGISTRY = {
    "button": {
        "true": run_button_real,
        "sim": button_sim
    },
    "pir": {
        "true": run_pir_real,
        "sim": pir_sim
    },
    "membrane": ms_sim,
    "keyboard": keyboard_sim,
    "ultrasonic":ultrasonic_sim
}
ACTUATOR_REGISTRY = {
    "led": led_sim,
    "buzzer": buzzer_sim
}