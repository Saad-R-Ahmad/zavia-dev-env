# SparkplugB Simulator

A SparkplugB MQTT client simulator for testing and development.

## Running Locally

```bash
# Run directly with uv
uv run main.py
```

## Running with Docker

The simulator is included in the main Docker Compose configuration:

```bash
# Build and start the simulator
cd /home/saad/dev/uns_builder
docker compose -f docker-compose.dev.yml up -d spb-simulator

# View logs
docker compose -f docker-compose.dev.yml logs -f spb-simulator

# Stop the simulator
docker compose -f docker-compose.dev.yml stop spb-simulator
```

## Configuration

The following environment variables can be configured in `docker-compose.dev.yml`:

- `MQTT_BROKER` - MQTT broker hostname (default: localhost)
- `MQTT_PORT` - MQTT broker port (default: 11883)
- `MQTT_USERNAME` - MQTT username (default: admin)
- `MQTT_PASSWORD` - MQTT password (default: changeme)
- `SPB_GROUP_ID` - SparkplugB group ID (default: "Sparkplug B Devices")
- `SPB_NODE_NAME` - SparkplugB node name (default: "Python Edge Node 1")
- `SPB_DEVICE_NAME` - SparkplugB device name (default: "Emulated Device")
- `PUBLISH_PERIOD` - Data publish period in ms (default: 5000)

## Profiles

The simulator is included in the following Docker Compose profiles:
- `all` - All services
- `apps` - Application services
- `spb-simulator` - Just the simulator

Start specific profiles:
```bash
docker compose -f docker-compose.dev.yml --profile spb-simulator up -d
```
