from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import threading
import time
import random
import json # Import json to read the config file

app = Flask(__name__)

# Dictionary to hold the latest MQTT data. Keys are the full topic strings.
mqtt_data = {}

# Store the start time for Uptime calculation (used if no MQTT uptime topic is available or valid)
start_time = time.time()

# Global variable for configuration
CONFIG = {}

# Map meter index to the respective L-phase topics
METER_TOPIC_MAP = {
    0: {"V": "Smartmeter/SpannungL1", "A": "Smartmeter/StromL1"}, # L1
    1: {"V": "Smartmeter/SpannungL2", "A": "Smartmeter/StromL2"}, # L2
    2: {"V": "Smartmeter/SpannungL3", "A": "Smartmeter/StromL3"}  # L3
}

# --- Configuration Loader ---

def load_config():
    """Loads MQTT configuration from config.json."""
    global CONFIG
    try:
        with open('config.json', 'r') as f:
            CONFIG = json.load(f)
        print("Configuration loaded successfully from config.json.")
    except FileNotFoundError:
        print("Error: config.json not found. Please create it.")
        # Exit the application if config file is missing
        exit(1) 
    except json.JSONDecodeError:
        print("Error: config.json is invalid JSON.")
        # Exit the application if config file is invalid
        exit(1)

# --- MQTT Setup and Handlers ---

def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the MQTT broker."""
    if rc == 0:
        print("Connected successfully to MQTT Broker.")
        
        # Comprehensive list of all topics provided by the user
        topics = [
            "Smartmeter/Wirkleistunggesamt", "Smartmeter/WirkleistungBezug", "Smartmeter/WirkleistungLieferung",
            "Smartmeter/WirkenergieBezug", "Smartmeter/WirkenergieLieferung",
            "Smartmeter/SpannungL1", "Smartmeter/StromL1",
            "Smartmeter/SpannungL2", "Smartmeter/StromL2",
            "Smartmeter/SpannungL3", "Smartmeter/StromL3",
            "Smartmeter/Leistungsfaktor",
            "Smartmeter/uptime"
        ]
        
        for topic in topics:
            client.subscribe(topic)
            print(f"Subscribed to: {topic}")
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback function for when a message is received from the MQTT broker."""
    try:
        # Decode and store the payload
        mqtt_data[msg.topic] = msg.payload.decode()
    except Exception as e:
        print(f"Error processing MQTT message on topic {msg.topic}: {e}")

def mqtt_thread():
    """Initializes and runs the MQTT client loop using parameters from CONFIG."""
    
    # 1. Retrieve configuration parameters
    mqtt_config = CONFIG.get("mqtt", {})
    host = mqtt_config.get("broker_host")
    port = mqtt_config.get("broker_port")
    user = mqtt_config.get("username")
    pwd = mqtt_config.get("password")

    if not host or not port:
        print("Error: MQTT configuration (broker_host/broker_port) is missing or invalid in config.json.")
        return

    # 2. Setup client with config details
    client = mqtt.Client()
    if user and pwd:
        client.username_pw_set(user, pwd)
        
    client.on_connect = on_connect
    client.on_message = on_message
    
    connected = False
    retry_delay = 1
    max_retry_delay = 32

    # 3. Connection loop
    while not connected:
        try:
            print(f"Attempting to connect to MQTT broker at {host}:{port}...")
            client.connect(host, port, 60)
            connected = True
            client.loop_forever() # Blocks until disconnected
        except Exception as e:
            print(f"MQTT connection failed: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_retry_delay)

# --- Helper Functions (No changes here, as they use global mqtt_data) ---

def safe_float(topic_key, default_value=0.0):
    """Safely retrieves and converts MQTT data to a float, handling potential errors."""
    try:
        data = mqtt_data.get(topic_key)
        if data is None:
            return default_value
        return float(data)
    except ValueError:
        if topic_key != "Smartmeter/uptime":
            print(f"Warning: Could not convert data for {topic_key} to float. Using default {default_value}.")
        return default_value

def get_meter_data(meter_index):
    """
    Constructs a Shelly-like meter object for a given index (0, 1, or 2),
    using the correct L-phase data.
    """
    
    topic_v = METER_TOPIC_MAP[meter_index]["V"]
    topic_a = METER_TOPIC_MAP[meter_index]["A"]

    voltage = safe_float(topic_v, 230)
    current = safe_float(topic_a, 0)
    
    total_consumed_kwh = safe_float("Smartmeter/WirkenergieBezug", 0)
    total_returned_kwh = safe_float("Smartmeter/WirkenergieLieferung", 0)
    
    total_power_sum = safe_float("Smartmeter/Wirkleistunggesamt", 0)
    phase_power = total_power_sum / 3 if total_power_sum else 0 
    
    power_factor = safe_float("Smartmeter/Leistungsfaktor", 100) / 100 # Convert % to decimal
    
    return {
        "power": round(phase_power, 2), 
        "total": round(total_consumed_kwh, 2), 
        "total_returned": round(total_returned_kwh, 2), 
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "is_valid": True,
        "id": meter_index,
        "pf": round(power_factor, 3)
    }

# --- Flask Endpoints (No changes here) ---

@app.route('/emeter/<int:meter_id>')
def emeter_id(meter_id):
    """
    Single emeter endpoint (e.g., /emeter/0, /emeter/1, /emeter/2).
    """
    if 0 <= meter_id <= 2:
        meter_data = get_meter_data(meter_id)
        return jsonify({k: v for k, v in meter_data.items() if k not in ["id", "is_valid"]})
    else:
        return jsonify({"is_valid": False, "msg": "Invalid meter ID"}), 404


@app.route('/status')
def status():
    """
    Comprehensive Shelly 3EM status endpoint.
    """
    
    emeter_0 = get_meter_data(0)
    emeter_1 = get_meter_data(1)
    emeter_2 = get_meter_data(2)
    
    total_power_sum = safe_float("Smartmeter/Wirkleistunggesamt", 0)
    
    uptime_sec = int(time.time() - start_time) 
    uptime_topic_data = mqtt_data.get("Smartmeter/uptime")
    if uptime_topic_data:
        try:
            uptime_sec = int(float(uptime_topic_data))
        except ValueError:
            pass
        
    current_time_str = time.strftime("%H:%M", time.localtime())

    return jsonify({
        "wifi_sta": {
            "connected": True,
            "ip": "192.168.25.99",
            "rssi": random.randint(-60, -40),
            "ssid": "VirtualShellyNet"
        },
        "cloud": {
            "enabled": False,
            "connected": False
        },
        "mqtt": {
            "connected": True
        },
        "time": current_time_str,
        "uptime": int(uptime_sec),
        "ram_free": random.randint(30000, 40000), 
        "fs_free": 100000,
        "device": {
            "type": "SH3EM",
            "mac": "AA:BB:CC:DD:EE:FF",
            "model": "SHEM-3",
            "fw_id": "20240105-103323/v1.0.0@915b2257"
        },
        "emeters": [
            emeter_0,
            emeter_1,
            emeter_2
        ],
        "total_power": round(total_power_sum, 2), 
        "input": [{"state":0, "id":0}],
        "relay": [{"ison":False, "has_timer":False, "id":0}]
    })

if __name__ == '__main__':
    load_config() # Load configuration first
    print("Starting Virtual Shelly 3EM Emulator (Fully Mapped)...")
    # Start MQTT thread after config is loaded
    threading.Thread(target=mqtt_thread, daemon=True).start() 
    app.run(host='0.0.0.0', port=80, debug=False)
