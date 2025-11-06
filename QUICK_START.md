# Quick Start Guide

## 5-Minute Setup

### Option 1: Docker Compose (Recommended)

1. **Create `docker-compose.yml`**:
```yaml
version: "3"

services:
  hoymiles_smiles:
    container_name: hoymiles_smiles
    image: hoymiles_smiles
    network_mode: host
    environment:
      # Required
      MQTT_BROKER: 192.168.1.31          # Your WebSocket IP
      DTU_HOST: 192.168.1.191             # Your DTU IP
      
      # Optional but recommended
      QUERY_PERIOD: 300                   # Query every 5 minutes
      HEALTH_ENABLED: true
      HEALTH_PORT: 8090
      METRICS_ENABLED: true
      LOG_LEVEL: INFO
      LOG_TO_CONSOLE: true
      PERSISTENCE_ENABLED: true
      DATABASE_PATH: /data/hoymiles-smiles.db
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    
    volumes:
      - ./data:/data
    
    restart: unless-stopped
```

2. **Build and run**:
```bash
docker build https://github.com/wasilukm/hoymiles-smiles.git#v0.12.0 -t hoymiles_smiles
docker-compose up -d
```

3. **Verify**:
```bash
docker logs hoymiles_smiles
curl http://localhost:8090/health
```

---

### Option 2: Python Package

1. **Install**:
```bash
pip install hoymiles-smiles
```

2. **Run**:
```bash
python3 -m hoymiles_smiles \
  --mqtt-broker 192.168.1.31 \
  --dtu-host 192.168.1.191 \
  --log-to-console \
  --log-level INFO
```

---

## Home Assistant Integration

### Method 1: Custom Integration (Recommended)

**Features**: UI configuration, native entities, no YAML needed

1. **Install**:
```bash
cd /Users/tim/Downloads/hoymiles-smiles-main
./install_v1.1.sh
```

2. **Restart Home Assistant**

3. **Add Integration**:
   - Settings → Devices & Services
   - Click "+ ADD INTEGRATION"
   - Search "Hoymiles MQTT Bridge"
   - Enter host and port
   - Done!

**Provides**:
- 8 sensor entities (uptime, messages, queries, errors, database stats)
- 1 binary sensor (application health)
- Device grouping
- Custom Hoymiles icon/logo

---

### Method 2: YAML Configuration

**Features**: Manual configuration, full control

1. **Copy `home_assistant_sensors.yaml` content** to your `configuration.yaml`

2. **Update configuration**:
```yaml
sensor:
  - platform: rest
    resource: http://192.168.1.191:8090/health  # Update host:port
    # ... rest of config
```

3. **Restart Home Assistant**

**See**: `HOME_ASSISTANT_SETUP.md` for detailed YAML setup

---

## Configuration Variables

### Essential
| Variable | Description | Example |
|----------|-------------|---------|
| `MQTT_BROKER` | WebSocket address | `192.168.1.31` |
| `DTU_HOST` | Hoymiles DTU address | `192.168.1.191` |

### Common Options
| Variable | Default | Description |
|----------|---------|-------------|
| `QUERY_PERIOD` | 60 | Query interval in seconds |
| `HEALTH_ENABLED` | false | Enable health endpoints |
| `HEALTH_PORT` | 8080 | Health server port |
| `LOG_LEVEL` | WARNING | DEBUG, INFO, WARNING, ERROR |
| `PERSISTENCE_ENABLED` | false | Enable production caching |

**See**: `WEB_SERVER_CONFIG.md` for all configuration options

---

## Verification Checklist

### After Start
- [ ] Container is running: `docker ps`
- [ ] No errors in logs: `docker logs hoymiles_smiles`
- [ ] Health endpoint responds: `curl http://localhost:8090/health`
- [ ] DTU queries working (check logs)
- [ ] MQTT messages publishing (check WebSocket)

### In Home Assistant
- [ ] DTU device appears
- [ ] Inverter devices appear
- [ ] Entities show current values (during daylight)
- [ ] `today_production` updating
- [ ] No "unavailable" or "unknown" states

---

## Quick Commands

```bash
# View logs
docker logs hoymiles_smiles
docker logs -f hoymiles_smiles  # Follow

# Check health
curl http://localhost:8090/health | jq
curl http://localhost:8090/stats | jq
curl http://localhost:8090/metrics

# Restart
docker restart hoymiles_smiles

# Debug mode
docker-compose down
docker-compose up  # Watch output

# Check MQTT messages
mosquitto_sub -h 192.168.1.31 -t "homeassistant/#" -v
```

---

## Troubleshooting

### Container unhealthy
- Check `HEALTH_PORT` matches in environment and healthcheck
- Verify health endpoint: `docker exec hoymiles_smiles curl -f http://localhost:8090/health`

### No data in Home Assistant
- Verify WebSocket is running
- Check inverters are online (daylight hours)
- Check logs for DTU connection errors
- Test MQTT: `mosquitto_sub -h <broker> -t "homeassistant/#"`

### DTU connection errors
- Power cycle DTU (unplug 30 seconds)
- Verify DTU IP address
- Check ModbusTCP is enabled on DTU
- Update DTU firmware if available

**More help**: See `TROUBLESHOOTING.md`

---

##Next Steps

1. **Monitor for 24 hours** - Ensure stable operation
2. **Add to Home Assistant Energy dashboard** - Use `today_production` sensor
3. **Set up automations** - Alert on errors or low production
4. **Configure Grafana** (optional) - Visualize metrics from `/metrics` endpoint

---

**Documentation**:
- **README.md** - Project overview and features
- **TROUBLESHOOTING.md** - Detailed problem solving
- **UPGRADE_GUIDE.md** - Upgrading to v1.1
- **HOME_ASSISTANT_SETUP.md** - HA integration details
- **WEB_SERVER_CONFIG.md** - Health endpoint configuration
- **DOCKER_COMPOSE_GUIDE.md** - Advanced Docker setup

**Ready to go!** 🚀
