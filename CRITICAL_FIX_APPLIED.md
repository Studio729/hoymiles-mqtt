# Critical Fix Applied - WebSocket Working But Data Missing

## What Was Wrong

Looking at your logs, the WebSocket connection WAS working:
```
[Thread-4] INFO [hoymiles_smiles.websocket_client] Registered WebSocket: Home Assistant
[Thread-4] INFO [hoymiles_smiles.websocket_client] Connecting to WebSocket: Home Assistant
[Thread-6] INFO [hoymiles_smiles.runners] Successfully pushed data via WebSocket to 1 connections
```

**BUT** Home Assistant showed:
```
[Poll] No push data available, polling API. WebSocket push may not be configured or connected.
```

And sensors had no values.

### Root Cause

The issue was **NOT** with the WebSocket connection - that was working fine!

The problem was:

1. **API endpoints were returning incomplete data**
   - `/api/inverters` returned only basic inverter metadata
   - Did NOT include latest readings (voltage, current, power, etc.)
   - Did NOT include port data
   
2. **Initial data fetch on integration load**
   - Home Assistant calls `async_config_entry_first_refresh()` which polls the API
   - Since API returned incomplete data, sensors had nothing to display
   
3. **WebSocket messages might not have been processed**
   - Server was receiving them but may not have been handled correctly
   - Added better logging to diagnose

## Fixes Applied

### 1. Fixed API Endpoints (`hoymiles_smiles/health.py`)

**Before:**
```python
# Only returned basic metadata - no readings, no ports!
inverters = self.persistence_manager.get_all_inverters()
```

**After:**
```python
# Returns enriched data with latest readings AND ports
inverters = self.persistence_manager.get_all_inverters_with_data()
```

This ensures:
- Initial poll on integration load gets complete data
- Fallback polling (if WebSocket fails) gets complete data  
- `/api/inverters/{serial}` endpoint returns complete inverter with ports

### 2. Enhanced WebSocket Logging (`websocket_server.py`)

Added detailed logging to see what's happening:
- Connection establishment
- Message receipt and processing
- Data payload details
- Success/failure indicators

### 3. Confirmed Data Flow

The complete data flow is now:
1. **Initial Load**: HA polls `/api/inverters` → gets enriched data → sensors populate
2. **Ongoing Updates**: Bridge pushes via WebSocket → HA receives → sensors update
3. **Fallback**: If WebSocket fails → HA polls `/api/inverters` → gets enriched data

## What To Do Now

### Step 1: Restart the Bridge

```bash
docker-compose restart
```

Wait for:
```
INFO Successfully queried DTU in X.XXs - Found 37 inverters
INFO Successfully pushed data via WebSocket to 1 connections
```

### Step 2: Restart Home Assistant

**Settings → System → Restart Home Assistant**

### Step 3: Check Home Assistant Logs (First 2 Minutes)

You should see (in order):

**1. WebSocket Server Setup:**
```
[WebSocket Server] Server registered at /api/hoymiles_smiles/ws - Ready to accept bridge connections
```

**2. WebSocket Registration:**
```
[WebSocket Registration] Registering with bridge at 192.168.1.191:8080
[WebSocket Registration] ✓ Successfully registered with bridge. Push updates are enabled.
```

**3. WebSocket Connection from Bridge:**
```
[WebSocket Server] ✓ Connection established from bridge (192.168.1.191) for entry xxxx
```

**4. Initial Poll (happens during setup):**
```
[API Call Start] Fetching data from 192.168.1.191:8080
[API Call] Fetching /api/inverters from 192.168.1.191:8080
[API Call] Received inverters data: count=37
[API Call Complete] Success in X.XXs from 192.168.1.191:8080
```

**5. After ~60 seconds - First WebSocket Push:**
```
[WebSocket Server] Processing update: 37 inverters, 74 ports
[WebSocket Server] ✓ Update processed successfully
[WebSocket Push] ✓ Received data from bridge: 37 inverters, 74 ports
```

**6. Subsequent Updates (every 60 seconds):**
```
[Push Data] Using pushed data from bridge (age: 2.3s, max: 120.0s, inverters: 37)
[WebSocket Server] Processing update: 37 inverters, 74 ports
[WebSocket Push] ✓ Received data from bridge: 37 inverters, 74 ports
```

### Step 4: Check Sensor States

**Developer Tools → States**

Search for `sensor.inverter_`

**✅ Should see:**
- All sensors showing actual values (voltages, currents, power, etc.)
- State: "Available"
- Attributes showing serial_number, port_number, dtu_name, last_seen

**❌ If still showing unavailable:**
- Check if initial poll succeeded (look for "API Call Complete" in logs)
- Check for errors in logs
- Verify bridge has data: `curl http://192.168.1.191:8080/api/inverters` (should show 37 inverters with data)

## Diagnostic Commands

### Check Bridge Has Enriched Data
```bash
curl http://192.168.1.191:8080/api/inverters | jq '.[0]'
```

Should return something like:
```json
{
  "serial_number": "114182041630",
  "dtu_name": "DTU",
  "grid_voltage": 30.4,
  "grid_frequency": 60.0,
  "temperature": 45.2,
  "operating_status": 1,
  "alarm_code": 0,
  "link_status": 1,
  "ports": [
    {
      "port_number": 1,
      "pv_voltage": 30.1,
      "pv_current": 2.5,
      "pv_power": 75.25,
      "today_production": 1234,
      "total_production": 567890
    },
    {
      "port_number": 2,
      "pv_voltage": 30.4,
      ...
    }
  ]
}
```

**Important:** The `ports` array MUST be present with data!

### Check Home Assistant Can Fetch Data
```bash
# From HA container or host
curl http://192.168.1.191:8080/api/inverters | jq 'length'
# Should return: 37
```

### Enable Full Debug Logging

In Home Assistant `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.hoymiles_smiles: info
    custom_components.hoymiles_smiles.coordinator: info
    custom_components.hoymiles_smiles.sensor: debug
    custom_components.hoymiles_smiles.websocket_server: info
```

## Expected Behavior After Fix

### Integration Load (one-time):
1. Coordinator polls `/api/inverters`
2. Receives 37 inverters with complete data (readings + ports)
3. Sensors created and populated with initial values
4. WebSocket connection registered with bridge
5. Bridge connects back via WebSocket

### Ongoing Operation (every 60 seconds):
1. Bridge queries DTU
2. Bridge saves to PostgreSQL
3. Bridge pushes to Home Assistant via WebSocket
4. HA receives push, updates coordinator cache
5. All sensors read from cache (no API calls)
6. Sensors update with new values

### Fallback (if WebSocket fails):
1. HA detects stale push data
2. HA polls `/api/inverters` (gets enriched data)
3. Sensors still work using polled data
4. Logs show warnings about WebSocket

## Common Issues

### Issue: Initial poll fails

**Symptom:** Sensors show "unavailable" on first load  
**Log:** "API Call Failed" during setup  
**Fix:**
- Verify bridge is running and accessible
- Check bridge has data: `docker-compose logs hoymiles-smiles | grep "Successfully queried"`
- Ensure bridge is responding: `curl http://192.168.1.191:8080/health`

### Issue: WebSocket connects but no updates

**Symptom:** Connection established but no "Processing update" messages  
**Log:** "WebSocket Server ✓ Connection established" but no subsequent messages  
**Fix:**
- Check bridge logs for "Successfully pushed data via WebSocket"
- If bridge shows 0 connections, restart both bridge and HA
- Verify no firewall blocking WebSocket messages

### Issue: Sensors work initially but go unavailable

**Symptom:** Sensors show values at first, then unavailable  
**Log:** "[Push Data] Using pushed data" stops appearing  
**Cause:** WebSocket connection dropped  
**Fix:**
- Restart bridge to re-establish WebSocket
- Check for network issues between bridge and HA
- Review bridge logs for WebSocket errors

## Files Modified in This Fix

1. `hoymiles_smiles/health.py` - API endpoints now return enriched data
2. `custom_components/hoymiles_smiles/websocket_server.py` - Enhanced logging

## What Changed from Previous Fix

The previous fix correctly implemented:
- ✅ Bridge pushing enriched data via WebSocket
- ✅ Coordinator caching pushed data
- ✅ Sensors reading from cached data

But missed:
- ❌ API endpoints still returning incomplete data (for initial poll and fallback)

This fix ensures:
- ✅ API endpoints return complete data
- ✅ Initial poll populates sensors
- ✅ Fallback polling works correctly
- ✅ Better diagnostic logging

## Success Checklist

After restart, verify:

- [ ] Bridge logs show "Successfully queried DTU" every 60s
- [ ] Bridge logs show "Successfully pushed data via WebSocket to 1 connections"
- [ ] HA logs show "[WebSocket Registration] ✓ Successfully registered"
- [ ] HA logs show "[WebSocket Server] ✓ Connection established"
- [ ] HA logs show "[WebSocket Server] Processing update: 37 inverters, 74 ports"
- [ ] HA logs show "[Push Data] Using pushed data from bridge"
- [ ] All 37 inverters have sensors showing values
- [ ] Sensors stay "Available" continuously
- [ ] History shows continuous data (no gaps)

If all checkboxes are ticked: **YOU'RE DONE! Everything is working!** 🎉

If some are missing, check which step failed and review the corresponding section above.

