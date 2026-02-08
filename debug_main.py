import threading
import time
from settings import load_settings
from registry import SENSOR_REGISTRY, ACTUATOR_REGISTRY

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    GPIO = None

def terminal_callback(device_code, field_name, value):
    """ funkcija koja mijenja on_event i direktno ispisuje u terminal """
    timestamp = time.strftime("%H:%M:%S")
    # format: [Vrijeme] [Uređaj] Polje -> Vrijednost
    print(f"[{timestamp}] [{device_code}] {field_name.upper()}: {value}")

def run_debug():
    settings = load_settings()
    sensors = settings.get("sensors", {})
    actuators = settings.get("actuators", {})
    
    stop_event = threading.Event()
    threads = []

    print("\n" + "="*50)

    # pokretanje senzora
    for s_code, s_cfg in sensors.items():
        is_sim = s_cfg.get("simulated", True)
        entry = SENSOR_REGISTRY.get(s_cfg["type"])
        
        if isinstance(entry, dict):
            runner = entry["sim"] if is_sim else entry["true"]
        else:
            runner = entry # za senzore koji imaju samo sim verziju

        if not runner:
            continue

        kwargs = {
            "sensor_code": s_code,
            "settings": s_cfg,
            "stop_event": stop_event,
            "delay": s_cfg.get("delay", 2)
        }

        # callback za terminal
        callback = lambda c, s, v: terminal_callback(c, s.get("field_name", "data"), v)
        
        # jer različiti senzori koriste različite nazive za callback funkcije
        if s_cfg["type"] in ["keyboard", "membrane", "ultrasonic"]:
            kwargs["on_value"] = callback
        else:
            kwargs["on_state_change"] = callback

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)
        mode = "SIMULATOR" if is_sim else "HARDWARE"
        print(f"pokrenut senzor: {s_code} [{mode}]")

    # akuratori
    for a_code, a_cfg in actuators.items():
        is_sim = a_cfg.get("simulated", True)
        entry = ACTUATOR_REGISTRY.get(a_cfg["type"])
        
        if isinstance(entry, dict):
            runner = entry["sim"] if is_sim else entry["true"]
        else:
            runner = entry

        if not runner:
            continue

        kwargs = {
            "actuator_code": a_code,
            "stop_event": stop_event,
            "settings": a_cfg,
            "on_state_change": lambda c, s, v: terminal_callback(c, "status", v)
        }

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)
        mode = "SIMULATOR" if is_sim else "HARDWARE"
        print(f"pokrenut aktuator: {a_code} [{mode}]")


    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping...")
        stop_event.set()
        if GPIO:
            GPIO.cleanup()

if __name__ == "__main__":
    run_debug()