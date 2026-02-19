import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

settings = load_settings_spec('PI3-settings.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

state = {
    "rgb_on": True,
    "rgb_color": [0, 0, 0],
    "dht": {"DHT1": None, "DHT2": None, "DHT3": None},
    "people_count": 0 
}

batch_lock = threading.Lock()
data_batch = []

def process_logic(device_code, value, settings_cfg):
    global state
    
    # Ako je vrednost došla kao rečnik (sa MQTT-a ili simulatora), uzmi samo string komandu
    command = value
    if isinstance(value, dict):
        command = value.get("value", "")

    # --- RGB LOGIKA ---
    if device_code == "IR" or device_code == "BRGB":
        if command == "POWER":
            state["rgb_on"] = not state["rgb_on"]
        if command in ["COLOR_RED"]: # Dodaj nazive tvojih dugmića
            state["rgb_color"] = [1, 0, 0]
        elif command in ["COLOR_BLUE"]:
            state["rgb_color"] = [0, 0, 1]
        elif command in ["COLOR_GREEN"]:
            state["rgb_color"] = [0, 1, 0]
        elif command in ["COLOR_PURPLE"]:
            state["rgb_color"] = [1, 0, 1]
        
        
        final_color = state["rgb_color"] if state["rgb_on"] else [0, 0, 0]
        # KLJUČNA IZMENA: Nađi RGB u settings i promeni mu boju
        for code, cfg in settings.get("actuators", {}).items():
            if cfg["type"] == "rgb_led":
                cfg["color"] = final_color  # Sada će simulator u sledećoj iteraciji videti ovo!
        
        # Obaveštavamo Dashboard (JS traži data.device === "BRGB" i data.value kao niz)
        mqtt_client.publish("home/PI3/rgb", json.dumps({
            "pi": "PI3", 
            "device": "BRGB", 
            "value": final_color
        }))
        # --- PEOPLE COUNT ---
        if device_code == "DPIR3" and value == True:
            state["people_count"] += 1
            # BITNO: Šaljemo measurement "people" da bi Dashboard prepoznao!
            mqtt_client.publish("home/PI3/people_count", json.dumps({
                "measurement": "people", 
                "value": state["people_count"], 
                "device": "SYSTEM", 
                "pi": "PI3"
            }))


# ================= EVENT HANDLER =================

def on_event(device_code, settings_cfg, value):
    if device_code == "LCD": return 

    # BITNO: Ako je IR, 'value' je često string. Ako je DHT, 'value' je rečnik.
    # Za Dashboard IR ispis, moramo poslati čistu komandu.
    clean_value = value
    if isinstance(value, dict) and "value" in value:
        clean_value = value["value"]

    process_logic(device_code, clean_value, settings_cfg)

    # Ovo ide u bazu/publisher
    data = {
        "measurement": "iot_devices",
        "device": device_code,
        "pi": "PI3",
        "field": settings_cfg.get("field_name", "value"),
        "value": clean_value, # Šaljemo čistu vrednost (npr. "POWER" umesto {} )
        "topic": settings_cfg.get("topic", "unknown")
    }

    with batch_lock:
        data_batch.append(data)
    
    # Odmah pošalji na specifičan topic za front da IR ne bi kasnio
    mqtt_client.publish(settings_cfg.get("topic"), json.dumps(data))
# ================= MQTT CALLBACKS =================

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        
        # Ažuriranje LCD simulatora direktno!
        if topic == "home/PI3/lcd":
            # Menjamo poruku u settings-u koji simulator čita
            for code, cfg in settings.get("actuators", {}).items():
                if cfg["type"] == "lcd":
                    cfg["message"] = payload.get("value", "---")
            return

        if topic == "home/PI2/dht3":
            state["dht"]["DHT3"] = payload
            return

        device = topic.split("/")[-1].upper()
        if device in ["DHT1", "DHT2"]:
            state["dht"][device] = payload

    except Exception as e:
        print(f"Error on_message: {e}")

# ================= LCD ROTACIJA =================

def lcd_rotation():
    dht_keys = ["DHT1", "DHT2", "DHT3"]
    idx = 0
    while True:
        key = dht_keys[idx % 3]
        raw_data = state["dht"].get(key)
        
        temp, hum = "--", "--"
        
        if raw_data:
            # Ako je podatak rečnik (što DHT jeste)
            if isinstance(raw_data, dict):
                # Proveravamo da li je simulator spakovao u "value" ključ
                inner = raw_data.get("value", raw_data)
                if isinstance(inner, dict):
                    temp = inner.get('temperature') or inner.get('temp', '--')
                    hum = inner.get('humidity') or inner.get('hum', '--')
            
            msg = f"{key}:T={temp}C H={hum}%"
        else:
            msg = f"Waiting {key}..."
            
        # Slanje na MQTT (sa device: "LCD" da bi Dashboard prepoznao)
        mqtt_client.publish("home/PI3/lcd", json.dumps({
            "value": msg, 
            "pi": "PI3", 
            "device": "LCD",
            "measurement": "iot_devices"
        }))
        
        idx += 1
        time.sleep(4)

# ================= PUBLISHER & MAIN =================

def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(2)
        with batch_lock:
            if data_batch:
                for item in data_batch:
                    mqtt_client.publish(item["topic"], json.dumps(item))
                data_batch.clear()

def main():
    mqtt_client.on_connect = lambda c, u, f, rc: [c.subscribe("home/commands/PI3/#"), c.subscribe("home/PI3/#"), c.subscribe("home/PI2/dht3")]
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start()

    stop_event = threading.Event()
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()
    threading.Thread(target=lcd_rotation, daemon=True).start()

    # --- SENSORS (IR, DPIR, DHT) ---
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY[cfg["type"]]
        cb = "on_value" if cfg["type"] in ["dht", "ir"] else "on_state_change"
        threading.Thread(target=entry["sim"], kwargs={
            "sensor_code": code, "delay": cfg.get("delay", 5), # Povećaj delay za IR!
            "stop_event": stop_event, "settings": cfg, cb: on_event
        }, daemon=True).start()

    # --- ACTUATORS (LCD, RGB) ---
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY[cfg["type"]]
        threading.Thread(target=entry["sim"], kwargs={
            "actuator_code" if cfg["type"]=="lcd" else "actuator_code": code,
            "stop_event": stop_event, "settings": cfg, "on_state_change": on_event
        }, daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()