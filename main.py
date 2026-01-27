import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

# --- KONFIGURACIJA ---
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except ImportError:
    GPIO = None

settings = load_settings()
sensors = settings.get("sensors", {})
actuators = settings.get("actuators", {})

# --- MQTT SETUP ---
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to MQTT broker")
    else:
        print(f"Failed to connect, return code {rc}")

mqtt_client.on_connect = on_connect
mqtt_client.connect(mqtt_config.get("broker", "localhost"), mqtt_config.get("port", 1883), 60)
mqtt_client.loop_start()

# --- LOGIKA DOGAĐAJA ---
def on_event(device_code, field, value, topic):
    # 1. Ispis u konzolu
    print(f"[EVENT] {device_code} | {field} = {value} | Topic: {topic}")

    # 2. Slanje na MQTT
    payload = {
        "measurement": "iot_devices",
        "device": device_code,
        "field": field,
        "value": value
    }
    mqtt_client.publish(topic, json.dumps(payload))

    # 3. Interna logika za aktuatore
    if device_code == "KB1" and value == "b":
        buzzer = actuators.get("DB")
        if buzzer:
            buzzer["state"] = not buzzer["state"]
    if device_code == "KB1" and value == "l":
        led = actuators.get("DL")
        if led:
            led["state"] = not led["state"]

def main():
    print("Starting app")
    threads = []
    stop_event = threading.Event()

    print(f"Mode: {settings['mode']} | Runs on: {settings['runs_on']}")

    # Pokretanje senzora
    for sensor_code, sensor_cfg in sensors.items():
        if not sensor_cfg.get("simulated", False):
            continue

        runner = SENSOR_REGISTRY.get(sensor_cfg["type"])
        if not runner:
            continue

        # Uzimamo topic direktno iz JSON podešavanja za svaki senzor
        topic = sensor_cfg.get("topic", f"home/{sensor_code}")

        kwargs = {
            "sensor_code": sensor_code,
            "delay": sensor_cfg.get("delay", 0.1),
            "stop_event": stop_event,
            "settings": sensor_cfg,
        }

        # Podešavanje callback-a tako da prosleđuje i topic
        if sensor_cfg["type"] in ["keyboard", "membrane", "ultrasonic"]:
            kwargs["on_value"] = lambda c, s, v, t=topic: on_event(
                c, s.get("field_name", "value"), v, t
            )
        else:
            kwargs["on_state_change"] = lambda c, s, v, t=topic: on_event(
                c, s.get("field_name", "active"), v, t
            )

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)

    # Pokretanje aktuatora
    for act_code, act_cfg in actuators.items():
        if not act_cfg.get("simulated", False):
            continue

        runner = ACTUATOR_REGISTRY.get(act_cfg["type"])
        if not runner:
            continue

        kwargs = {
            "actuator_code": act_code,
            "stop_event": stop_event,
            "settings": act_cfg,
            "on_state_change": lambda c, s, v: print(f"[ACTUATOR] {c} state changed to: {v}"),
        }

        t = threading.Thread(target=runner, kwargs=kwargs, daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping app...")
        stop_event.set()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()