FROM python:3.13-slim

WORKDIR /app

COPY simulator.py /app/simulator.py
COPY config.yaml /app/config.yaml

RUN pip install paho-mqtt pyyaml

ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER_HOST=mosquitto
ENV MQTT_BROKER_PORT=1883

CMD ["python", "simulator.py"]
