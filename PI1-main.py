import threading
import time
import json
import paho.mqtt.client as mqtt
from settings import load_settings_spec
from registry import ACTUATOR_REGISTRY, SENSOR_REGISTRY

# --- SETTINGS ---
settings = load_settings_spec('PI1-settings.json')
mqtt_config = settings.get("mqtt", {})
mqtt_client = mqtt.Client()
BATCH_SIZE = mqtt_config.get("batch_size", 5)

# --- GLOBAL STATE ---
state = {
    "alarm_active": False,
    "alarm_reason": None,  # Može biti: "door_stuck", "intrusion", "motion"
    "system_armed": False,
    "people_count": 0,
    "last_distances": [],
    "correct_pin": "1234",
    "ds1_trigger_time": None,
    "ds2_trigger_time": None,
    "pin_buffer": ""
}

batch_lock = threading.Lock()
data_batch = []
alarm_lock = threading.Lock()

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    client.subscribe("home/commands/PI1/#")
    client.subscribe("home/PI2/person_event")
    client.subscribe("home/PI2/door_event")
    client.subscribe("home/PI2/gsg_event")
    client.subscribe("home/PI2/motion_event")
    client.subscribe("home/PI3/motion_event")

def on_message(client, userdata, msg):
    global state
    payload = json.loads(msg.payload.decode())
    topic = msg.topic
    device_code = topic.split('/')[-1].upper()

    # --- PERSON EVENT FROM PI2 ---
    if msg.topic == "home/PI2/person_event":
        direction = payload.get("direction")

        if direction == "enter":
            state["people_count"] += 1
        elif direction == "exit":
            state["people_count"] = max(0, state["people_count"] - 1)

        print(f"[PEOPLE] Trenutno u objektu: {state['people_count']}")
        return
    # --- DOOR EVENT FROM PI2 ---
    if msg.topic == "home/PI2/door_event":
        event = payload.get("event")

        if event == "door_open":
            if state["system_armed"]:
                activate_alarm("intrusion","PI2")

        elif event == "door_stuck_pi2":
            activate_alarm("door_stuck_pi2","PI2")

        elif event == "door_closed":
            if state["alarm_reason"] == "door_stuck_pi2":
                deactivate_alarm("DS2 vrata zatvorena","PI2")
        return
    # --- GSG EVENT ---
    if msg.topic == "home/PI2/gsg_event":
        activate_alarm("gsg","PI2")
        return
    # --- MOTION FROM PI2 ---
    if msg.topic == "home/PI2/motion_event":
        if state["people_count"] == 0:
            activate_alarm("motion","PI2")
        return
    # --- MOTION FROM PI3 ---
    if msg.topic == "home/PI3/motion_event":
        if state["people_count"] == 0:
            activate_alarm("motion","PI3")
        return
    #Aktuatori
    if device_code in settings.get("actuators", {}):
        settings["actuators"][device_code]["state"] = bool(payload.get("value", False))

# --- ALARM FUNCTIONS ---
def activate_alarm(reason,device):
    with alarm_lock:
        current_reason = state.get("alarm_reason")
        if current_reason in ["intrusion", "motion"] and (reason == "door_stuck" or reason=="door_stuck_pi2"):
            return
            
        state["alarm_reason"] = reason
        if state["alarm_active"]:
            return
            
        state["alarm_active"] = True
        print(f"[ALARM] AKTIVIRAN (Razlog: {reason}, uredjaj {device})")
        mqtt_client.publish("home/commands/PI1/DB", json.dumps({"value": 1}))
        mqtt_client.publish("home/pi1/alarm", json.dumps({
            "measurement": "alarm", "device": "DB", "pi": "PI1", "field": "state", "value": 1, "simulated": True
        }))

def deactivate_alarm(reason,device):
    with alarm_lock:
        if not state["alarm_active"]:
            return
        state["alarm_active"] = False
        state["alarm_reason"] = None
        print(f"[ALARM] DEAKTIVIRAN (Razlog: {reason}, uredjaj {device})")
        mqtt_client.publish("home/commands/PI1/DB", json.dumps({"value": 0}))
        mqtt_client.publish("home/pi1/alarm", json.dumps({
            "measurement": "alarm", "device": "DB", "pi": "PI1", "field": "state", "value": 0, "simulated": True
        }))

def arm_system():
    state["system_armed"] = True
    print("[SYSTEM] Sistem je AKTIVAN")

# --- LOGIC ---
def process_logic(device_code, value):
    # 1. PIN LOGIKA (DMS) - On je "Master" i gasi sve
    if device_code == "DMS":
        entered_pin = ""
        if len(str(value)) == 1:
            state["pin_buffer"] += str(value)
            print(f"[DMS] Trenutni unos: {state['pin_buffer']}")
            
            # tek kada skupimo 4 karaktera, postavljamo entered_pin za provjeru
            if len(state["pin_buffer"]) == 4:
                entered_pin = state["pin_buffer"]
                state["pin_buffer"] = "" # reset bafer za sledeći put
        else:
            # ako je simulacija, ona šalje cijelo kod odjednom
            entered_pin = value
        if entered_pin:
            if entered_pin == state["correct_pin"]:
                # Ako je alarm aktivan ILI je sistem samo naoružan
                if state["alarm_active"] or state["system_armed"]:
                    deactivate_alarm("PIN UNET","PI1") # Ovo briše state["alarm_reason"]
                    state["system_armed"] = False
                    print("[SYSTEM] Sve deaktivirano PIN-om.")
                else:
                    # Ako je sve bilo ugašeno, PIN naoružava sistem
                    print("[SYSTEM] Sistem će biti aktivan za 10s...")
                    threading.Timer(10, arm_system).start()

    # 2. VRATA (DS1)
    if device_code=="DS1":
        trigger_key = f"{device_code.lower()}_trigger_time"
        timer_key = f"{device_code.lower()}_timer"

        if value: # Vrata su OTVORENA
            state[trigger_key] = time.time()
            
            # Ako je sistem naoružan -> PROVALA (intrusion) - Odmah i visoki prioritet
            if state["system_armed"]:
                activate_alarm("intrusion","PI1")
            
            # Tajmer za "zaboravljena vrata" (>5s)
            def door_timer_check(d_code, trig_k):
                # Proveri da li su vrata još uvek otvorena
                if state.get(trig_k) is not None:
                    # Pali alarm samo kao "door_stuck" ako već nije "intrusion"
                    activate_alarm("door_stuck","PI1")
            
            # Otkaži stari tajmer ako postoji i pokreni novi
            if state.get(timer_key):
                state[timer_key].cancel()
            t = threading.Timer(5.0, door_timer_check, args=(device_code, trigger_key))
            state[timer_key] = t
            t.start()
        
        else: # Vrata su ZATVORENA
            state[trigger_key] = None
            if state.get(timer_key):
                state[timer_key].cancel()
                state[timer_key] = None
            
            # KLJUČNA PROMENA: 
            # Vrata gase alarm SAMO ako je razlog bio 'door_stuck'.
            # Ako je razlog 'motion' ili 'intrusion', zatvaranje vrata NE RADI NIŠTA.
            if state["alarm_active"] and state["alarm_reason"] == "door_stuck":
                print(f"[INFO] {device_code} zatvoren, razlog je bio door_stuck, gasim alarm.")
                deactivate_alarm("DS1 vrata zatvorena","PI1")
            else:
                print(f"[INFO] {device_code} zatvoren, ali alarm ostaje jer je razlog: {state['alarm_reason']}")

    # 3. PEOPLE COUNTING (DUS1 + DPIR1)
    if device_code == "DUS1":
        state["last_distances"].append(value)
        if len(state["last_distances"]) > 5:
            state["last_distances"].pop(0)
    if device_code == "DPIR1" and value and len(state["last_distances"]) >= 3:
        first, last = state["last_distances"][0], state["last_distances"][-1]
        if last < first:
            state["people_count"] += 1
        else:
            state["people_count"] = max(0, state["people_count"] - 1)
        mqtt_client.publish("home/PI1/people_count", json.dumps({
            "measurement": "people", "value": state["people_count"], "device": "SYSTEM", "pi": "PI1", "field": "count"
        }))

    # 4. POKRET U PRAZNOM OBJEKTU (DPIR1)
    if device_code == "DPIR1" and value:
        if state["people_count"] == 0:
            activate_alarm("motion","PI1")

    # 5. SVETLO (DPIR1)
    if device_code == "DPIR1" and value:
        mqtt_client.publish("home/commands/PI1/DL", json.dumps({"value": 1}))
        threading.Timer(10, lambda: mqtt_client.publish("home/commands/PI1/DL", json.dumps({"value": 0}))).start()

# --- EVENT HANDLER & MAIN (Ostaje isto kao u tvom kodu) ---
def on_event(device_code, field, value, topic, is_simulated):
    payload = {"measurement": "iot_devices", "device": device_code, "pi": "PI1", "field": field, "value": value, "simulated": is_simulated, "topic": topic}
    with batch_lock:
        data_batch.append(payload)
    process_logic(device_code, value)

def publisher_task(stop_event):
    while not stop_event.is_set():
        time.sleep(mqtt_config.get("publish_interval", 5))
        with batch_lock:
            if data_batch:
                batch_copy = data_batch[:]
                data_batch.clear()
                for item in batch_copy:
                    t = item.pop("topic")
                    mqtt_client.publish(t, json.dumps(item))

def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_config.get("broker", "localhost"), mqtt_config.get("port", 1883), 60)
    mqtt_client.loop_start()
    stop_event = threading.Event()
    threading.Thread(target=publisher_task, args=(stop_event,), daemon=True).start()

    for code, cfg in settings.get("sensors", {}).items():
        entry = SENSOR_REGISTRY.get(cfg["type"])
        if not entry:
            continue
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]
        cb_type = "on_value" if cfg["type"] in ["ultrasonic", "membrane"] else "on_state_change"
        threading.Thread(target=runner, kwargs={"sensor_code": code, "delay": cfg.get("delay", 2), "stop_event": stop_event, cb_type: (lambda c, f, v, t=cfg["topic"], sim=cfg.get("simulated", True): on_event(c, f, v, t, sim)), "settings": cfg}, daemon=True).start()

    for code, cfg in settings.get("actuators", {}).items():
        entry = ACTUATOR_REGISTRY.get(cfg["type"])
        if not entry:
            continue
        runner = entry["sim"] if cfg.get("simulated", True) else entry["true"]
        threading.Thread(target=runner, kwargs={"actuator_code": code, "stop_event": stop_event, "settings": cfg, "on_state_change": (lambda c, s, v, t=cfg["topic"]: on_event(c, "state", v, t, True))}, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()

if __name__ == "__main__":
    main()