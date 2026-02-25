from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*",async_mode="threading")

# INFLUXDB SETUP
#Andjela, ne brisi moj token samo zakomentarisi
#token = "Mr_rBWmLoa9EXenHySzkHOW6tN-bi0iJ_b-SD1wxhZSs37pqdnW8hDZW8f3XKYJ-TMHf2gRYDuPhsfZDhBresA=="
#token="6HCU2B_untoFWt_nrCyPtU863ltIn2EAg-bzScRONbTawqQzYO62tG6QMdxdrSfkTCDiYAoWVMenZB5HR_Yvaw=="
token="wXZ_NwOVI4Zkj-rv-fv92t7DqNG-p6EH7hhkHtmT1PFpOhNdEaJItARNVFaAxI7Qn2cAPc4KmBZpZe34dbIvoA=="
org = "smart house"
bucket = "iot_bucket"
client = InfluxDBClient(url="http://localhost:8086", token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# MQTT
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())

        measurement = str(data.get("measurement", "iot_devices"))
        device = data.get("device")  # može biti None za system events
        pi = str(data.get("pi", "PI1"))
        field = str(data.get("field", "value"))
        value = data.get("value")

        # ako je dict ili list, pretvori u string
        if isinstance(value, (dict, list)):
            value_to_write = json.dumps(value)
        else:
            value_to_write = value

        # upis u Influx samo ako imamo device (izuzev system events)
        if device is not None and isinstance(value_to_write, (int, float, bool, str)):
            point = Point(measurement) \
                .tag("device", device) \
                .tag("pi", pi) \
                .field(field, value_to_write)

            write_api.write(bucket=bucket, org=org, record=point)

        # Emituj sve podatke na web frontend
        socketio.emit('device_update', data)

    except Exception as e:
        print(f"Greška: {e}")

mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2)
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)
mqtt_client.subscribe("home/#")
mqtt_client.loop_start()

# ROUTES
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.json

    pi = data.get("pi") 
    device = data.get("device")
    value = data.get("value")
    color = data.get("color")

    topic = f"home/commands/{pi}/{device}"

    payload = {"value": value}
    if color:
        payload["color"] = color

    print("Publishing to:", topic)
    print("Payload:", payload)

    mqtt_client.publish(topic, json.dumps(payload))

    return jsonify({"status": "sent"})

@socketio.on("command")
def handle_command(data):
    print("Primljena komanda:", data)

    topic = f"home/commands/{data['pi']}/{data['device']}"

    payload = {
        "value": data.get("value")
    }

    if "color" in data:
        payload["color"] = data["color"]

    mqtt_client.publish(topic, json.dumps(payload))

# web kontrola alarma
@app.route('/api/alarm', methods=['POST'])
def control_alarm():
    data = request.json
    mqtt_client.publish(
        "home/commands/PI1/ALARM",
        json.dumps({"value": data['value']})
    )
    return jsonify({"status": "ok"})

@app.route('/charts')
def charts_page():
    return render_template('charts.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
