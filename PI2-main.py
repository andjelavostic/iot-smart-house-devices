import threading
import time
import json
import math
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

settings = load_settings_spec('PI2-settings.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client()

# GLOBALNO STANJE ZA PI2
state = {
    "people_count": 0,
    "last_distances": [],
    "ds2_trigger_time": None,
    "alarm_active": False,
    # TIMER (Štoperica)
    "timer_value": 0,
    "timer_running": False,
    "timer_blink": False,
    "timer_add_seconds": 10  # Broj sekundi koji BTN dodaje
}

batch_lock = threading.Lock()
data_batch = []

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/commands/PI2/#")
    client.subscribe("home/PI1/people_count") # Slušamo broj ljudi sa PI1

def on_message(client, userdata, msg):
    global state
    payload = json.loads(msg.payload.decode())
    topic = msg.topic
    device_code = topic.split('/')[-1].upper()

    if "home/commands/PI2" in topic:
            value = payload.get("value")
            if device_code == "BTN_CONFIG":
                state["timer_add_seconds"] = int(value)
                print(f"[BTN] add {state['timer_add_seconds']}")
                print(f"[TIMER CONFIG] Dugme sada dodaje {state['timer_add_seconds']} sekundi")
                return

            if device_code == "TIMERSET":
                state["timer_value"] = int(value)
                state["timer_running"] = True
                state["timer_blink"] = False
                print(f"[TIMERSET] value={value}")
                publish_display(state["timer_value"])
                return
    
    # Sinhronizacija broja ljudi
    if "people_count" in topic:
        state["people_count"] = int(payload.get("value", 0))
        return

    # Aktuatori (BB, BRGB...)
    for code, cfg in settings.get("actuators", {}).items():
        if code == device_code:
            cfg["state"] = payload.get("value", False)
            if "color" in payload:
                cfg["color"] = payload["color"]

def publish_display(seconds):
    mins, secs = divmod(seconds, 60)
    time_str = f"{mins:02d}:{secs:02d}"
    print(f"[DISPLAY] {time_str}")
    mqtt_client.publish(
        "home/PI2/4sd",
        json.dumps({
            "measurement": "iot_devices",
            "device": "4SD",
            "pi": "PI2",
            "field": "display_time",
            "value": time_str
        })
    )

def on_event(device_code, settings_cfg, value, topic, simulated):
    global data_batch
    
    # prvo obradi logiku za uređaj
    process_logic(device_code, value, settings_cfg)

    field_name = settings_cfg.get("field_name", "value")

    #num podaci: int/float
    #timer (4SD) i string polja: string
    #DHT3 i GSG: šaljemo dict u value
    if device_code == "4SD":
        send_value = str(value)   # timer kao string
    elif device_code == "DHT3" or device_code == "GSG":
        send_value = value        # dict, front čita JSON
    elif isinstance(value, (int, float)):
        send_value = value
    elif isinstance(value, str):
        send_value = value
    else:
        send_value = str(value)   # fallback u string

    data = {
        "measurement": "iot_devices",
        "device": device_code,
        "pi": "PI2",
        "field": field_name,
        "value": send_value,
        "topic": topic
    }

    with batch_lock:
        data_batch.append(data)

def process_logic(device_code, value, settings_cfg):
    global state, mqtt_client

    # 1. BTN - Štoperica
    if device_code == "BTN" and value:
        # Ako treperi → zaustavi
        if state["timer_blink"]:
            state["timer_blink"] = False
            state["timer_running"] = False
            state["timer_value"] = 0
            publish_display(0)
            return

        # Inače dodaj sekunde
        state["timer_value"] += state["timer_add_seconds"]
        state["timer_running"] = True
        publish_display(state["timer_value"])

    # 3. DS2 - POPRAVLJENO (Vrata sama gase svoj alarm kad se zatvore)
    if device_code == "DS2":
        if value:  # Vrata otvorena
            state["ds2_trigger_time"] = time.time()
            mqtt_client.publish("home/PI2/door_event",json.dumps({"event": "door_open"}))
            
            # Provera za "zaboravljena vrata" (5s)
            def check_ds2_stuck():
                if state.get("ds2_trigger_time") is not None:
                    mqtt_client.publish("home/PI2/door_event",json.dumps({"event": "door_stuck_pi2"}))
            threading.Timer(5.0, check_ds2_stuck).start()
        else:
            state["ds2_trigger_time"] = None
            mqtt_client.publish("home/PI2/door_event",json.dumps({"event": "door_closed"}))

    # 4. GSG - Žiroskop 
    if device_code == "GSG":
        accel = value.get("accel", [0,0,0])
        magnitude = math.sqrt(sum([x**2 for x in accel]))
        if magnitude > 3.5:
            mqtt_client.publish("home/PI2/gsg_event",json.dumps({"reason": "GSG movement detected", "value": True}))

    # 5. DUS2 / DPIR2 - Brojanje ljudi (Ostaje tvoje)
    if device_code == "DUS2":
        state["last_distances"].append(value)
        if len(state["last_distances"]) > 5:
            state["last_distances"].pop(0)

    if device_code == "DPIR2" and value and len(state["last_distances"]) >= 3:
        first = state["last_distances"][0]
        last = state["last_distances"][-1]

        if last < first:
            direction = "enter"
            state["people_count"] += 1
        else:
            direction = "exit"
            state["people_count"] = max(0, state["people_count"] - 1)

        mqtt_client.publish("home/PI2/person_event", json.dumps({"measurement": "people", "value": state["people_count"], 
            "device": "SYSTEM", "pi": "PI2", "field": "count","direction":direction
        }))

    # 6. DPIR2 - Alarm kad je prazno (Ostaje tvoje)
    if "DPIR2" in device_code and value and state["people_count"] == 0:
        mqtt_client.publish("home/PI2/motion_event",json.dumps({"motion": True, "device": "DPIR2"}))

    # 7. DHT3 (Ostaje tvoje)
    if device_code == "DHT3":
        mqtt_client.publish("home/PI2/dht3", json.dumps({
            "temperature": value.get("temperature"),
            "humidity": value.get("humidity"), "pi": "PI2"
        }))

    # 4SD Timer display
    if device_code == "4SD":
        pass  #obrađeno u on_event()

# timer thread (4SD) 
def timer_thread():
    global state

    while True:

        if state["timer_running"] and state["timer_value"] > 0:
            time.sleep(1)
            state["timer_value"] -= 1

            publish_display(state["timer_value"])

            if state["timer_value"] <= 0:
                state["timer_running"] = False
                state["timer_blink"] = True
                print("[TIMER] Isteklo vreme!")

        elif state["timer_blink"]:
            publish_display(0)
            time.sleep(0.5)

            mqtt_client.publish(
                "home/PI2/4sd",
                json.dumps({
                    "measurement": "iot_devices",
                    "device": "4SD",
                    "pi": "PI2",
                    "field": "display_time",
                    "value": "    "
                })
            )
            time.sleep(0.5)

        else:
            time.sleep(0.2)

def publisher_task(stop_event):
    global data_batch
    while not stop_event.is_set():
        time.sleep(mqtt_config.get("publish_interval", 5))
        with batch_lock:
            if data_batch:
                for item in data_batch:
                    mqtt_client.publish(item["topic"], json.dumps(item))
                data_batch = []

def run_pi2():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_config.get("broker", "localhost"), mqtt_config.get("port", 1883), 60)
    mqtt_client.loop_start()

    stop_event = threading.Event()

    # Pokretanje niti za štopericu
    threading.Thread(target=timer_thread, daemon=True).start()

    # Pokretanje publisher niti
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()

    # Start senzora
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY.get(cfg["type"])
        if not entry:
            continue
        
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]
        
        # Određivanje callback-a na osnovu tipa
        cb_type = "on_value" if cfg["type"] in ["ultrasonic", "gyro", "dht", "membrane"] else "on_state_change"

        threading.Thread(
            target=runner,
            kwargs={
                "sensor_code": code,
                "delay": cfg.get("delay", 2),
                "stop_event": stop_event,
                cb_type: lambda c, f, v, t=cfg["topic"], sim=cfg.get("simulated", True): on_event(c, f, v, t, sim),
                "settings": cfg
            },
            daemon=True
        ).start()

    # Start aktuatora
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY.get(cfg["type"])
        if not entry:
            continue
        
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]

        threading.Thread(
            target=runner,
            kwargs={
                "actuator_code": code,
                "stop_event": stop_event,
                "settings": cfg,
                "on_state_change": lambda c, s, v, t=cfg["topic"], sim=cfg.get("simulated", True): on_event(c, s, v, t, sim)
            },
            daemon=True
        ).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    run_pi2()