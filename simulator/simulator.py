import time
import random
from datetime import datetime
from typing import Tuple
import paho.mqtt.client as mqtt
import os

# ==========================
# CONFIG
# ==========================

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_CLIENT_ID = "smarthome-simulator"

SIMULATION_INTERVAL_SECONDS = 60

ROOMS = {
    "room1": {"room": "kitchen", "profile": "kitchen"},
    "room2": {"room": "livingroom", "profile": "livingroom"},
    "room3": {"room": "bedroom", "profile": "bedroom"},
}

SENSOR_ID = "1"

WINDOW_STATE = {
    room_id: {"open": False, "minutes_left": 0}
    for room_id in ROOMS.keys()
}

# ==========================
# UTILS
# ==========================

def get_local_time() -> datetime:
    return datetime.now()

def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))

# ==========================
# TEMPERATURE
# ==========================

def get_temperature_baseline(profile: str, now: datetime) -> float:
    hour = now.hour

    if profile == "bedroom":
        return 19.0 if hour < 6 else 20.0 if hour < 9 else 21.0 if hour < 18 else 22.0 if hour < 22 else 20.0
    if profile == "livingroom":
        return 20.0 if hour < 6 else 21.0 if hour < 9 else 22.0 if hour < 18 else 23.0 if hour < 23 else 21.0

    base = 20.0 if hour < 6 else 21.0 if hour < 18 else 22.0 if hour < 23 else 21.0
    if (hour == 12 and now.minute < 45) or (hour == 19 and now.minute < 45):
        base += 3.0
    return base

def simulate_temperature(profile: str, now: datetime) -> float:
    baseline = get_temperature_baseline(profile, now)
    noise = random.gauss(0, 0.4)
    return round(clamp(baseline + noise, 16.0, 30.0), 1)

# ==========================
# HUMIDITY
# ==========================

def get_humidity_baseline(profile: str, now: datetime) -> float:
    hour = now.hour

    if profile == "kitchen":
        base = 45.0 if hour < 6 else 47.0 if hour < 18 else 50.0
        if (hour == 12 and now.minute < 45) or (hour == 19 and now.minute < 45):
            base += 20.0
        return base

    return 47.0 if hour < 6 else 43.0 if hour < 18 else 46.0

def simulate_humidity(profile: str, now: datetime) -> float:
    noise = random.gauss(0, 3.5)
    return round(clamp(get_humidity_baseline(profile, now) + noise, 25.0, 80.0), 1)

# ==========================
# WINDOW
# ==========================

def simulate_window(room_id: str, profile: str, now: datetime) -> int:
    state = WINDOW_STATE[room_id]
    hour = now.hour

    if state["open"]:
        state["minutes_left"] -= 1
        if state["minutes_left"] <= 0:
            state["open"] = False
    else:
        prob = 0.02 if profile == "livingroom" and 10 <= hour < 18 else 0.005
        if random.random() < prob:
            state["open"] = True
            state["minutes_left"] = random.randint(10, 30)

    return 1 if state["open"] else 0

# ==========================
# SMOKE
# ==========================

def simulate_smoke(profile: str, now: datetime) -> int:
    if profile != "kitchen":
        return 0
    if (now.hour == 12 and 20 <= now.minute < 23) or (now.hour == 19 and 10 <= now.minute < 13):
        return 1
    return 0

# ==========================
# MQTT
# ==========================

def publish_value(client: mqtt.Client, topic: str, value):
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
            print(f"MQTT connection failed: {e}, retrying...")
            time.sleep(2)

    client.loop_start()
    print("Smart home simulator started.")

    while True:
        now = get_local_time()

        for room_id, info in ROOMS.items():
            profile = info["profile"]

            temp = simulate_temperature(profile, now)
            hum = simulate_humidity(profile, now)
            window = simulate_window(room_id, profile, now)
            smoke = simulate_smoke(profile, now)

            publish_value(client, f"home/{room_id}/temperature/{SENSOR_ID}", temp)
            publish_value(client, f"home/{room_id}/humidity/{SENSOR_ID}", hum)
            publish_value(client, f"home/{room_id}/window/{SENSOR_ID}", window)
            publish_value(client, f"home/{room_id}/smoke/{SENSOR_ID}", smoke)

            print(f"{room_id}: T={temp} H={hum} W={window} S={smoke}")

        time.sleep(SIMULATION_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()