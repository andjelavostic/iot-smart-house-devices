import json
import sys

def load_settings():
    
    file_name = 'PI1-settings.json'
    if len(sys.argv) > 1:
        file_name = f"{sys.argv[1]}-settings.json"
        
    with open(file_name, 'r') as f:
        return json.load(f)