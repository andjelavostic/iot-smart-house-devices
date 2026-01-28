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

batch_lock = threading.Lock()
data_batch = []

settings = load_settings()
sensors = settings.get("sensors", {})
actuators = settings.get("actuators", {})
mqtt_config = settings.get("mqtt", {})

BATCH_SIZE = mqtt_config.get("batch_size", 5)
PUBLISH_INTERVAL = mqtt_config.get("publish_interval", 5)

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

def on_event(device_code, field, value, topic, is_simulated):
    global data_batch
    
    payload = {
        "measurement": "iot_devices",
        "device": device_code,
        "pi": settings.get("runs_on", "PI1"),
        "hostname": settings.get("device_hostname", "Unknown"),
        "field": field,
        "value": value,
        "simulated": is_simulated,
        "topic": topic
    }

    with batch_lock:
        data_batch.append(payload)
        print(f"[BUFFER] Dodat {device_code} ({field}={value}). Bafer: {len(data_batch)}/{BATCH_SIZE}")

def publisher_task(stop_event):
    """
    Generička daemon nit koja periodično šalje batch-eve na MQTT.
    """
    global data_batch
    while not stop_event.is_set():
        time.sleep(PUBLISH_INTERVAL)
        
        batch_to_send = []
        with batch_lock:
            # Ako je bafer pun ili je prošao interval, šaljemo sve
            if len(data_batch) >= BATCH_SIZE or len(data_batch) > 0:
                batch_to_send = data_batch.copy()
                data_batch.clear()
        
        if batch_to_send:
            print(f"\n[MQTT] Šaljem batch od {len(batch_to_send)} poruka...")
            for item in batch_to_send:
                # Topic se koristi za slanje, ali se ne šalje u samom JSON-u u bazu
                target_topic = item.pop("topic")
                mqtt_client.publish(target_topic, json.dumps(item))
            print("[MQTT] Batch poslat.\n")

def main():
    print(f"Starting PI1: {settings.get('device_hostname')} on {settings.get('runs_on')}")
    stop_event = threading.Event()
    threads = []

    # Pokretanje DAEMON niti za batch slanje
    pub_thread = threading.Thread(target=publisher_task, args=(stop_event,), daemon=True)
    pub_thread.start()

    # Pokretanje senzora
    for sensor_code, sensor_cfg in sensors.items():
        if not sensor_cfg.get("simulated", False):
            continue
        runner = SENSOR_REGISTRY.get(sensor_cfg["type"])
        if not runner:
            continue

        topic = sensor_cfg.get("topic", f"home/{sensor_code}")
        sim = sensor_cfg.get("simulated", True)

        kwargs = {
            "sensor_code": sensor_code,
            "delay": sensor_cfg.get("delay", 0.1),
            "stop_event": stop_event,
            "settings": sensor_cfg,
        }

        # Prosleđujemo 'sim' i 'topic' u callback
        if sensor_cfg["type"] in ["keyboard", "membrane", "ultrasonic"]:
            kwargs["on_value"] = lambda c, s, v, t=topic, is_sim=sim: on_event(
                c, s.get("field_name", "value"), v, t, is_sim
            )
        else:
            kwargs["on_state_change"] = lambda c, s, v, t=topic, is_sim=sim: on_event(
                c, s.get("field_name", "active"), v, t, is_sim
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