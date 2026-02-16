# sensors/gyroscope.py
import os
import sys
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from MPU6050 import MPU6050
except ImportError as e:
    print(f"Greška pri uvozu MPU6050: {e}")
    MPU6050 = None

def run_gyro_real(sensor_code, delay, stop_event, on_value, settings):

    if MPU6050 is None:
        print("Greška: MPU6050 biblioteka nije instalirana.")
        return

    mpu = MPU6050(1, 0x68, 0, 0, 0, 0, 0, 0, False) 
    print(f"Pokrenuto čitanje sa PRAVOG žiroskopa [{sensor_code}]")

    try:
        while not stop_event.is_set():
            accel = mpu.get_acceleration()
            gyro = mpu.get_rotation()
            
            val = {
                "accel": [accel[0]/16384.0, accel[1]/16384.0, accel[2]/16384.0],
                "gyro": [gyro[0]/131.0, gyro[1]/131.0, gyro[2]/131.0]
            }
            
            # ovde prodljedjivanje podataka mainu
            on_value(sensor_code, settings, val)
            
            time.sleep(delay)
    except Exception as e:
        print(f"Greška u radu žiroskopa: {e}")