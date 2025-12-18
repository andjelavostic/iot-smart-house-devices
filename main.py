import threading
import time
from settings import load_settings
from registry import SENSOR_REGISTRY

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    GPIO = None


def default_on_event(sensor_code, field, value):
    print(f"[EVENT] {sensor_code} | {field} = {value}")

def main():
    print("Starting app")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    print(f"Mode: {settings['mode']} | Runs on: {settings['runs_on']}")

    sensors = settings.get("sensors", {})

    for sensor_code, sensor_cfg in sensors.items():

        if not sensor_cfg.get("simulated", False):
            continue

        runner = SENSOR_REGISTRY.get(sensor_cfg["type"])
        if not runner:
            print(f"[WARN] No runner for {sensor_cfg['type']}")
            continue

        t = threading.Thread(
            target=runner,
            kwargs={
                "sensor_code": sensor_code,
                "delay": sensor_cfg.get("delay", 1),
                "on_state_change": lambda c, s, v: default_on_event(
                    c,
                    sensor_cfg["field_name"],
                    v
                ),
                "stop_event": stop_event,
                "settings": sensor_cfg
            },
            daemon=True
        )
        t.start()
        threads.append(t)

    try:
        print("System running. Press CTRL+C to stop.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping app...")
        stop_event.set()

        for t in threads:
            t.join(timeout=2)

        print("System stopped cleanly.")

if __name__ == "__main__":
    main()
