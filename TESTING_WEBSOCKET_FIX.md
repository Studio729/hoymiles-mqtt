# Quick Testing Guide - WebSocket Fix

## Step 1: Restart the Bridge

```bash
# If using Docker Compose
docker-compose restart

# Or if running directly
# Stop the bridge process and start it again
python3 -m hoymiles_smiles
```

## Step 2: Restart Home Assistant

Restart Home Assistant to load the updated custom component.

## Step 3: Check Logs Immediately

### In Home Assistant

Go to **Settings → System → Logs** and look for:

**✅ SUCCESS - You should see:**
```
[WebSocket Registration] ✓ Successfully registered with bridge. Push updates are enabled.
```

**❌ PROBLEM - If you see:**
```
[WebSocket Registration] ✗ Bridge does not support WebSocket endpoint
```
This means the bridge is running an older version or the endpoint is not available.

## Step 4: Monitor for Push Updates (wait 1-2 minutes)

After the first data collection cycle, you should see:

**✅ SUCCESS - Every 60 seconds:**
```
[WebSocket Push] ✓ Received data from bridge: 4 inverters, 8 ports
[Push Data] Using pushed data from bridge (age: 2.3s, max: 120.0s, inverters: 4)
```

**❌ PROBLEM - If you see:**
```
[Poll] No push data available, polling API. WebSocket push may not be configured or connected.
```
This means the bridge is not pushing data via WebSocket.

## Step 5: Check Sensor States

Go to **Developer Tools → States** and search for your inverter sensors (e.g., `sensor.inverter_*`).

**✅ SUCCESS:**
- Sensors show actual values (30.1, etc.)
- State shows "Available"
- Values update every 60 seconds

**❌ PROBLEM:**
- Sensors show "Unavailable" or "Unknown"
- Values don't update
- Check logs for errors

## Step 6: Verify History (wait 10 minutes)

Go to **History** and select one of your sensors (e.g., `sensor.inverter_114182041630_port_2_pv_voltage`).

**✅ SUCCESS:**
- Graph shows continuous data
- ~10 data points in 10 minutes
- No gaps or "unavailable" periods

**❌ PROBLEM:**
- Sparse data with gaps
- Still showing unavailable states
- Check WebSocket connection

## Quick Diagnostics

### Check Bridge is Running
```bash
# Check bridge health endpoint
curl http://YOUR_BRIDGE_IP:8080/health

# Should return:
# {"healthy": true, "uptime_seconds": 123, ...}
```

### Check Bridge Has Data
```bash
# Check if bridge has inverter data
curl http://YOUR_BRIDGE_IP:8080/api/inverters

# Should return array of inverters with data
```

### Check Home Assistant Can Reach Bridge
```bash
# From Home Assistant container/host
curl http://YOUR_BRIDGE_IP:8080/health
```

### Enable Debug Logging

**In Home Assistant** (`configuration.yaml`):
```yaml
logger:
  default: info
  logs:
    custom_components.hoymiles_smiles.coordinator: debug
    custom_components.hoymiles_smiles.sensor: debug
```

**In Bridge** (environment variable or config):
```bash
LOG_LEVEL=DEBUG
```

## Expected Timeline

| Time | What Should Happen |
|------|-------------------|
| 0:00 | Restart bridge and HA |
| 0:01 | WebSocket registration logged |
| 1:00 | First data collection and push |
| 1:01 | Push update received in HA |
| 1:01 | Sensors update with new values |
| 2:00 | Second push update |
| 10:00 | ~10 data points in history |

## Common Issues

### Issue 1: No WebSocket Registration Message

**Symptom:** No registration log message appears  
**Cause:** Integration not loading or bridge not reachable  
**Fix:**
1. Check HA logs for integration errors
2. Verify bridge is accessible: `curl http://BRIDGE_IP:8080/health`
3. Check firewall rules

### Issue 2: Registration Succeeds but No Push Updates

**Symptom:** Registration ✓ but no push updates received  
**Cause:** Bridge can't connect back to Home Assistant WebSocket  
**Check Bridge Logs:**
```bash
docker-compose logs -f hoymiles-smiles
# Look for WebSocket connection errors
```

**Fix:**
- Ensure Home Assistant is accessible from bridge network
- Check WebSocket URL is correct
- Verify no firewall blocking

### Issue 3: Sensors Still Show "Unavailable"

**Symptom:** Push updates received but sensors still unavailable  
**Cause:** Sensor data missing in pushed payload  
**Check:**
1. Look for debug logs: `[Sensor Init] PortSensor ... using cached data: no data yet`
2. Verify bridge is collecting data from DTU
3. Check bridge logs for DTU query errors

### Issue 4: Bridge Not Collecting Data

**Symptom:** Bridge runs but no data in database  
**Check Bridge Logs:**
```bash
docker-compose logs hoymiles-smiles | grep "Successfully queried"
# Should see: Successfully queried DTU in X.XXs - Found N inverters
```

**Fix:**
- Verify DTU_HOST and DTU_PORT settings
- Check DTU is accessible: `ping YOUR_DTU_IP`
- Check Modbus port is open: `telnet YOUR_DTU_IP 502`

## Success Indicators

When everything is working:

1. ✅ **Bridge logs** show successful DTU queries every 60s
2. ✅ **Bridge logs** show successful WebSocket pushes
3. ✅ **HA logs** show WebSocket registration success
4. ✅ **HA logs** show push updates every 60s
5. ✅ **HA logs** show "Using pushed data from bridge"
6. ✅ **Sensors** stay available with updating values
7. ✅ **History** shows continuous data

## If All Else Fails

1. **Collect logs:**
   - Bridge logs: `docker-compose logs > bridge.log`
   - HA logs: Copy from Settings → System → Logs
   
2. **Check versions:**
   - Bridge version
   - Home Assistant version
   - Integration version
   
3. **Verify configuration:**
   - Bridge config (DTU_HOST, DB settings)
   - HA integration config
   
4. **Test connectivity:**
   - Bridge → DTU: `ping DTU_IP`
   - HA → Bridge: `curl http://BRIDGE_IP:8080/health`
   - Bridge → HA: Check bridge logs for WebSocket connection

## Getting More Help

If issues persist, gather:
- Bridge logs (with LOG_LEVEL=DEBUG)
- Home Assistant logs (with debug enabled for integration)
- Configuration files (redact sensitive info)
- Network topology (how systems are connected)
- Output of diagnostic commands above

