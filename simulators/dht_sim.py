import time
import random


def generate_values(initial_temp=25, initial_humidity=20):
    temperature = initial_temp
    humidity = initial_humidity
    while True:
        temperature = temperature + random.randint(-1, 1)
        humidity = humidity + random.randint(-1, 1)
        if humidity < 0:
            humidity = 0
        if humidity > 100:
            humidity = 100
        yield humidity, temperature


# def dht_simulator(delay, callback, stop_event, publish_event, settings):
#     for h, t in generate_values():
#         time.sleep(delay)  
#         callback(h, t, publish_event, settings)
#         if stop_event.is_set():
#             break

def dht_simulator(sensor_code, delay, stop_event, on_value, settings): 
    for h, t in generate_values():
        if stop_event.is_set():
            break
        time.sleep(delay)
        val = {"temperature": t, "humidity": h}
        on_value(sensor_code, settings, val)