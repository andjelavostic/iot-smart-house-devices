import math
import time
import random

def generate_distance_realistic(delay=0.1, min_dist=50, max_dist=200, frequency=0.05, max_speed=3):
    """
    Realistična simulacija senzora.
    - min_dist, max_dist: opseg udaljenosti
    - frequency: Hz, brzina oscilacije cilja
    - max_speed: maksimalna promena po step-u (jedinica: isti kao udaljenost)
    - delay: sekunde između merenja
    """
    amplitude = (max_dist - min_dist) / 2
    offset = min_dist + amplitude
    start_time = time.time()
    
    current_distance = offset  # start na sredini

    while True:
        t = time.time() - start_time
        # Ciljna vrednost po sinusoidu
        target_distance = offset + amplitude * math.sin(2 * math.pi * frequency * t)
        
        # Realistična promena: ne preskačemo previše po step-u
        diff = target_distance - current_distance
        if abs(diff) > max_speed:
            diff = max_speed if diff > 0 else -max_speed

        # Dodajemo malu slučajnu fluktuaciju
        noise = random.uniform(-0.3, 0.3)
        
        current_distance += diff + noise
        current_distance = max(min_dist, min(max_dist, current_distance))  # ograniči opseg

        yield float(round(current_distance, 2))
        time.sleep(delay)
def ultrasonic_sim(sensor_code, delay, on_value, stop_event, settings=None):
    """
    Simulacija ultrazvučnog senzora.
    Poziva callback svaki put kada se udaljenost promeni.
    """
    initial = settings.get("distance") if settings else None

    for distance in generate_distance_realistic(delay):
        if stop_event.is_set():
            break

        if settings is not None:
            settings["distance"] = distance  # ažurira settings

        if on_value:
            on_value(sensor_code, settings, distance)

        print(f"[{sensor_code}] Distance: {distance} cm")
