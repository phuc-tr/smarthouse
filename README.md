# Smart Home
## About the Project

This project presents a Smart Home system that simulates how IoT devices communicate and operate together in a realistic home environment. The system demonstrates an end-to-end IoT architecture, starting from sensor data generation to storage, visualization, and real-time user notifications.

A configurable simulator generates data from multiple virtual sensors including temperature, humidity, window state, and smoke detectors across different rooms. The simulated devices publish their data using MQTT, which is then collected and stored in a time-series database. Grafana dashboards allow real-time monitoring and historical analysis of sensor values, while abnormal conditions such as smoke detection or unusual temperature values automatically trigger alerts sent to the homeowner via Telegram.

This project was developed for the **Software Engineering for Internet of Things (SE4IOT)** course, University of L’Aquila, Fall Semester 2025–2026.

## System Architecture

The Smart Home system is composed of multiple containerized services that work together to simulate, process, store, visualize, and react to sensor data.

A Python-based simulator represents smart home sensors deployed across different rooms. These sensors periodically generate measurements as and publish them to an MQTT broker using a structured topic hierarchy. The home is totally configurable, from the number of rooms and number of sensor devices in each room to sensor measurement periods. 

The MQTT broker (Mosquitto) acts as the central communication layer, distributing sensor messages to subscribed services. Telegraf subscribes to the MQTT topics and automatically ingests the sensor data, parsing metadata such as room and sensor identifiers directly from the topic structure. All measurements are stored in InfluxDB as time-series data.

Grafana connects to InfluxDB to provide interactive dashboards, enabling real-time monitoring and historical analysis of sensor values across rooms and sensor types.

In parallel, Node-RED listens to sensor data streams and applies application-level logic to detect abnormal conditions. When anomalies such as smoke detection or unusual temperature values occur, Node-RED triggers notifications that are sent to the homeowner via Telegram.

All components are orchestrated using Docker Compose, forming a complete end-to-end pipeline from sensor simulation to visualization and alerting.

## Built with

[![Python][Python.org]][Python-url][![Docker][Docker.com]][Docker-url][![MQTT][MQTT.com]][MQTT-url][![Telegraf][Telegraf.org]][Telegraf-url][![Grafana][Grafana.com]][Grafana-url][![InfluxDB][InfluxDB.com]][InfluxDB-url][![Nodered][Nodered.org]][Nodered-url][![Telegram][Telegram.org]][Telegram-url]


## Getting Started
### Prerequisites

Make sure the following software is installed on your machine:

- Docker
- Docker Compose

### Installation

Clone the repository:

```bash
git clone https://github.com/phuc-tr/smarthouse
cd smarthouse
```

Run the containers:

```bash
docker-compose up
```

Navigate to http://localhost:3000/, where you can see the dashboard. Use the following credentials: username=`admin`, password=`admin`.

To interact with InfluxDB, navigate to http://localhost:8086/. Use the following credentials: username=`admin`, password=`admin1234`.......... --- HERE Maybe briefly give instructions---

To open the Node-RED editor, navigate to http://localhost:1880/.

## Configuration

The configuration of the Smart Home system is mainly contained in the `docker-compose.yml` file. All services are deployed as Docker containers and connected through a dedicated bridge network.

Make sure that the following ports are available on your system:

- `1883` for the Mosquitto MQTT broker
- `8086` for InfluxDB
- `1880` for Node-RED
- `3000` for Grafana

### Telegram Notifications

...

## Developed by

- [Mete Harun Akcay](https://github.com/meteharun)
- [Than Phuc Tran](https://github.com/phuc-tr)
- [Pragati Manandhar](https://github.com/mdhrpragati)


<!-- Badge image definitions -->
[Docker.com]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white
[Python.org]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[MQTT.com]: https://img.shields.io/badge/MQTT-660066?style=for-the-badge&logo=eclipsemosquitto&logoColor=white
[Telegraf.org]: https://img.shields.io/badge/Telegraf-22ADF6?style=for-the-badge&logo=influxdb&logoColor=white
[InfluxDB.com]: https://img.shields.io/badge/InfluxDB-22ADF6?style=for-the-badge&logo=influxdb&logoColor=white
[Grafana.com]: https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white
[Nodered.org]: https://img.shields.io/badge/Node--RED-8F0000?style=for-the-badge&logo=nodered&logoColor=white
[Telegram.org]: https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white

<!-- Badge link definitions -->
[Docker-url]: https://www.docker.com/
[Python-url]: https://www.python.org/
[MQTT-url]: https://mqtt.org/
[Telegraf-url]: https://www.influxdata.com/time-series-platform/telegraf/
[InfluxDB-url]: https://www.influxdata.com/products/influxdb/
[Grafana-url]: https://grafana.com/
[Nodered-url]: https://nodered.org/
[Telegram-url]: https://telegram.org/

