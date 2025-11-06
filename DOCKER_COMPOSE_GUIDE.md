# Docker Compose Configuration Guide

This project provides multiple docker-compose configurations for different use cases.

## Available Configurations

### 1. `docker-compose.user.yml` - Your Setup (Simple & Compatible)
**Best for:** Users upgrading from v0.11.0 or wanting a simple setup

```yaml
version: "3"

services:
  hoymiles_smiles:
    container_name: "hoymiles_smiles"
    image: hoymiles_smiles
    network_mode: host
    environment:
      MQTT_BROKER: 192.168.1.31
      DTU_HOST: 192.168.1.194
      MICROINVERTER_TYPE: 'HM'
      QUERY_PERIOD: 300
```

**Usage:**
```bash
# Build image
docker build -t hoymiles_smiles .

# Start service
docker-compose -f docker-compose.user.yml up -d

# View logs
docker-compose -f docker-compose.user.yml logs -f

# Stop service
docker-compose -f docker-compose.user.yml down
```

**Features:**
- ✅ Uses `network_mode: host` (no port mapping needed)
- ✅ Minimal configuration
- ✅ Watchtower compatible
- ✅ All v0.12.0 features available via optional env vars
- ✅ Backward compatible with v0.11.0

---

### 2. `docker-compose.simple.yml` - Standalone with All Options
**Best for:** Single service deployment with explicit configuration

```yaml
version: "3"

services:
  hoymiles_smiles:
    container_name: "hoymiles_smiles"
    build:
      context: .
      dockerfile: Dockerfile
    image: hoymiles_smiles
    network_mode: host
    environment:
      # All environment variables explicitly defined
      MQTT_BROKER: 192.168.1.31
      DTU_HOST: 192.168.1.194
      QUERY_PERIOD: 300
      # ... and many more options
```

**Usage:**
```bash
docker-compose -f docker-compose.simple.yml up -d
```

**Features:**
- ✅ All options visible and configurable
- ✅ Uses `network_mode: host`
- ✅ Health check enabled (port 8080)
- ✅ Persistence enabled with volume mount

---

### 3. `docker-compose.yml` - Full Stack
**Best for:** Complete home automation setup

Includes:
- Hoymiles MQTT Bridge
- Mosquitto WebSocket
- Home Assistant (optional profile)
- Prometheus (optional profile)
- Grafana (optional profile)

**Usage:**
```bash
# Default: Hoymiles + Mosquitto
docker-compose up -d

# With Home Assistant
docker-compose --profile with-ha up -d

# With monitoring
docker-compose --profile with-monitoring up -d

# Everything
docker-compose --profile with-ha --profile with-monitoring up -d
```

**Features:**
- ✅ Complete integrated stack
- ✅ Custom network (not host mode)
- ✅ All services pre-configured
- ✅ Optional monitoring and HA

---

## Environment Variables Reference

### Required
```bash
MQTT_BROKER=192.168.1.31      # WebSocket IP/hostname
DTU_HOST=192.168.1.194        # DTU IP address
```

### Common Options
```bash
MICROINVERTER_TYPE=HM         # Inverter type (HM, HMS, HMT)
QUERY_PERIOD=300              # Query interval in seconds
MQTT_PORT=1883                # MQTT port
DTU_PORT=502                  # Modbus port
TIMEZONE=UTC                  # Timezone (e.g., America/New_York)
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR
```

### Advanced Options (v0.12.0)
```bash
# Persistence
PERSISTENCE_ENABLED=true
DATABASE_PATH=/data/hoymiles-smiles.db

# Web Server / Health Monitoring
# Accessible at http://your-ip:PORT (where PORT is HEALTH_PORT value)
HEALTH_ENABLED=true
HEALTH_PORT=8080              # Change this to use a different port (e.g., 9090)
METRICS_ENABLED=true

# Security
MQTT_USER=username
MQTT_PASSWORD=password
MQTT_TLS=false

# Error Recovery
EXPONENTIAL_BACKOFF=true
CIRCUIT_BREAKER_THRESHOLD=5

# Timing
RESET_HOUR=23
EXPIRE_AFTER=0

# Logging
LOG_FORMAT=standard           # or 'json'
LOG_TO_CONSOLE=true
```

---

## Migration from Your Current Setup

### If you have this:
```yaml
version: "3"
services:
  hoymiles_smiles:
    container_name: "hoymiles_smiles"
    image: hoymiles_smiles
    network_mode: host
    environment:
      MQTT_BROKER: 192.168.1.31
      DTU_HOST: 192.168.1.194
      MICROINVERTER_TYPE: 'HM'
      QUERY_PERIOD: 300
    labels:
      - "com.centurylinklabs.watchtower.enable=false"
    restart: unless-stopped
```

### Migration Steps:

1. **Backup your current setup:**
```bash
docker-compose down
docker save hoymiles_smiles > hoymiles_smiles_backup.tar
```

2. **Pull the new code:**
```bash
git pull origin main
```

3. **Use the compatible configuration:**
```bash
# Copy your format
cp docker-compose.user.yml docker-compose.yml

# Or keep your existing file and just rebuild
docker build -t hoymiles_smiles .
```

4. **Start with your existing config (it just works!):**
```bash
docker-compose up -d
```

5. **Optional: Enable new features by adding env vars:**
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
  MICROINVERTER_TYPE: 'HM'
  QUERY_PERIOD: 300
  # New features:
  PERSISTENCE_ENABLED: true
  HEALTH_ENABLED: true
  LOG_LEVEL: INFO
```

6. **Access health check (if enabled):**
```bash
curl http://192.168.1.31:8080/health
curl http://192.168.1.31:8080/metrics
```

---

## Network Modes

### Host Mode (Your Setup)
```yaml
network_mode: host
```
**Pros:**
- ✅ No port mapping needed
- ✅ Better performance
- ✅ Simpler configuration

**Cons:**
- ❌ Less isolation
- ❌ Can't use custom networks

**When to use:** Single service deployment, simple setup

### Bridge Mode (Full Stack)
```yaml
networks:
  - hoymiles-network
```
**Pros:**
- ✅ Better isolation
- ✅ Service discovery
- ✅ Multiple services can coexist

**Cons:**
- ❌ Need port mapping
- ❌ Slightly more complex

**When to use:** Multiple services, complete stack

---

## Quick Reference

### Build Image
```bash
docker build -t hoymiles_smiles .
```

### Start Service (Your Format)
```bash
docker-compose -f docker-compose.user.yml up -d
```

### View Logs
```bash
docker-compose logs -f hoymiles_smiles
```

### Restart
```bash
docker-compose restart hoymiles_smiles
```

### Stop
```bash
docker-compose down
```

### Update to Latest
```bash
git pull
docker build -t hoymiles_smiles .
docker-compose up -d
```

### Check Health
```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

### Enable Debug Logging
```bash
# In docker-compose.yml, add:
environment:
  LOG_LEVEL: DEBUG
  LOG_TO_CONSOLE: true

# Then restart
docker-compose restart hoymiles_smiles
```

---

## Troubleshooting

### Health Port Already in Use
If port 8080 conflicts:
```yaml
environment:
  HEALTH_PORT: 8888  # Change to any available port
```

### Can't Access Health Endpoint with Host Mode
With `network_mode: host`, access health check at:
```bash
curl http://localhost:8080/health
# or
curl http://127.0.0.1:8080/health
# or your machine's IP
curl http://192.168.1.X:8080/health
```

### Disable Health Check
```yaml
environment:
  HEALTH_ENABLED: false
```

### Database Location with Host Mode
```yaml
volumes:
  - ./data:/data
environment:
  DATABASE_PATH: /data/hoymiles-smiles.db
```

---

## Recommendations

### For Your Setup (Simple, Host Mode)
Use `docker-compose.user.yml`:
- Minimal changes from your current setup
- All features available via env vars
- Uses host networking
- Watchtower compatible

### For Complete Home Automation
Use `docker-compose.yml`:
- Includes Mosquitto
- Optional Home Assistant
- Optional monitoring
- Better service isolation

### For Production
Consider:
- Using MQTT authentication
- Enabling persistence
- Setting up monitoring
- Using specific log levels
- Regular database backups

---

## Examples

### Minimal (Your Current Setup)
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
```

### With Persistence
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
  PERSISTENCE_ENABLED: true
volumes:
  - ./data:/data
```

### With Health Monitoring
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
  HEALTH_ENABLED: true
  METRICS_ENABLED: true
```

### With Debug Logging
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
  LOG_LEVEL: DEBUG
  LOG_TO_CONSOLE: true
```

### Production Ready
```yaml
environment:
  MQTT_BROKER: 192.168.1.31
  DTU_HOST: 192.168.1.194
  MICROINVERTER_TYPE: HM
  QUERY_PERIOD: 300
  TIMEZONE: America/New_York
  PERSISTENCE_ENABLED: true
  HEALTH_ENABLED: true
  METRICS_ENABLED: true
  LOG_LEVEL: INFO
  LOG_FORMAT: json
  EXPONENTIAL_BACKOFF: true
volumes:
  - ./data:/data
```

---

## Need Help?

1. Check logs: `docker-compose logs -f hoymiles_smiles`
2. Check health: `curl http://localhost:8080/health`
3. Enable debug: `LOG_LEVEL=DEBUG`
4. See [UPGRADE_v0.12.md](UPGRADE_v0.12.md) for detailed guide
5. See [QUICK_START.md](QUICK_START.md) for quick setup

