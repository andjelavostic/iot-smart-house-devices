from simulators.button_sim import button_sim
from simulators.pir_sim import pir_sim

SENSOR_REGISTRY = {
    "button": button_sim,
    "pir": pir_sim,
}
