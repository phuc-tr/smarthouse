import time
import random
import os
from datetime import datetime
from typing import Dict, Any
import yaml
import paho.mqtt.client as mqtt

# ==========================
# ENV / CONFIG
# ==========================

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_CLIENT_ID = "smarthome-simulator"
CONFIG_PATH = os.getenv("SIM_CONFIG", "config.yaml")

# ==========================
# LOAD YAML CONFIG
# ==========================

with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

SIMULATION_INTERVAL_SECONDS = CONFIG["simulation"]["interval_seconds"]
PROFILES = CONFIG["profiles"]
ROOMS = CONFIG["rooms"]

# ==========================
# UTILS
# ==========================

def now():
    return datetime.now()

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ==========================
# BASELINE FROM CONFIG
# ==========================

def get_baseline(profile_name: str, sensor_type: str, t: datetime) -> float:
    """
    Get baseline value from config based on profile, sensor type, and current hour.
    Returns the value from the first matching interval, or default if no match.
    """
    if profile_name not in PROFILES:
        return 20.0
    
    profile = PROFILES[profile_name]
    
    if sensor_type not in profile:
        return 20.0
    
    sensor_config = profile[sensor_type]
    default_value = sensor_config.get("default", 20.0)
    intervals = sensor_config.get("intervals", [])
    
    current_hour = t.hour
    
    for interval in intervals:
        start_hour, end_hour, value = interval
        if start_hour <= current_hour < end_hour:
            return float(value)
    
    return float(default_value)

def get_probability(profile_name: str, sensor_type: str) -> float:
    """
    Get base probability from config for window or smoke sensors.
    Returns value between 0.0 and 1.0.
    """
    if profile_name not in PROFILES:
        return 0.1  # Default 10%
    
    profile = PROFILES[profile_name]
    
    if sensor_type not in profile:
        return 0.1
    
    sensor_config = profile[sensor_type]
    return float(sensor_config.get("base_probability", 0.1))

# ==========================
# TEMPERATURE
# ==========================

def simulate_temperature(profile: str, sensor_id: int, t: datetime) -> float:
    baseline = get_baseline(profile, "temperature", t)
    bias = (sensor_id - 1) * 0.2
    noise = random.gauss(0, 0.4)
    return round(clamp(baseline + noise + bias, 16, 30), 1)

# ==========================
# HUMIDITY
# ==========================

def simulate_humidity(profile: str, sensor_id: int, t: datetime) -> float:
    baseline = get_baseline(profile, "humidity", t)
    bias = (sensor_id - 1) * 0.5
    noise = random.gauss(0, 3.5)
    return round(clamp(baseline + noise + bias, 25, 80), 1)

# ==========================
# WINDOW 
# ==========================

def simulate_window(profile: str, sensor_id: int) -> int:
    base_prob = get_probability(profile, "window")
    
    # Add small bias per sensor and noise
    bias = (sensor_id - 1) * 0.05
    noise = random.gauss(0, 0.1)
    
    # Calculate final probability (clamped between 0 and 1)
    final_prob = clamp(base_prob + bias + noise, 0.0, 1.0)
    
    return 1 if random.random() < final_prob else 0

# ==========================
# SMOKE 
# ==========================

def simulate_smoke(profile: str, sensor_id: int) -> int:
    base_prob = get_probability(profile, "smoke")
    
    
    # Add small bias per sensor and noise
    bias = (sensor_id - 1) * 0.02
    noise = random.gauss(0, 0.05)
    
    # Calculate final probability (clamped between 0 and 1)
    final_prob = clamp(base_prob + bias + noise, 0.0, 1.0)
    
    return 1 if random.random() < final_prob else 0

# ==========================
# MQTT
# ==========================

def publish(client, topic, value):
    client.publish(topic, str(value), qos=0, retain=False)

# ==========================
# MAIN
# ==========================

def main():
    client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )

    while True:
        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            print("Connected to MQTT broker.")
            break
        except Exception as e:
            print(f"MQTT error: {e}, retrying...")
            time.sleep(2)

    client.loop_start()
    print("Simulator started.")
    print(f"Loaded {len(PROFILES)} profiles: {list(PROFILES.keys())}")
    print(f"Loaded {len(ROOMS)} rooms")

    while True:
        t = now()

        for room in ROOMS:
            room_id = room["id"]
            profile = room["profile"]
            sensors = room["sensors"]

            for i in range(1, sensors.get("temperature", 0) + 1):
                value = simulate_temperature(profile, i, t)
                publish(client, f"home/{room_id}/temperature/{i}", value)

            for i in range(1, sensors.get("humidity", 0) + 1):
                value = simulate_humidity(profile, i, t)
                publish(client, f"home/{room_id}/humidity/{i}", value)

            for i in range(1, sensors.get("window", 0) + 1):
                value = simulate_window(profile, i)
                publish(client, f"home/{room_id}/window/{i}", value)

            for i in range(1, sensors.get("smoke", 0) + 1):
                value = simulate_smoke(profile, i)
                publish(client, f"home/{room_id}/smoke/{i}", value)

        time.sleep(SIMULATION_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()