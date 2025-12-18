import time
import random

def generate_distance(delay, min_dist=2, max_dist=400, initial=None):
    """
    Generator koji simulira udaljenost koju meri ultrazvučni senzor.
    min_dist i max_dist u cm.
    """
    if initial is None:
        distance = random.randint(min_dist, max_dist)
    else:
        distance = initial

    while True:
        time.sleep(delay)
        new_distance = random.randint(min_dist, max_dist)
        if new_distance != distance:
            distance = new_distance
            yield distance
def ultrasonic_sim(sensor_code, delay, on_value, stop_event, settings=None):
    """
    Simulacija ultrazvučnog senzora.
    Poziva callback svaki put kada se udaljenost promeni.
    """
    initial = settings.get("distance") if settings else None

    for distance in generate_distance(delay, initial=initial):
        if stop_event.is_set():
            break

        if settings is not None:
            settings["distance"] = distance  # ažurira settings

        if on_value:
            on_value(sensor_code, settings, distance)

        print(f"[{sensor_code}] Distance: {distance} cm")
