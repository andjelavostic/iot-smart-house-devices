import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

# settings
settings = load_settings_spec('PI1-settings-saver.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client()

BATCH_SIZE = mqtt_config.get("batch_size", 5)

# GLOBALNO STANJE SISTEMA
state = {
    "alarm_active": False,      # da li alarm trenutno svira
    "system_armed": False,      # da li je sistem aktiviran
    "people_count": 0,          # broj osoba u objektu
    "last_distances": [],       # posljednje distance (za ulazak/izlazak)
    "correct_pin": "1234",      # tačan PIN
    "ds1_trigger_time": None    # koliko dugo su vrata otvorena
}

batch_lock = threading.Lock()
data_batch = []

# MQTT CALLBACKS
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/commands/PI1/#")
    client.subscribe("home/PI2/alarm_trigger")

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    device_code = msg.topic.split('/')[-1].upper()

    # komande sa Web aplikacije
    if device_code == "ALARM":
        if payload["value"] == 0:
            deactivate_alarm()
            state["system_armed"] = False
        return

    # ako je komanda za aktuator
    if "actuators" in settings and device_code in settings["actuators"]:
        settings["actuators"][device_code]["state"] = bool(payload["value"])
        print(f"[MQTT COMMAND] {device_code} set to {payload['value']}")

    if msg.topic == "home/PI2/alarm_trigger":
        if payload.get("value"):
            activate_alarm()
        else:
            deactivate_alarm()

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_config.get("broker", "localhost"), mqtt_config.get("port", 1883), 60)
mqtt_client.loop_start()

# FUNKCIJE ZA ALARM
alarm_lock = threading.Lock()

def activate_alarm():
    with alarm_lock:
        if state["alarm_active"]:
            return
        state["alarm_active"] = True
        print("[ALARM] AKTIVIRAN")
        mqtt_client.publish("home/commands/PI1/DB", json.dumps({"value": 1}))
        mqtt_client.publish("home/pi1/alarm", json.dumps({
            "measurement": "alarm",
            "device": "DB",
            "pi": "PI1",
            "field": "state",
            "value": 1,
            "simulated": True
        }))

def deactivate_alarm():
    with alarm_lock:
        if not state["alarm_active"]:
            return
        state["alarm_active"] = False
        print("[ALARM] DEAKTIVIRAN")
        mqtt_client.publish("home/commands/PI1/DB", json.dumps({"value": 0}))
        mqtt_client.publish("home/pi1/alarm", json.dumps({
            "measurement": "alarm",
            "device": "DB",
            "pi": "PI1",
            "field": "state",
            "value": 0,
            "simulated": True
        }))

def arm_system():
    state["system_armed"] = True
    print("[SYSTEM] Sistem je AKTIVAN")

#logika
def process_logic(device_code, value):

    #PIR --> uključi svjetlo na 10 s
    if device_code == "DPIR1" and value:
        mqtt_client.publish("home/commands/PI1/DL", json.dumps({"value": 1}))
        threading.Timer(10, lambda:
            mqtt_client.publish("home/commands/PI1/DL", json.dumps({"value": 0}))
        ).start()

    #ulazak/izlazak (pir i ultrasonic)
    if device_code == "DUS1":
        state["last_distances"].append(value)
        if len(state["last_distances"]) > 5:
            state["last_distances"].pop(0)

    if device_code == "DPIR1" and value and len(state["last_distances"]) >= 3:

        first = state["last_distances"][0]
        last = state["last_distances"][-1]

        if last < first:
            state["people_count"] += 1
            print("[PEOPLE] ULazak")
        else:
            state["people_count"] = max(0, state["people_count"] - 1)
            print("[PEOPLE] IZlazak")

        mqtt_client.publish("home/pi1/people", json.dumps({
            "measurement": "people",
            "value": state["people_count"],
            "device": "SYSTEM",
            "pi": "PI1",
            "field": "count",
            "simulated": True
        }))

    #nema nikoga i pokret --> alarm
    if device_code == "DPIR1" and value:
        if state["people_count"] == 0 and state["system_armed"]:
            print("[ALARM] Pokret u praznom objektu!")
            activate_alarm()

    #ds1 5 sekundi --> alarm
    if device_code == "DS1":

        if value:
            state["ds1_trigger_time"] = time.time()
        else:
            state["ds1_trigger_time"] = None

        if state["ds1_trigger_time"]:
            if time.time() - state["ds1_trigger_time"] > 5:
                print("[ALARM] Vrata otvorena >5s")
                activate_alarm()

        # Ako je sistem aktivan i vrata se otvore → alarm
        if value and state["system_armed"]:
            activate_alarm()

    #pin logika
    if device_code == "DMS":

        print(f"[PIN] {value}")

        # Gasi alarm
        if state["alarm_active"] and value == state["correct_pin"]:
            deactivate_alarm()
            state["system_armed"] = False
            return

        # Aktivira sistem sa delay 10s
        if not state["system_armed"] and value == state["correct_pin"]:
            print("[SYSTEM] Aktivacija za 10 sekundi...")
            threading.Timer(10, arm_system).start()



#slanje podataka
def on_event(device_code, field, value, topic, is_simulated):

    payload = {
        "measurement": "iot_devices",
        "device": device_code,
        "pi": "PI1",
        "field": field,
        "value": value,
        "simulated": is_simulated,
        "topic": topic
    }

    with batch_lock:
        data_batch.append(payload)

    process_logic(device_code, value)


def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(mqtt_config.get("publish_interval", 5))

        with batch_lock:
            if data_batch:
                for item in data_batch:
                    target_topic = item.pop("topic")
                    mqtt_client.publish(target_topic, json.dumps(item))
                data_batch.clear()


def main():

    stop_event = threading.Event()

    # Publisher thread
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()

    # Pokretanje senzora
    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY.get(cfg["type"])
        #runner = entry["sim"]
        is_simulated = cfg.get("simulated", True)
        runner = entry["sim"] if is_simulated else entry["true"]
        
        threading.Thread(
            target=runner,
            kwargs={
                "sensor_code": code,
                "delay": cfg.get("delay", 2),
                "stop_event": stop_event,
                "on_value" if cfg["type"] in ["ultrasonic", "membrane"] else "on_state_change":
                    lambda c, f, v, t=cfg["topic"], sim=cfg["simulated"]:
                        on_event(c, f, v, t, sim),
                "settings": cfg
            },
            daemon=True
        ).start()

    # Pokretanje aktuatora
    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY.get(cfg["type"])
        #runner = entry["sim"]
        is_simulated = cfg.get("simulated", True)
        runner = entry["sim"] if is_simulated else entry["true"]

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
