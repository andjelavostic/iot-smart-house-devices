from simulators.led_sim import led_sim
from simulators.button_sim import button_sim
from simulators.pir_sim import pir_sim
from simulators.membrane_switch_sim import ms_sim


SENSOR_REGISTRY = {
    "button": button_sim,
    "pir": pir_sim,
    "membrane": ms_sim
}
ACTUATOR_REGISTRY = {
    "led": led_sim
}