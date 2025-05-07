import json
import sys
from config import OUTPUT_FILE

def find_timeouts(json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_file}'.")
        return []

    return [key for key, value in data.items() if value == "Timeout"]

if __name__ == "__main__":

    timeouts = find_timeouts(OUTPUT_FILE)
    print("Timeout entries:", timeouts)