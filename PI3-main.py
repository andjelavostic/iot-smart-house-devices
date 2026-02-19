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
    command = value
    if isinstance(value, dict): command = value.get("value", "")

    if device_code == "IR" or device_code == "BRGB":
        if command == "POWER":
            state["rgb_on"] = not state["rgb_on"]
        elif command == "COLOR_RED":
            state["rgb_on"] = True
            state["rgb_color"] = [1, 0, 0]
        elif command == "COLOR_BLUE":
            state["rgb_on"] = True
            state["rgb_color"] = [0, 0, 1]
        elif command == "COLOR_GREEN":
            state["rgb_on"] = True
            state["rgb_color"] = [0, 1, 0]
        elif command == "COLOR_PURPLE":
            state["rgb_on"] = True
            state["rgb_color"] = [1, 0, 1]
        
        final_color = state["rgb_color"] if state["rgb_on"] else [0, 0, 0]
        
        # Ažuriraj settings za simulator
        for code, cfg in settings.get("actuators", {}).items():
            if cfg["type"] == "rgb_led":
                cfg["color"] = final_color
        
        # Javi frontu nazad da promeni kvadratić
        mqtt_client.publish("home/PI3/rgb", json.dumps({
            "pi": "PI3", "device": "BRGB", "value": final_color
        }))
    if device_code == "DPIR3" and value:
        if state["people_count"] == 0:
            mqtt_client.publish("home/PI3/alarm_trigger",
                json.dumps({
                    "reason": f"{device_code} motion while empty",
                    "value": True
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
    global state
    
    try:
        payload = json.loads(msg.payload.decode())
        topic = msg.topic
        device_code = topic.split('/')[-1].upper()

        # Sinhronizacija broja ljudi (Zahtjev 5)
        if "people_count" in topic:
            state["people_count"] = int(payload.get("value", 0))
            return
        
        # --- 1. KOMANDE SA DASHBOARDA (Web tasteri) ---
        if topic.startswith("home/commands/PI3"):
            device = device_code
            # Izvlačimo vrednost (za RGB to može biti 0/1 ili boja)
            val = payload.get("value")
            
            # Mapiranje boja sa weba u komande koje process_logic razume
            if device == "BRGB":
                color_list = payload.get("color")
                if val == 0:
                    command = "POWER"
                elif color_list == [1, 0, 0]:
                    command = "COLOR_RED"
                elif color_list == [0, 0, 1]:
                    command = "COLOR_BLUE"
                elif color_list == [0, 1, 0]:
                    command = "COLOR_GREEN"
                elif color_list == [1, 0, 1]:
                    command = "COLOR_PURPLE"
                else:
                    command = "POWER" # ili neka default vrednost
                
                # Pozivamo logiku da ažurira state i settings
                process_logic(device, command, None)
            return

        # --- 2. AŽURIRANJE LCD-a ---
        if topic == "home/PI3/lcd":
            for code, cfg in settings.get("actuators", {}).items():
                if cfg["type"] == "lcd":
                    cfg["message"] = payload.get("value", "---")
            return

        # --- 3. DHT PODACI (Sinhronizacija za LCD rotaciju) ---
        if topic == "home/PI2/dht3":
            state["dht"]["DHT3"] = payload
            return

        device_name = topic.split("/")[-1].upper()
        if device_name in ["DHT1", "DHT2"]:
            state["dht"][device_name] = payload

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
        time.sleep(2)

# ================= PUBLISHER & MAIN =================

def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(2)
        with batch_lock:
            if data_batch:
                for item in data_batch:
                    mqtt_client.publish(item["topic"], json.dumps(item))
                data_batch.clear()
# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/commands/PI3/#")
    client.subscribe("home/PI1/people_count") # Slušamo broj ljudi sa PI1
    client.subscribe("home/PI2/dht3")
    client.subscribe("home/PI3/#")
def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start()

    stop_event = threading.Event()
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()
    threading.Thread(target=lcd_rotation, daemon=True).start()

    # --- SENSORS (IR, DPIR, DHT) ---
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY[cfg["type"]]
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]
        cb = "on_value" if cfg["type"] in ["dht", "ir"] else "on_state_change"
        threading.Thread(target=runner, kwargs={
            "sensor_code": code, "delay": cfg.get("delay", 5), # Povećaj delay za IR!
            "stop_event": stop_event, "settings": cfg, cb: on_event
        }, daemon=True).start()

    # --- ACTUATORS (LCD, RGB) ---
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY[cfg["type"]]
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]
        threading.Thread(target=runner, kwargs={
            "actuator_code" if cfg["type"]=="lcd" else "actuator_code": code,
            "stop_event": stop_event, "settings": cfg, "on_state_change": on_event
        }, daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()