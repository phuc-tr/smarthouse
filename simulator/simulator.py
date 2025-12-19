import time
import random
import os
from datetime import datetime
from typing import Dict, Tuple
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
ROOMS = CONFIG["rooms"]

# Window state per (room_id, sensor_id)
WINDOW_STATE: Dict[Tuple[str, int], Dict] = {}

# ==========================
# UTILS
# ==========================

def now():
    return datetime.now()

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ==========================
# TEMPERATURE
# ==========================

def get_temperature_baseline(profile: str, t: datetime) -> float:
    h = t.hour
    if profile == "bedroom":
        return 19 if h < 6 else 20 if h < 9 else 21 if h < 18 else 22 if h < 22 else 20
    if profile == "livingroom":
        return 20 if h < 6 else 21 if h < 9 else 22 if h < 18 else 23 if h < 23 else 21
    base = 20 if h < 6 else 21 if h < 18 else 22 if h < 23 else 21
    if (h == 12 and t.minute < 45) or (h == 19 and t.minute < 45):
        base += 3
    return base

def simulate_temperature(profile: str, sensor_id: int, t: datetime) -> float:
    bias = (sensor_id - 1) * 0.2
    noise = random.gauss(0, 0.4)
    return round(clamp(get_temperature_baseline(profile, t) + noise + bias, 16, 30), 1)

# ==========================
# HUMIDITY
# ==========================

def get_humidity_baseline(profile: str, t: datetime) -> float:
    h = t.hour
    if profile == "kitchen":
        base = 45 if h < 6 else 47 if h < 18 else 50
        if (h == 12 and t.minute < 45) or (h == 19 and t.minute < 45):
            base += 20
        return base
    return 47 if h < 6 else 43 if h < 18 else 46

def simulate_humidity(profile: str, sensor_id: int, t: datetime) -> float:
    bias = (sensor_id - 1) * 0.5
    noise = random.gauss(0, 3.5)
    return round(clamp(get_humidity_baseline(profile, t) + noise + bias, 25, 80), 1)

# ==========================
# WINDOW
# ==========================

def simulate_window(room_id: str, sensor_id: int, profile: str, t: datetime) -> int:
    key = (room_id, sensor_id)
    if key not in WINDOW_STATE:
        WINDOW_STATE[key] = {"open": False, "minutes": 0}

    state = WINDOW_STATE[key]
    h = t.hour

    if state["open"]:
        state["minutes"] -= 1
        if state["minutes"] <= 0:
            state["open"] = False
    else:
        prob = 0.02 if profile == "livingroom" and 10 <= h < 18 else 0.005
        if random.random() < prob:
            state["open"] = True
            state["minutes"] = random.randint(10, 30)

    return 1 if state["open"] else 0

# ==========================
# SMOKE
# ==========================

def simulate_smoke(profile: str, t: datetime) -> int:
    if profile != "kitchen":
        return 0
    if (t.hour == 12 and 20 <= t.minute < 23) or (t.hour == 19 and 10 <= t.minute < 13):
        return 1
    return 0

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
        callback_api_version=1
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

    while True:
        t = now()

        for room in ROOMS:
            room_id = room["id"]
            profile = room["profile"]
            sensors = room["sensors"]

            for i in range(1, sensors.get("temperature", 0) + 1):
                publish(client, f"home/{room_id}/temperature/{i}",
                        simulate_temperature(profile, i, t))

            for i in range(1, sensors.get("humidity", 0) + 1):
                publish(client, f"home/{room_id}/humidity/{i}",
                        simulate_humidity(profile, i, t))

            for i in range(1, sensors.get("window", 0) + 1):
                publish(client, f"home/{room_id}/window/{i}",
                        simulate_window(room_id, i, profile, t))

            for i in range(1, sensors.get("smoke", 0) + 1):
                publish(client, f"home/{room_id}/smoke/{i}",
                        simulate_smoke(profile, t))

        time.sleep(SIMULATION_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
