# WebSocket Push Updates Fix - Summary

## Problem Identified

Your sensors were going `unavailable` frequently and Home Assistant history showed very few records because:

1. **The bridge was collecting data correctly** every 60 seconds and storing it in PostgreSQL
2. **Home Assistant sensors were making individual API calls** for each sensor on every update
3. **These API calls were timing out/failing**, causing sensors to go unavailable
4. **WebSocket push was partially implemented** but not being used by the sensors

### Root Cause
- Bridge was pushing data via WebSocket with basic inverter metadata only (not latest readings)
- Home Assistant coordinator received push data but sensors ignored it
- Each sensor (InverterSensor, PortSensor, InverterAggregateSensor) made separate API calls
- With multiple inverters × multiple ports, this created dozens of concurrent API calls every minute
- These calls frequently timed out, causing `unavailable` states

## Changes Made

### 1. Bridge Side (hoymiles_smiles/)

#### `persistence.py`
- **Added** `get_all_inverters_with_data()` method
  - Returns enriched inverter data with latest readings AND port data
  - Includes all metrics (voltage, current, power, production, status, etc.)
  - Groups port data by port number for efficient access

#### `runners.py`
- **Modified** `_send_websocket_update()` to use enriched data
  - Changed from `get_all_inverters()` to `get_all_inverters_with_data()`
  - Added debug logging showing inverter and port counts
  - Added info logging showing successful pushes

### 2. Home Assistant Side (custom_components/hoymiles_smiles/)

#### `coordinator.py`
- **Added** `get_inverter_data(serial_number)` - gets cached inverter data (no API call)
- **Added** `get_port_data(serial_number, port_number)` - gets cached port data (no API call)
- **Modified** `get_inverter_latest_data()` - marked as DEPRECATED, only used during initial setup
- **Enhanced logging**:
  - INFO level: Shows when using pushed data vs polling
  - WARNING level: Alerts when falling back to polling (stale/missing push data)
  - WebSocket registration success/failure clearly logged

#### `sensor.py`
- **Modified** `InverterSensor.async_update()` - now uses `coordinator.get_inverter_data()` (cached)
- **Modified** `PortSensor.async_update()` - now uses `coordinator.get_port_data()` (cached)
- **Modified** `InverterAggregateSensor.async_update()` - now uses `coordinator.get_inverter_data()` (cached)
- **Removed** unnecessary `_latest_data` attribute from PortSensor
- **Added** debug logging showing sensor initialization and data availability

## Expected Behavior After Fix

### Normal Operation (WebSocket Working)
Every 60 seconds:
1. Bridge queries DTU and saves to PostgreSQL
2. Bridge pushes complete data to Home Assistant via WebSocket
3. Home Assistant coordinator receives push and updates cached data
4. All sensors read from cached data (NO API CALLS)
5. Sensors update reliably without going unavailable

**Home Assistant Logs (INFO level):**
```
[WebSocket Registration] ✓ Successfully registered with bridge. Push updates are enabled.
[WebSocket Push] ✓ Received data from bridge: 4 inverters, 8 ports
[Push Data] Using pushed data from bridge (age: 2.3s, max: 120.0s, inverters: 4)
```

### Fallback Mode (WebSocket Issues)
If WebSocket connection fails:
1. Bridge still queries DTU and saves to PostgreSQL every 60 seconds
2. Home Assistant coordinator falls back to polling API endpoints
3. Sensors still read from coordinator's cached data (from polling)
4. **Logs will show WARNING messages** indicating fallback mode

**Home Assistant Logs (WARNING level):**
```
[WebSocket Registration] ✗ Could not register with bridge: Connection refused. Push updates will NOT work - falling back to polling only.
[Poll] No push data available, polling API. WebSocket push may not be configured or connected.
```

## Performance Improvements

### Before Fix
- **API Calls per Update**: 10-30+ (depending on inverter/port count)
- **Update Reliability**: Poor (frequent timeouts)
- **Database Records**: Sparse (only recorded on success/failure transitions)
- **Sensor State**: Frequently `unavailable` or `unknown`

### After Fix
- **API Calls per Update**: 0 (when WebSocket working) or 3 (health, stats, inverters - when polling)
- **Update Reliability**: Excellent (uses cached data)
- **Database Records**: Every state change recorded
- **Sensor State**: Stable and available

## How to Verify

### 1. Check WebSocket Registration
Look for this in Home Assistant logs:
```
[WebSocket Registration] ✓ Successfully registered with bridge. Push updates are enabled.
```

If you see errors, check:
- Bridge is running and accessible
- Bridge has `/api/websocket/register` endpoint
- No firewall blocking WebSocket connections

### 2. Monitor Push Updates
In Home Assistant logs (set to INFO level), you should see every 60 seconds:
```
[WebSocket Push] ✓ Received data from bridge: X inverters, Y ports
```

If not appearing:
- Check bridge logs for WebSocket connection errors
- Verify bridge is successfully connecting to Home Assistant WebSocket

### 3. Check Sensor Updates
Your sensors should now:
- Stay `available` consistently
- Update every 60 seconds with new values
- Build complete history in Home Assistant recorder

### 4. Monitor History
After running for a few hours, check sensor history:
- Should have ~60 records per hour (one per minute)
- No more long gaps with `unavailable`
- Smooth data transitions

## Enabling Debug Logging

To see detailed WebSocket activity, add to Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hoymiles_smiles: debug
    custom_components.hoymiles_smiles.coordinator: info
```

For bridge logging, set in your config:
```yaml
log_level: "INFO"  # or "DEBUG" for more detail
```

## Troubleshooting

### Issue: Still seeing "unavailable" states

**Check:**
1. Bridge is running and accessible
2. WebSocket registration succeeded (check logs)
3. Push updates are being received (check logs every 60s)
4. Bridge can query DTU successfully

### Issue: "Push data is stale" warnings

**Cause:** WebSocket connection dropped or bridge stopped pushing

**Fix:**
- Restart the bridge to re-establish WebSocket connection
- Check bridge logs for WebSocket errors
- Verify Home Assistant WebSocket endpoint is accessible from bridge

### Issue: "No push data available, polling API"

**Cause:** WebSocket registration failed or not supported

**Fix:**
- Update bridge to latest version with WebSocket support
- Check bridge logs for registration endpoint errors
- Verify `/api/websocket/register` endpoint exists on bridge

## Files Modified

### Bridge (hoymiles-smiles/)
- `hoymiles_smiles/persistence.py` - Added enriched data method
- `hoymiles_smiles/runners.py` - Enhanced WebSocket push with complete data

### Home Assistant Integration (custom_components/hoymiles_smiles/)
- `custom_components/hoymiles_smiles/coordinator.py` - Added cached data methods, enhanced logging
- `custom_components/hoymiles_smiles/sensor.py` - Modified all sensor classes to use cached data

## Next Steps

1. **Restart the bridge** to apply changes
2. **Restart Home Assistant** to load updated integration
3. **Monitor logs** for WebSocket registration and push updates
4. **Wait 5-10 minutes** and check sensor history
5. **Verify** sensors are staying available and building history

If you encounter issues, check logs first - they now clearly indicate:
- ✓ Success messages (WebSocket working)
- ✗ Error messages (what's wrong and what to check)

