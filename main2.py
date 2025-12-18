import threading
import time
from settings import load_settings
from registry import SENSOR_REGISTRY, ACTUATOR_REGISTRY

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    GPIO = None


def main():
    print("Starting app")

    settings = load_settings()
    threads = []
    stop_event = threading.Event()

    print(f"Mode: {settings['mode']} | Runs on: {settings['runs_on']}")

    sensors = settings.get("sensors", {})
    actuators = settings.get("actuators", {})

    for act in actuators.values():
        act["state"] = False

    def on_event(device_code, field, value):
        print(f"[EVENT] {device_code} | {field} = {value}")

        if device_code == "KB1" and value == "b":
            buzzer = actuators.get("DB")
            if buzzer:
                buzzer["state"] = not buzzer["state"]

    for sensor_code, sensor_cfg in sensors.items():

        if not sensor_cfg.get("simulated", False):
            continue

        runner = SENSOR_REGISTRY.get(sensor_cfg["type"])
        if not runner:
            print(f"[WARN] No sensor runner for {sensor_cfg['type']}")
            continue

        kwargs = {
            "sensor_code": sensor_code,
            "delay": sensor_cfg.get("delay", 0.1),
            "stop_event": stop_event,
            "settings": sensor_cfg,
        }

        if sensor_cfg["type"] in ["keyboard", "membrane"]:
            kwargs["on_value"] = lambda c, s, v: on_event(
                c, s.get("field_name", "value"), v
            )
        else:
            kwargs["on_state_change"] = lambda c, s, v: on_event(
                c, s.get("field_name", "active"), v
            )

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)

    for act_code, act_cfg in actuators.items():

        if not act_cfg.get("simulated", False):
            continue

        runner = ACTUATOR_REGISTRY.get(act_cfg["type"])
        if not runner:
            print(f"[WARN] No actuator runner for {act_cfg['type']}")
            continue

        if act_cfg["type"] == "led":
            kwargs = {
                "actuator_code": act_code,
                "delay": act_cfg.get("delay", 0.5),
                "stop_event": stop_event,
                "settings": act_cfg,
                "on_state_change": lambda c, s, v: print(
                    f"[ACTUATOR] {c} = {v}"
                ),
            }

        elif act_cfg["type"] == "buzzer":
            kwargs = {
                "actuator_code": act_code,
                "stop_event": stop_event,
                "settings": act_cfg,
                "on_state_change": lambda c, s, v: print(
                    f"[ACTUATOR] {c} = {v}"
                ),
            }

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
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
