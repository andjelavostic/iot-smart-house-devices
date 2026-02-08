# sensors/gyroscope.py
import time
from MPU6050 import MPU6050  

def run_gyro_real(sensor_code, delay, on_value, stop_event, settings):
    # Inicijalizacija MPU6050 objekta
    mpu = MPU6050(1, 0x68, 0, 0, 0, 0, 0, 0, False) 
    
    print(f"Pokrenuto čitanje sa PRAVOG žiroskopa [{sensor_code}]")

    while not stop_event.is_set():
        accel = mpu.get_acceleration()
        gyro = mpu.get_rotation()
        
        val = {
            "accel": [accel[0]/16384.0, accel[1]/16384.0, accel[2]/16384.0],
            "gyro": [gyro[0]/131.0, gyro[1]/131.0, gyro[2]/131.0]
        }
        
        on_value(sensor_code, settings, val)
        
        time.sleep(delay)