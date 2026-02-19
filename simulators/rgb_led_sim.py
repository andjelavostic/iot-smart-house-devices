import time

import time

def rgb_sim(actuator_code, stop_event, settings=None, on_state_change=None):
    """
    Simulacija RGB LED koja prati settings["color"].
    """
    print(f"[{actuator_code}] RGB SIMULATOR started. Waiting for commands...")
    
    # Pratimo poslednju boju da ne bismo spamovali konzolu istim ispisom
    last_color = [None, None, None]

    try:
        while not stop_event.is_set():
            # 1. Uzmi boju koju je tvoj Main (process_logic) upisao u settings
            current_color = settings.get("color", [0, 0, 0])
            
            # 2. Ako se boja promenila u odnosu na poslednju poznatu
            if current_color != last_color:
                print(f"\n[{actuator_code}] DISPLAY UPDATED: {current_color}")
                if current_color == [1, 0, 0]:
                    print(" >>> [ SJAJI CRVENO ] <<<")
                elif current_color == [0, 1, 0]:
                    print(" >>> [ SJAJI ZELENO ] <<<")
                elif current_color == [0, 0, 1]:
                    print(" >>> [ SJAJI PLAVO ] <<<")
                elif current_color == [0, 0, 0]:
                    print(" >>> [ ISKLJUČENO ] <<<")
                
                last_color = current_color
                
                # Javi Main-u da je simulator uspešno "prikazao" boju
                # Ovo šalje potvrdu Dashboardu
                if on_state_change:
                    on_state_change(actuator_code, settings, current_color)

            # Proveravaj promene svakih 100ms
            time.sleep(1)

    finally:
        print(f"[{actuator_code}] RGB SIMULATOR stopped")
