# Upgrade Guide to v0.12.0

This guide will help you upgrade from v0.11.0 to v0.12.0, which includes major enhancements and new features.

## Breaking Changes

### WebSocket client
- The WebSocket client now uses **persistent connections** instead of single-shot publishes
- This improves reliability but requires slightly more resources
- Configuration is backwards compatible

### File Structure
- Old implementation files are backed up with `_old` suffix
- New modules added: `config.py`, `persistence.py`, `health.py`, `circuit_breaker.py`, `mqtt_client.py`, `logging_config.py`

## New Features in v0.12.0

### 1. **Enhanced Configuration System**
- Type-safe configuration with Pydantic validation
- Support for YAML configuration files
- Environment variable support (unchanged)
- Better error messages for invalid configurations

### 2. **Multiple DTU Support**
You can now monitor multiple DTUs simultaneously!

**Environment Variables (Single DTU - Backwards Compatible):**
```bash
DTU_HOST=192.168.1.100
DTU_PORT=502
```

**YAML Config (Multiple DTUs):**
```yaml
dtu_configs:
  - name: "DTU_East"
    host: "192.168.1.100"
    port: 502
    unit_id: 1
  - name: "DTU_West"
    host: "192.168.1.101"
    port: 502
    unit_id: 1
```

### 3. **Data Persistence**
- SQLite database for caching production values
- Survives container/application restarts
- Automatic daily reset
- Database backup on shutdown

**Configuration:**
```bash
PERSISTENCE_ENABLED=true
DATABASE_PATH=/data/hoymiles-smiles.db
```

### 4. **Health Monitoring & Metrics**
- HTTP health check endpoint at `:8080/health`
- Kubernetes-compatible readiness probe at `:8080/ready`
- Prometheus metrics at `:8080/metrics`
- Database statistics at `:8080/stats`

**Exposed Metrics:**
- Query success/failure rates
- DTU availability
- Power output per inverter
- Temperature per inverter
- MQTT message counts
- Circuit breaker states

### 5. **Timezone Support**
- Proper timezone handling for daily resets
- Configurable reset hour

```bash
TIMEZONE=America/New_York
RESET_HOUR=23
```

### 6. **Circuit Breaker Pattern**
- Automatic failure detection
- Prevents cascade failures
- Exponential backoff retry strategy

```bash
CIRCUIT_BREAKER_THRESHOLD=5
EXPONENTIAL_BACKOFF=true
```

### 7. **Advanced Entity Filtering**
- Exclude specific inverters
- Value multipliers (e.g., W to kW conversion)
- Custom friendly names

```bash
EXCLUDE_INVERTERS=123456789 987654321
```

```yaml
value_multipliers:
  pv_power: 0.001  # Convert W to kW
```

### 8. **Structured Logging**
- JSON logging support
- Rotating log files
- Better debugging

```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
```

### 9. **Dry Run Mode**
- Test configuration without publishing
- Useful for troubleshooting

```bash
DRY_RUN=true
```

### 10. **Graceful Shutdown**
- Proper signal handling
- Flushes all pending messages
- Saves cache to persistence
- Database backup

## Migration Steps

### Docker Compose Users

1. **Backup your data:**
```bash
docker-compose down
cp -r ./data ./data_backup
```

2. **Update docker-compose.yml:**
```bash
cp docker-compose.yml docker-compose.yml.old
# Copy the new docker-compose.yml from the repository
```

3. **Update environment variables:**
```bash
cp .env .env.old
# Add new variables from env.example
```

4. **Start services:**
```bash
docker-compose pull
docker-compose up -d
```

5. **Verify health:**
```bash
curl http://localhost:8080/health
```

### Direct Python Users

1. **Update dependencies:**
```bash
pip install --upgrade hoymiles-smiles
# or with poetry:
poetry update
```

2. **Update your configuration:**
- Add new environment variables or create `config.yaml`
- See `config.yaml.example` for all options

3. **Run the application:**
```bash
python -m hoymiles_smiles --config config.yaml
```

## Configuration Reference

### Minimum Configuration (Unchanged)
```bash
MQTT_BROKER=localhost
DTU_HOST=192.168.1.100
```

### Recommended Configuration
```bash
# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883

# DTU
DTU_HOST=192.168.1.100

# Timing
QUERY_PERIOD=60
TIMEZONE=America/New_York
RESET_HOUR=23

# Persistence
PERSISTENCE_ENABLED=true
DATABASE_PATH=/data/hoymiles-smiles.db

# Health
HEALTH_ENABLED=true
HEALTH_PORT=8080

# Logging
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
```

## Monitoring Setup

### Prometheus + Grafana

1. **Start monitoring stack:**
```bash
docker-compose --profile with-monitoring up -d
```

2. **Access Grafana:**
- URL: http://localhost:3000
- Default credentials: admin/admin

3. **Add Prometheus data source:**
- URL: http://prometheus:9090

4. **Import dashboard:**
- Create dashboard using metrics from `/metrics` endpoint

### Health Checks in Kubernetes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
```

## Troubleshooting

### Health Check Fails
```bash
# Check health endpoint
curl http://localhost:8080/health

# Check logs
docker-compose logs hoymiles-smiles

# Check metrics
curl http://localhost:8080/metrics | grep hoymiles
```

### Database Issues
```bash
# Check database statistics
curl http://localhost:8080/stats

# Backup database manually
docker-compose exec hoymiles-smiles sqlite3 /data/hoymiles-smiles.db ".backup /data/backup.db"

# Reset database (WARNING: Loses cached data)
docker-compose down
rm ./data/hoymiles-smiles.db
docker-compose up -d
```

### Circuit Breaker Open
If the circuit breaker is open (DTU unreachable), it will automatically retry after the timeout. Check:

```bash
# Check circuit breaker status
curl http://localhost:8080/health | jq '.dtus'

# Force restart to reset
docker-compose restart hoymiles-smiles
```

### Migration from Old Version
If you experience issues after upgrading:

1. Check logs for validation errors
2. Ensure all required variables are set
3. Try dry-run mode first
4. Consult the new configuration examples

## New Docker Compose Profiles

- **Default**: Hoymiles MQTT + Mosquitto
- **with-ha**: Adds Home Assistant
- **with-monitoring**: Adds Prometheus + Grafana

```bash
# Start with Home Assistant
docker-compose --profile with-ha up -d

# Start with monitoring
docker-compose --profile with-monitoring up -d

# Start everything
docker-compose --profile with-ha --profile with-monitoring up -d
```

## Support

If you encounter issues:
1. Check the logs with increased verbosity: `LOG_LEVEL=DEBUG`
2. Try dry-run mode: `DRY_RUN=true`
3. Verify configuration with health endpoint
4. Check GitHub issues
5. Consult the updated README.md

## Rollback

If you need to rollback to v0.11.0:

```bash
docker-compose down
docker-compose pull hoymiles-smiles:0.11.0
# Restore old docker-compose.yml and .env
docker-compose up -d
```

Note: Database created by v0.12.0 is not compatible with v0.11.0.

