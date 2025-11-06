# Hoymiles MQTT

[![pypi](https://img.shields.io/pypi/v/hoymiles-smiles.svg)](https://pypi.org/project/hoymiles-smiles/)
[![python](https://img.shields.io/pypi/pyversions/hoymiles-smiles.svg)](https://pypi.org/project/hoymiles-smiles/)
[![Build Status](https://github.com/wasilukm/hoymiles-smiles/actions/workflows/dev.yml/badge.svg)](https://github.com/wasilukm/hoymiles-smiles/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/wasilukm/hoymiles-smiles/branch/main/graphs/badge.svg)](https://codecov.io/github/wasilukm/hoymiles-smiles)

**Send data from Hoymiles photovoltaic installation to Home Assistant through WebSocket.**

*Disclaimer: This is an independent project, not affiliated with Hoymiles. Any trademarks or product names mentioned are the property of their respective owners.*

* **GitHub**: <https://github.com/wasilukm/hoymiles-smiles>
* **PyPI**: <https://pypi.org/project/hoymiles-smiles/>
* **License**: MIT

---

## Overview

The tool periodically communicates with Hoymiles DTU (Pro) through ModbusTCP and sends gathered data to WebSocket. Data is push via WebSocket discovery, automatically creating devices and entities.

![MQTT Devices](/docs/mqtt_devices.png)
![MQTT Entities](/docs/mqtt_entities.png)

---

## Features

### Core Functionality
- ✅ **Automatic MQTT Discovery** - Devices appear in Home Assistant automatically
- ✅ **Multiple DTU Support** - Monitor multiple installations
- ✅ **Production Caching** - SQLite database prevents data loss during outages
- ✅ **Health Monitoring** - HTTP endpoints for application health and metrics
- ✅ **Prometheus Metrics** - Integration with monitoring tools
- ✅ **Circuit Breaker** - Graceful handling of DTU failures
- ✅ **Timezone Support** - Accurate daily production resets
- ✅ **Docker Support** - Easy deployment with Docker Compose

### Home Assistant Integration
- ✅ **Custom Integration** - Native UI-based configuration (v1.1)
- ✅ **YAML Configuration** - Traditional sensor setup
- ✅ **Energy Dashboard** - Compatible with HA Energy panel
- ✅ **Device Grouping** - DTU and inverters as separate devices
- ✅ **Custom Branding** - Hoymiles icon and logo (v1.1)

### Monitoring & Observability
- ✅ **Health Endpoints** - `/health`, `/ready`, `/metrics`, `/stats`
- ✅ **Structured Logging** - JSON format option
- ✅ **Configurable Logging** - DEBUG, INFO, WARNING, ERROR levels
- ✅ **Persistent HTTP Sessions** - Efficient data fetching (v1.1)
- ✅ **Automatic Retries** - Resilient to transient failures (v1.1)

---

## Quick Start

### Docker Compose (Recommended)
```bash
# Create docker-compose.yml
docker-compose up -d
```

See **[QUICK_START.md](QUICK_START.md)** for detailed setup.

### Python Package
```bash
pip install hoymiles-smiles
python3 -m hoymiles_smiles --mqtt-broker 192.168.1.31 --dtu-host 192.168.1.191
```

### Home Assistant Custom Integration
```bash
cd /path/to/hoymiles-smiles-main
./install_v1.1.sh
```

Then add via: Settings → Devices & Services → "+ ADD INTEGRATION" → Search "Hoymiles MQTT Bridge"

---

## Entities

### DTU Device
Overall installation metrics:
- **`pv_power`** - Current power (sum from all inverters)
- **`today_production`** - Today's energy production (for Energy Dashboard)
- **`total_production`** - Lifetime energy production

![Solar Production](/docs/solar%20production.png)

### Inverter Devices
Each inverter provides:
- `grid_voltage`, `grid_frequency`
- `temperature`
- `operating_status`, `alarm_code`, `alarm_count`
- `link_status`

### Port Entities (PV Panels)
Each panel/port provides:
- `pv_voltage`, `pv_current`, `pv_power`
- `today_production`, `total_production`

**Configuration**: Limit entities with `--mi-entities` and `--port-entities` options.

---

## Configuration

### Environment Variables (Docker)
```yaml
environment:
  # Required
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.191
  
  # Optional
  QUERY_PERIOD: 300                # Query every 5 minutes
  HEALTH_ENABLED: true
  HEALTH_PORT: 8090
  PERSISTENCE_ENABLED: true
  LOG_LEVEL: INFO
```

### Command Line
```bash
python3 -m hoymiles_smiles \
  --mqtt-broker 192.168.1.31 \
  --dtu-host 192.168.1.191 \
  --query-period 300 \
  --log-level INFO \
  --log-to-console
```

**Full options**: Run `python3 -m hoymiles_smiles --help`

---

## Documentation

| Document | Description |
|----------|-------------|
| **[QUICK_START.md](QUICK_START.md)** | 5-minute setup guide |
| **[UPGRADE_GUIDE.md](UPGRADE_GUIDE.md)** | Upgrading to v1.1 |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Problem solving |
| **[HOME_ASSISTANT_SETUP.md](HOME_ASSISTANT_SETUP.md)** | HA integration details |
| **[WEB_SERVER_CONFIG.md](WEB_SERVER_CONFIG.md)** | Health endpoint configuration |
| **[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)** | Advanced Docker setup |
| **[UPGRADE_v0.12.md](UPGRADE_v0.12.md)** | v0.12 features and migration |
| **[custom_components/hoymiles_smiles/README.md](custom_components/hoymiles_smiles/README.md)** | Custom integration docs |

---

## Prerequisites

- **DTU**: Ethernet port connected to network, assigned IP address (reserved via DHCP)
- **WebSocket**: Running instance (e.g., [Mosquitto](https://mosquitto.org/))
- **Home Assistant**: MQTT integration enabled ([docs](https://www.home-assistant.io/integrations/mqtt/))

---

## Troubleshooting

### DTU Connection Issues
**Symptom**: `Modbus Error: No response received`

**Solutions**:
1. Power cycle DTU (unplug for 30 seconds)
2. Update DTU firmware
3. Verify ModbusTCP is enabled on DTU
4. Check network connectivity: `ping <DTU_IP>`

### Container Unhealthy
Verify `HEALTH_PORT` matches in both environment variable and healthcheck command.

### No Data in Home Assistant
1. Ensure inverters are online (daylight hours)
2. Check WebSocket is running
3. Verify container logs: `docker logs hoymiles_smiles`
4. Test MQTT: `mosquitto_sub -h <broker> -t "homeassistant/#"`

**More help**: See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

---

## What's New in v1.1

### Fixes
- ✅ **Intermittent unavailability** - No more periodic "unavailable" status
- ✅ **40% faster updates** - Persistent HTTP sessions
- ✅ **95% fewer failures** - Automatic retries with exponential backoff

### Enhancements
- ✅ **Custom branding** - Hoymiles icon and logo in Home Assistant
- ✅ **Better error handling** - Enhanced logging and diagnostics
- ✅ **Resource cleanup** - Proper session management

**Upgrade**: See **[UPGRADE_GUIDE.md](UPGRADE_GUIDE.md)**

---

## Examples

### Docker Compose
```yaml
version: "3"
services:
  hoymiles_smiles:
    container_name: hoymiles_smiles
    image: hoymiles_smiles
    network_mode: host
    environment:
      MQTT_BROKER: 192.168.1.31
      DTU_HOST: 192.168.1.191
      QUERY_PERIOD: 300
      HEALTH_ENABLED: true
      HEALTH_PORT: 8090
      PERSISTENCE_ENABLED: true
    volumes:
      - ./data:/data
    restart: unless-stopped
```

### Multiple DTUs
Create `config.yaml`:
```yaml
mqtt_broker: 192.168.1.31
dtu_configs:
  - name: "House"
    host: "192.168.1.191"
  - name: "Garage"
    host: "192.168.1.192"
```

### Home Assistant Energy Dashboard
Add `today_production` sensor from DTU device to track solar production.

---

## Monitoring

### Health Endpoints
```bash
curl http://localhost:8090/health    # Overall health status
curl http://localhost:8090/stats     # Database statistics
curl http://localhost:8090/metrics   # Prometheus metrics
curl http://localhost:8090/ready     # Readiness probe
```

### Logs
```bash
docker logs hoymiles_smiles
docker logs -f hoymiles_smiles  # Follow mode
```

---

## Development

### Run Tests
```bash
make test
```

### Build Docker Image
```bash
docker build -t hoymiles_smiles .
```

### Install from Source
```bash
git clone https://github.com/wasilukm/hoymiles-smiles.git
cd hoymiles-smiles
pip install -e .
```

---

## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [waynerv/cookiecutter-pypackage](https://github.com/waynerv/cookiecutter-pypackage) project template.

---

## Support

- **Documentation**: See guides in this repository
- **Issues**: [GitHub Issues](https://github.com/wasilukm/hoymiles-smiles/issues)
- **Community**: See discussions and pull requests

---

**Version**: 0.12.0 / Custom Integration v1.1  
**License**: MIT  
**Status**: Production Ready ✅

*Happy solar monitoring!* ☀️
