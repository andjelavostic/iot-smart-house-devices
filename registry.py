from sensors.dht import run_dht_real
from sensors.ir import run_ir_real
from sensors.lcd.lcd import run_lcd_real
from sensors.led import run_led_real
from sensors.rgb_led import run_rgb_real
from sensors.ultrasonic import run_ultrasonic_real
from simulators.lcd_sim import lcd_sim
from simulators.led_sim import led_sim
from simulators.button_sim import button_sim
from simulators.rgb_led_sim import rgb_sim
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
from simulators.ultrasonic_sim import ultrasonic_sim
from simulators.gyroscope_sim import gyro_simulator
from simulators.dht_sim import dht_simulator
from simulators._4sd_sim import run_4sd_simulator
from sensors.gyro.gyro import run_gyro_real
from simulators.ir_sim import ir_sim
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
    "ultrasonic":{
        "true":run_ultrasonic_real,
        "sim":ultrasonic_sim
    },
    "gyro": {
        "true": run_gyro_real,
        "sim": gyro_simulator
    },
    "dht": {
        "true":run_dht_real,
        "sim": dht_simulator
    },
    "ir":{
        "true":run_ir_real,
        "sim":ir_sim
    }
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
    "7segment": {
        "true": None,
        "sim": run_4sd_simulator
    },
    "lcd":{
        "true":run_lcd_real,
        "sim":lcd_sim
    },
    "rgb_led": {
        "true": run_rgb_real,
        "sim": rgb_sim
    }
}