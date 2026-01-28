import threading
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import json
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- KONFIGURACIJA ---
token=  "6HCU2B_untoFWt_nrCyPtU863ltIn2EAg-bzScRONbTawqQzYO62tG6QMdxdrSfkTCDiYAoWVMenZB5HR_Yvaw=="
org = "smart house"
url = "http://localhost:8086"
bucket = "iot_bucket"

mqtt_broker = "localhost"
mqtt_port = 1883

# Inicijalizacija InfluxDB klijenta
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

mqtt_client = mqtt.Client()
mqtt_connected = False

def on_connect(client, userdata, flags, rc):
    print(f"Server povezan na MQTT broker (code: {rc})")
    mqtt_connected = True
    client.subscribe("home/#") # Sluša sve senzore iz PI1-settings.json

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        
        # InfluxDB modelovanje sa tagovima za uređaj i simulaciju
        point = Point(data["measurement"]) \
            .tag("device", data["device"]) \
            .tag("pi", data["pi"]) \
            .tag("simulated", str(data["simulated"])) \
            .field(data["field"], data["value"]) 

        write_api.write(bucket=bucket, org=org, record=point)
        print(f"Upisano u InfluxDB: {data['device']} sa {data['pi']}")
        
    except Exception as e:
        print(f"Greška: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_forever()

# --- Flask REST API ---
@app.route("/")
def index():
    return "Server aktivan. Prima MQTT poruke i upisuje u InfluxDB."

@app.route("/status")
def status():
    return jsonify({
        "mqtt_connected": mqtt_connected,
        "bucket": bucket,
        "org": org
    })

# --- Pokretanje servera ---
if __name__ == "__main__":
    mqtt_thread = threading.Thread(target=start_mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    # Flask REST API
    app.run(host="0.0.0.0", port=5000, debug=True)