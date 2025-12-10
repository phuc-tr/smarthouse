import time
import json
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

# Simulation interval in seconds (1 minute)
SIMULATION_INTERVAL_SECONDS = 60

# Room mapping: room_id -> logical room name + profile
ROOMS = {
    "room1": {"room": "kitchen", "profile": "kitchen"},
    "room2": {"room": "livingroom", "profile": "livingroom"},
    "room3": {"room": "bedroom", "profile": "bedroom"},
}

# We keep exactly 1 sensor per type per room for now
SENSORS = ["temperature", "humidity", "window", "smoke"]
SENSOR_ID = "1"  

# Window state per room (for open/close episodes)
WINDOW_STATE = {
    room_id: {"open": False, "minutes_left": 0}
    for room_id in ROOMS.keys()
}


# ==========================
# UTILS
# ==========================

def get_local_time() -> datetime:
    """
    Return current local time as datetime.
    We can use this for time-of-day patterns.
    """
    return datetime.now()


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


# ==========================
# TEMPERATURE SIMULATION
# ==========================

def get_temperature_baseline(profile: str, now: datetime) -> float:
    """
    Simple time-of-day dependent baseline temperature per room profile.
    """
    hour = now.hour

    if profile == "bedroom":
        if 0 <= hour < 6:
            return 19.0
        elif 6 <= hour < 9:
            return 20.0
        elif 9 <= hour < 18:
            return 21.0
        elif 18 <= hour < 22:
            return 22.0
        else:
            return 20.0

    elif profile == "livingroom":
        if 0 <= hour < 6:
            return 20.0
        elif 6 <= hour < 9:
            return 21.0
        elif 9 <= hour < 18:
            return 22.0
        elif 18 <= hour < 23:
            return 23.0
        else:
            return 21.0

    elif profile == "kitchen":
        if 0 <= hour < 6:
            base = 20.0
        elif 6 <= hour < 9:
            base = 21.0
        elif 9 <= hour < 18:
            base = 21.0
        elif 18 <= hour < 23:
            base = 22.0
        else:
            base = 21.0

        # Cooking events in kitchen: 12:00–12:45 and 19:00–19:45
        if (hour == 12 and 0 <= now.minute < 45) or (hour == 19 and 0 <= now.minute < 45):
            base += 3.0 

        return base

    # fallback
    return 21.0


def simulate_temperature(profile: str, now: datetime, humidity_value: float) -> Tuple[float, float, str]:
    """
    Simulate temperature (°C) for given profile and time.
    Also compute heat index based on temp and humidity.
    Returns: (temperature, heat_index, status)
    """
    baseline = get_temperature_baseline(profile, now)

    # Noise: bedroom < livingroom/kitchen
    if profile == "bedroom":
        noise = random.gauss(0, 0.3)
        temp_min, temp_max = 16.0, 26.0
    elif profile == "livingroom":
        noise = random.gauss(0, 0.5)
        temp_min, temp_max = 18.0, 28.0
    else:  # kitchen
        noise = random.gauss(0, 0.5)
        temp_min, temp_max = 18.0, 30.0

    temp = clamp(baseline + noise, temp_min, temp_max)
    temp = round(temp, 1)

    # Heat index calculation (simple approximation)
    heat_index = calculate_heat_index(temp, humidity_value)
    heat_index = round(heat_index, 1)

    # Status based on temperature
    if temp < 18.0:
        status = "too_cold"
    elif temp > 26.0:
        status = "too_hot"
    else:
        status = "normal"

    return temp, heat_index, status


def calculate_heat_index(temp_c: float, humidity: float) -> float:
    """
    Simple indoor Heat Index approximation based on temperature and humidity.
    """
    if temp_c < 24.0:
        return temp_c

    rh = clamp(humidity, 0.0, 100.0)
    extra = max(0.0, (rh - 40.0) / 10.0)  # every 10% above 40 adds ~1°C
    hi = temp_c + extra
    # Optional clamp so it doesn't explode
    hi = min(hi, temp_c + 6.0)
    return hi


# ==========================
# HUMIDITY SIMULATION
# ==========================

def get_humidity_baseline(profile: str, now: datetime) -> float:
    """
    Simple time-of-day baseline for humidity.
    """
    hour = now.hour

    if profile in ("bedroom", "livingroom"):
        if 0 <= hour < 6:
            return 47.0
        elif 6 <= hour < 18:
            return 43.0
        else:
            return 46.0

    elif profile == "kitchen":
        if 0 <= hour < 6:
            base = 45.0
        elif 6 <= hour < 18:
            base = 47.0
        else:
            base = 50.0

        # Cooking events: same as temperature
        if (hour == 12 and 0 <= now.minute < 45) or (hour == 19 and 0 <= now.minute < 45):
            base += 20.0  # bump humidity significantly

        return base

    return 45.0


def simulate_humidity(profile: str, now: datetime) -> Tuple[float, str]:
    """
    Simulate humidity (% RH) for given profile and time.
    Returns: (humidity, status)
    """
    baseline = get_humidity_baseline(profile, now)

    if profile in ("bedroom", "livingroom"):
        noise = random.gauss(0, 3.0)
        hum_min, hum_max = 25.0, 65.0
    else:  # kitchen
        noise = random.gauss(0, 4.0)
        hum_min, hum_max = 30.0, 80.0

    hum = clamp(baseline + noise, hum_min, hum_max)
    hum = round(hum, 1)

    if hum < 30.0:
        status = "too_dry"
    elif hum > 60.0:
        status = "too_humid"
    else:
        status = "normal"

    return hum, status


# ==========================
# WINDOW SIMULATION
# ==========================

def simulate_window(room_id: str, profile: str, now: datetime) -> str:
    """
    Simulate window open/close behavior per room, with episodes.
    Uses WINDOW_STATE[room_id] for stateful behavior.
    Returns: "OPEN" or "CLOSED"
    """
    state = WINDOW_STATE[room_id]
    hour = now.hour

    # If currently open, count down minutes_left
    if state["open"]:
        if state["minutes_left"] > 0:
            state["minutes_left"] -= 1
        if state["minutes_left"] <= 0:
            state["open"] = False

    else:
        # Currently closed → maybe start an "open" episode based on probability
        # Define probabilities higher around typical open-time windows

        open_prob = 0.0

        if profile == "bedroom":
            # Morning/evening airing
            if 7 <= hour < 9 or 20 <= hour < 21:
                open_prob = 0.03  # 3% chance per minute
            else:
                open_prob = 0.002  # small background chance

        elif profile == "livingroom":
            # Daytime more active
            if 10 <= hour < 18:
                open_prob = 0.02
            else:
                open_prob = 0.003

        elif profile == "kitchen":
            # Strong link to cooking hours
            if (hour == 12 and 0 <= now.minute < 60) or (hour == 19 and 0 <= now.minute < 60):
                open_prob = 0.05
            else:
                open_prob = 0.004

        if random.random() < open_prob:
            state["open"] = True
            state["minutes_left"] = random.randint(10, 30)  # open episode duration in minutes

    return "OPEN" if state["open"] else "CLOSED"


# ==========================
# SMOKE SIMULATION
# ==========================

def simulate_smoke(profile: str, now: datetime) -> int:
    """
    Simulate smoke detector.
    Kitchen: few hard-coded short alarm intervals.
    Other rooms: always 0 for simplicity.
    Returns: 0 (no alarm) or 1 (alarm).
    """
    if profile != "kitchen":
        return 0

    # Hardcoded smoke "events" during cooking times
    if now.hour == 12 and 20 <= now.minute < 23:
        return 1
    if now.hour == 19 and 10 <= now.minute < 13:
        return 1

    # Otherwise no alarm
    return 0


# ==========================
# MQTT PUBLISH
# ==========================

def publish_json(client: mqtt.Client, topic: str, payload: dict):
    msg = json.dumps(payload)
    client.publish(topic, msg, qos=0, retain=False)


# ==========================
# MAIN LOOP
# ==========================

def main():
    client = mqtt.Client(
    client_id=MQTT_CLIENT_ID,
    protocol=mqtt.MQTTv311,
    userdata=None,
    transport="tcp",
    callback_api_version=1
)

    # Retry connecting to MQTT broker until it succeeds
    while True:
        try:
            client.connect(
                MQTT_BROKER_HOST,
                int(MQTT_BROKER_PORT),
                keepalive=60
            )
            print("Connected to MQTT broker.")
            break
        except Exception as e:
            print(f"MQTT connection failed: {e}. Retrying in 2 seconds...")
            time.sleep(2)

    client.loop_start()

    print("Smart home simulator started. Publishing every",
          SIMULATION_INTERVAL_SECONDS, "seconds.")

    try:
        while True:
            now = get_local_time()
            iso_timestamp = now.isoformat()

            for room_id, info in ROOMS.items():
                room_name = info["room"]
                profile = info["profile"]

                # 1) Humidity first (needed to compute heat index for temperature)
                humidity_value, humidity_status = simulate_humidity(profile, now)
                humidity_payload = {
                    "timestamp": iso_timestamp,
                    "room_id": room_id,
                    "room": room_name,
                    "sensor": "humidity",
                    "sensor_id": SENSOR_ID,
                    "value": humidity_value,
                    "unit": "%",
                    "status": humidity_status,
                }
                humidity_topic = f"home/{room_id}/humidity/{SENSOR_ID}"
                publish_json(client, humidity_topic, humidity_payload)

                # 2) Temperature (+ Heat Index)
                temp_value, heat_index, temp_status = simulate_temperature(
                    profile, now, humidity_value
                )
                temp_payload = {
                    "timestamp": iso_timestamp,
                    "room_id": room_id,
                    "room": room_name,
                    "sensor": "temperature",
                    "sensor_id": SENSOR_ID,
                    "value": temp_value,
                    "heat_index": heat_index,
                    "unit": "C",
                    "status": temp_status,
                }
                temp_topic = f"home/{room_id}/temperature/{SENSOR_ID}"
                publish_json(client, temp_topic, temp_payload)

                # 3) Window
                window_state = simulate_window(room_id, profile, now)
                window_payload = {
                    "timestamp": iso_timestamp,
                    "room_id": room_id,
                    "room": room_name,
                    "sensor": "window",
                    "sensor_id": SENSOR_ID,
                    "state": window_state,
                }
                window_topic = f"home/{room_id}/window/{SENSOR_ID}"
                publish_json(client, window_topic, window_payload)

                # 4) Smoke
                smoke_alarm = simulate_smoke(profile, now)
                smoke_status = "alarm" if smoke_alarm == 1 else "normal"
                smoke_payload = {
                    "timestamp": iso_timestamp,
                    "room_id": room_id,
                    "room": room_name,
                    "sensor": "smoke",
                    "sensor_id": SENSOR_ID,
                    "alarm": smoke_alarm,
                    "status": smoke_status,
                }
                smoke_topic = f"home/{room_id}/smoke/{SENSOR_ID}"
                publish_json(client, smoke_topic, smoke_payload)

                # Optional: log to console for debugging
                print(f"[{iso_timestamp}] {room_name}: "
                      f"T={temp_value}°C (HI={heat_index}°C), "
                      f"H={humidity_value}%, "
                      f"W={window_state}, "
                      f"Smoke={smoke_alarm}")

            time.sleep(SIMULATION_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("Stopping simulator...")

    finally:
        client.loop_stop()
        client.disconnect()
        print("Simulator stopped.")


if __name__ == "__main__":
    main()
