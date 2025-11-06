# Troubleshooting Guide

## Docker Container Issues

### Container Shows Unhealthy
**Check**:
1. Verify health endpoint is accessible:
   ```bash
   docker exec hoymiles_smiles curl -f http://localhost:8090/health
   ```
2. Check `HEALTH_PORT` matches in:
   - `docker-compose.yml` environment variable
   - Docker healthcheck command
3. Ensure health server is enabled: `HEALTH_ENABLED=true`

### Port Mismatch
If healthcheck fails, verify port configuration:
```yaml
environment:
  HEALTH_PORT: 8090
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
```

**Solution**: Ensure both use the same port.

---

## DTU Connection Issues

### Cannot Connect to DTU
**Symptoms**: 
- `Modbus Error: No response received`
- Repeated connection errors

**Solutions**:
1. **Power cycle the DTU** - Unplug for 30 seconds
2. **Verify network connectivity**:
   ```bash
   ping <DTU_IP>
   ```
3. **Check DTU firmware** - Update if available
4. **Verify ModbusTCP is enabled** on DTU
5. **Check firewall rules** - Ensure port 502 is open

### Intermittent DTU Responses
**Enable circuit breaker** in `docker-compose.yml`:
```yaml
environment:
  CIRCUIT_BREAKER_THRESHOLD: 5
  EXPONENTIAL_BACKOFF: true
```

This prevents cascading failures when DTU is temporarily unresponsive.

---

## Home Assistant Integration Issues

### Custom Integration: "Application Healthy" Unavailable

**Fixed in v1.1**: If running v1.0, upgrade to v1.1 (see `UPGRADE_GUIDE.md`)

**If still occurring**:
1. **Enable debug logging** in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.hoymiles_smiles.coordinator: debug
   ```

2. **Check logs** for:
   - Timeout errors
   - Connection refused
   - Network issues

3. **Test health endpoint manually**:
   ```bash
   curl -v http://<HOST>:<HEALTH_PORT>/health
   curl -v http://<HOST>:<HEALTH_PORT>/stats
   ```
   Both should return JSON within 1 second.

4. **Verify network connectivity** between HA and bridge

### Icons/Logo Not Showing
**Solution**:
1. **Clear browser cache**: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
2. **Verify files exist**:
   ```bash
   ls -lh /config/custom_components/hoymiles_smiles/*.png
   ```
   Should show `icon.png` (1.0K) and `logo.png` (3.8K)
3. Try another browser to rule out caching

### Entities Show "Unknown" or "Unavailable"
**Check**:
1. DTU is powered on and connected
2. Inverters are online (check during daylight)
3. Bridge container is running: `docker ps`
4. WebSocket is accessible
5. Check bridge logs for errors: `docker logs hoymiles_smiles`

---

## MQTT Issues

### Messages Not Publishing
**Check**:
1. **WebSocket is running**:
   ```bash
   docker ps | grep mosquitto
   ```

2. **Test MQTT connection**:
   ```bash
   mosquitto_sub -h <MQTT_BROKER> -t "homeassistant/#" -v
   ```

3. **Verify credentials** in `docker-compose.yml`:
   ```yaml
   environment:
     MQTT_BROKER: 192.168.1.31
     MQTT_USER: your_user      # if broker requires auth
     MQTT_PASSWORD: your_pass   # if broker requires auth
   ```

4. **Check bridge logs**:
   ```bash
   docker logs hoymiles_smiles | grep -i mqtt
   ```

### High MQTT Error Count
**Check** `/metrics` endpoint:
```bash
curl http://<HOST>:<HEALTH_PORT>/metrics
```

Look for `mqtt_errors_total` - if increasing:
1. Check WebSocket logs
2. Verify network stability
3. Check broker is not overloaded

---

## Performance Issues

### Slow Updates
**Check query period**:
```yaml
environment:
  QUERY_PERIOD: 300  # Reduce if needed (minimum: 10)
```

**Note**: Too frequent queries may overload DTU.

### High CPU/Memory Usage
**Enable metrics monitoring**:
```bash
curl http://<HOST>:<HEALTH_PORT>/metrics
```

**Solutions**:
1. Increase `QUERY_PERIOD` to reduce load
2. Limit entities with `MI_ENTITIES` and `PORT_ENTITIES`
3. Check for DTU communication issues causing retries

---

## Database Issues

### Database Growing Too Large
**Check size**:
```bash
curl http://<HOST>:<HEALTH_PORT>/stats
```

**Solution**: Database auto-manages, but you can reset:
```bash
docker exec hoymiles_smiles rm /data/hoymiles-smiles.db
docker restart hoymiles_smiles
```

**Note**: This resets `today_production` and `total_production` cache.

---

## Logging and Debugging

### Enable Debug Logging
**For Docker**:
```yaml
environment:
  LOG_LEVEL: DEBUG
  LOG_FORMAT: standard  # or 'json' for structured logs
  LOG_TO_CONSOLE: true
```

**For Home Assistant Integration**:
```yaml
logger:
  logs:
    custom_components.hoymiles_smiles: debug
```

### View Logs
**Docker**:
```bash
docker logs hoymiles_smiles
docker logs -f hoymiles_smiles  # Follow mode
docker logs --tail 100 hoymiles_smiles  # Last 100 lines
```

**Home Assistant**:
- Settings → System → Logs
- Filter by `hoymiles_smiles`

### Important Log Messages

**Good**:
```
Health check server started on 0.0.0.0:8090
Created new aiohttp session for 192.168.1.191:8090
Successfully queried DTU
```

**Warning**:
```
Timeout fetching data from DTU
Retry X/2 for /health after error
```

**Error**:
```
All retries failed for /health
Cannot connect to WebSocket
Modbus Error: No response received
```

---

## Health Endpoints

### Check Application Health
```bash
# Overall health
curl http://<HOST>:<HEALTH_PORT>/health | jq

# Database stats
curl http://<HOST>:<HEALTH_PORT>/stats | jq

# Prometheus metrics
curl http://<HOST>:<HEALTH_PORT>/metrics

# Readiness check
curl http://<HOST>:<HEALTH_PORT>/ready
```

### Understanding Health Response
```json
{
  "healthy": true,
  "uptime_seconds": 3600,
  "start_time": "2024-11-05T10:00:00",
  "dtus": {
    "DTU": {
      "status": "healthy",
      "last_successful_query": "2024-11-05T11:00:00",
      "query_count": 120,
      "error_count": 0
    }
  },
  "mqtt": {
    "messages_published": 1200,
    "errors": 0
  }
}
```

**Unhealthy if**:
- `healthy: false`
- High `error_count`
- Old `last_successful_query` (> 5 minutes)
- High MQTT errors

---

## Common Error Messages

### "No response received, expected at least 8 bytes"
**Cause**: DTU not responding  
**Solution**: Power cycle DTU, update firmware

### "Connection refused"
**Cause**: Wrong host/port or service not running  
**Solution**: Verify `DTU_HOST`, `DTU_PORT`, `HEALTH_PORT`

### "Timeout communicating with API"
**Cause**: Network latency or endpoint slow  
**Solution**: Increase timeout, check network

### "MQTT connection failed"
**Cause**: Broker unreachable or wrong credentials  
**Solution**: Verify `MQTT_BROKER`, credentials, broker is running

---

## Getting Help

### Gather Information
1. **Version**: `docker exec hoymiles_smiles python3 -m hoymiles_smiles --version`
2. **Logs**: Last 100 lines with timestamps
3. **Configuration**: Your `docker-compose.yml` (redact passwords)
4. **Health status**: `curl http://<HOST>:<HEALTH_PORT>/health`
5. **Network test**: Can you ping DTU and WebSocket?

### Report Issues
Include:
- Hoymiles MQTT version
- DTU model and firmware
- Home Assistant version (if using integration)
- Full error messages from logs
- What you've already tried

---

**Need more help? Check `QUICK_START.md` for setup guidance or see the main `README.md`.**

