import json

def load_settings(filePath='PI1-settings.json'):
    with open(filePath, 'r') as f:
        return json.load(f)