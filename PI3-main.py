import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

# settings
settings = load_settings_spec('PI3-settings.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client()

# --- GLOBALNO STANJE ZA PI3 ---
state = {
    "rgb_on": False,
    "rgb_color": [0, 0, 0],   # [R,G,B] 0/1
    "dht": {
        "DHT1": None,
        "DHT2": None,
        "DHT3": None
    }
}



batch_lock = threading.Lock()
data_batch = []

# MQTT CALLBACKSa
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/commands/PI3/#")
    client.subscribe("home/PI3/dht1")
    client.subscribe("home/PI3/dht2")
    client.subscribe("home/PI2/dht3")


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    topic = msg.topic
    device = topic.split("/")[-1].upper()

    # --- DHT CACHE ---
    if device in ["DHT1", "DHT2"]:
        state["dht"][device] = payload
        return

    if topic == "home/PI2/dht3":
        state["dht"]["DHT3"] = payload
        return

    # --- WEB RGB COMMAND ---
    if device == "BRGB":
        state["rgb_on"] = bool(payload.get("value", False))
        if "color" in payload:
            state["rgb_color"] = payload["color"]

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(
    mqtt_config.get("broker", "localhost"),
    mqtt_config.get("port", 1883),
    60
)
mqtt_client.loop_start()

# ================= LOGIC =================
def process_logic(device_code, value):
    # ----- IR BUTTONS -----
    if device_code == "IR":
        if value == "POWER":
            state["rgb_on"] = not state["rgb_on"]

        elif value == "COLOR_UP":
            state["rgb_color"] = [1, 0, 0]  # RED

        elif value == "COLOR_DOWN":
            state["rgb_color"] = [0, 0, 1]  # BLUE

    # ----- PIR3 → ALARM NOTIFY -----
    if device_code == "DPIR3" and value:
        mqtt_client.publish(
            "home/PI3/alarm_trigger",
            json.dumps({
                "reason": "DPIR3 motion detected",
                "value": True
            })
        )

# ================= EVENT =================
def on_event(device_code, field, value, topic, simulated):
    process_logic(device_code, value)

    data = {
        "measurement": "iot_devices",
        "device": device_code,
        "pi": "PI3",
        "field": field,
        "value": value,
        "topic": topic
    }

    with batch_lock:
        data_batch.append(data)

# ================= LCD ROTATION =================
def lcd_rotation():
    dht_keys = ["DHT1", "DHT2", "DHT3"]
    idx = 0

    while True:
        key = dht_keys[idx % 3]
        data = state["dht"].get(key)

        if data:
            msg = f"{key}: {data['temperature']}C {data['humidity']}%"
            mqtt_client.publish(
                "home/lcd",
                json.dumps({"value": msg})
            )

        idx += 1
        time.sleep(4)

# ================= PUBLISHER =================
def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(mqtt_config.get("publish_interval", 5))
        with batch_lock:
            for item in data_batch:
                mqtt_client.publish(item["topic"], json.dumps(item))
            data_batch.clear()

# ================= MAIN =================
def main():
    stop_event = threading.Event()

    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()
    threading.Thread(target=lcd_rotation, daemon=True).start()

    # --- SENSORS ---
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY[cfg["type"]]
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]

        threading.Thread(
            target=runner,
            kwargs={
                "sensor_code": code,
                "delay": cfg.get("delay", 2),
                "stop_event": stop_event,
                "on_value": lambda c, f, v, t=cfg["topic"]:
                    on_event(c, f, v, t, True),
                "settings": cfg
            },
            daemon=True
        ).start()

    # --- ACTUATORS ---
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY[cfg["type"]]
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]

        threading.Thread(
            target=runner,
            kwargs={
                "actuator_code": code,
                "stop_event": stop_event,
                "settings": cfg,
                "on_state_change":
                    lambda c, s, v, t=cfg["topic"]:
                        on_event(c, "state", v, t, True)
            },
            daemon=True
        ).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()


