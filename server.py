import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import json

# --- KONFIGURACIJA ---
token = "Mr_rBWmLoa9EXenHySzkHOW6tN-bi0iJ_b-SD1wxhZSs37pqdnW8hDZW8f3XKYJ-TMHf2gRYDuPhsfZDhBresA=="
org = "smart house"
url = "http://localhost:8086"
bucket = "iot_bucket"

mqtt_broker = "localhost"
mqtt_port = 1883

# Inicijalizacija InfluxDB klijenta
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

def on_connect(client, userdata, flags, rc):
    print(f"Server povezan na MQTT broker (code: {rc})")
    client.subscribe("home/#") # Sluša sve senzore iz PI1-settings.json

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        
        point = Point(data["measurement"]) \
            .tag("device", data["device"]) \
            .field(data["field"], data["value"]) 

        write_api.write(bucket=bucket, org=org, record=point)
        print(f"Upisano: {data['device']} -> {data['field']}: {data['value']}")
        
    except Exception as e:
        print(f"Greška pri upisu: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

print("Server pokrenut i čeka podatke...")
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_forever()