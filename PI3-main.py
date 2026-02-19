import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

# 1. Postavke i MQTT
settings = load_settings_spec('PI3-settings.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

state = {
    "rgb_on": False,
    "rgb_color": [0, 0, 0],
    "dht": {"DHT1": None, "DHT2": None, "DHT3": None},
    "people_count": 0  # Dodato za People Count logiku
}

batch_lock = threading.Lock()
data_batch = []

# ================= LOGIKA (People Count & RGB) =================

def process_logic(device_code, value):
    # --- IR Daljinac & Web Komande ---
    if device_code == "IR" or device_code == "BRGB":
        # Rešavanje "object object" problema:
        command = value
        if isinstance(value, dict):
            command = value.get("value", "")

        if command == "POWER":
            state["rgb_on"] = not state["rgb_on"]
        elif command == "COLOR_UP" or command == "RED":
            state["rgb_color"] = [1, 0, 0]
        elif command == "COLOR_DOWN" or command == "BLUE":
            state["rgb_color"] = [0, 0, 1]
        
        # Slanje finalne boje aktuatoru
        final_color = state["rgb_color"] if state["rgb_on"] else [0,0,0]
        mqtt_client.publish("home/PI3/rgb", json.dumps({"value": final_color}))

    # --- People Count (PIR3) ---
    if device_code == "DPIR3" and value == True:
        state["people_count"] += 1
        print(f"Motion detected on DPIR3. People count: {state['people_count']}")
        
        # Slanje Alarm Triggera po specifikaciji
        mqtt_client.publish("home/PI3/alarm_trigger", 
                            json.dumps({"reason": "DPIR3 motion", "people_count": state["people_count"]}))
        
        # Slanje ažuriranog broja ljudi na dashboard (ako PI3 ima svoj topik za to)
        mqtt_client.publish("home/PI3/people_count", json.dumps({"value": state["people_count"]}))

# ================= EVENT HANDLER =================

def on_event(device_code, settings_cfg, value):
    topic = settings_cfg.get("topic", "unknown")
    field = settings_cfg.get("field_name", "value")

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

# ================= MQTT CALLBACKS =================

def on_connect(client, userdata, flags, rc):
    print("PI3 Connected to MQTT broker")
    client.subscribe("home/commands/PI3/#")
    client.subscribe("home/PI3/dht1")
    client.subscribe("home/PI3/dht2")
    client.subscribe("home/PI2/dht3") # Slušamo DHT3 sa drugog PI-ja

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        
        # 1. DHT3 sa PI2
        if topic == "home/PI2/dht3":
            state["dht"]["DHT3"] = payload
            return

        # 2. DHT1 i DHT2 sa PI3
        device = topic.split("/")[-1].upper()
        if device in ["DHT1", "DHT2"]:
            state["dht"][device] = payload
            return

        # 3. BRGB (Web komanda)
        if device == "BRGB":
            # Ako Dashboard šalje direktno boju
            if "color" in payload:
                state["rgb_color"] = payload["color"]
                state["rgb_on"] = True
            elif "value" in payload:
                # Ako šalje komande tipa "RED", "BLUE" ili 0/1
                process_logic("BRGB", payload["value"])
                return

            final_color = state["rgb_color"] if state["rgb_on"] else [0,0,0]
            mqtt_client.publish("home/PI3/rgb", json.dumps({"value": final_color}))

    except Exception as e:
        print(f"Error on_message: {e}")

# ================= LCD ROTACIJA =================

def lcd_rotation():
    dht_keys = ["DHT1", "DHT2", "DHT3"]
    idx = 0
    while True:
        key = dht_keys[idx % 3]
        data = state["dht"].get(key)
        
        if data:
            temp = data.get('temperature', '--')
            hum = data.get('humidity', '--')
            msg = f"{key}: T={temp}C H={hum}%"
            mqtt_client.publish("home/PI3/lcd", json.dumps({"value": msg}))
        else:
            # Ako nema podataka, ispiši bar da se čeka
            mqtt_client.publish("home/PI3/lcd", json.dumps({"value": f"Waiting {key}..."}))
            
        idx += 1
        time.sleep(4)

def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(mqtt_config.get("publish_interval", 5))
        with batch_lock:
            for item in data_batch:
                mqtt_client.publish(item["topic"], json.dumps(item))
            data_batch.clear()

# ================= MAIN =================

def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_config.get("broker", "localhost"), mqtt_config.get("port", 1883), 60)
    mqtt_client.loop_start()

    stop_event = threading.Event()
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()
    threading.Thread(target=lcd_rotation, daemon=True).start()

    # --- SENSORS ---
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY[cfg["type"]]
        runner = entry["sim"]
        
        callback_name = "on_state_change" if cfg["type"] == "pir" else "on_value"
        
        args = {
            "sensor_code": code,
            "delay": cfg.get("delay", 2),
            "stop_event": stop_event,
            "settings": cfg,
            callback_name: on_event
        }
        threading.Thread(target=runner, kwargs=args, daemon=True).start()

    # --- ACTUATORS ---
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY[cfg["type"]]
        runner = entry["sim"]

        # Određujemo ime callback-a
        callback_name = "on_value" if cfg["type"] == "lcd" else "on_state_change"
        
        # DODATO: delay je obavezan za lcd_sim, pa ga izvlačimo iz podešavanja
        delay = cfg.get("delay", 2) 

        args = {
            "stop_event": stop_event,
            "settings": cfg,
            callback_name: on_event
        }

        # Usklađivanje naziva koda (neki simulatori traže sensor_code, neki actuator_code)
        if cfg["type"] == "rgb_led": 
            args["actuator_code"] = code
        if cfg["type"] == "lcd": 
            args["sensor_code"] = code 

        threading.Thread(target=runner, kwargs=args, daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()