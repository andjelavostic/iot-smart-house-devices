import threading
import time
from settings import load_settings

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass


if __name__ == "__main__":
    print('Starting app')
    settings = load_settings()
    threads = []
    stop_event = threading.Event()
    try:
        ds1_settings = settings['DS1']
        dl_settings = settings['DL']
        dus1_settings = settings['DUS1']
        db_settings = settings['DB']
        dpir1_settings = settings['DPIR1']
        dms_settings = settings['DMS']
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print('Stopping app')
        for t in threads:
            stop_event.set()
