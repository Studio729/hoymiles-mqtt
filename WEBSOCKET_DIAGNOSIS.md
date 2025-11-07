# WebSocket Connection Diagnosis

## What We Found

Your logs reveal the **exact problem**:

### ✅ Bridge Side (Working Perfectly)
```
Successfully queried DTU in 5.71s - Found 37 inverters
Preparing WebSocket push: 11 inverters, 37 total ports
Successfully pushed data via WebSocket to 0 connections  ← THE PROBLEM
```

The bridge is:
- ✅ Collecting data from DTUs
- ✅ Saving to database
- ✅ Preparing WebSocket pushes
- ❌ **Has ZERO WebSocket connections**

### ❌ Home Assistant Side (Not Registering)
```
[API Request] GET /api/inverters from 192.168.1.23
```

Home Assistant is:
- ✅ Running and reachable
- ✅ Making API calls to the bridge
- ❌ **NOT registering its WebSocket URL**

## The Missing Step

Home Assistant should call this on startup:
```
POST http://hoymiles-smiles:8080/api/websocket/register
{
  "websocket_url": "ws://192.168.1.23:8123/api/hoymiles_smiles/ws?token=...",
  "name": "Home Assistant"
}
```

**This call is not happening**, which means the custom component either:
1. Hasn't been properly installed
2. Is an older version without WebSocket support
3. Home Assistant hasn't been restarted since installation

## Solution

### Step 1: Verify Custom Component Installation

The custom component files should be at:
```
/config/custom_components/hoymiles_smiles/
├── __init__.py          ← Must have line 48: "await coordinator.register_websocket_with_bridge(ws_url)"
├── coordinator.py       ← Must have register_websocket_with_bridge() method
├── websocket_server.py  ← WebSocket server for receiving pushes
├── sensor.py
├── binary_sensor.py
├── config_flow.py
├── manifest.json
├── strings.json
└── const.py
```

**Where `/config` is your Home Assistant configuration directory.**

If you're using:
- **Home Assistant OS/Supervised**: `/config` is auto-mounted
- **Docker Compose**: Check your docker-compose.yml volumes
- **Core installation**: Usually `~/.homeassistant/`

### Step 2: Restart Home Assistant

#### Via UI:
```
Settings → System → Restart Home Assistant
```

#### Via CLI (if using HA OS):
```bash
ha core restart
```

#### Via Docker:
```bash
docker restart homeassistant
```

### Step 3: Watch the Logs

#### Home Assistant Logs:
Look for these messages immediately after restart:
```
[WebSocket Registration] Registering with bridge at 192.168.1.191:8080
[WebSocket Registration] ✓ Successfully registered with bridge. Push updates are enabled.
```

If you see errors:
```
[WebSocket Registration] ✗ Bridge does not support WebSocket endpoint
→ Check bridge is running and reachable

[WebSocket Registration] ✗ Could not register with bridge
→ Check network connectivity between HA and bridge
```

#### Bridge Logs:
After HA restart, watch for:
```bash
docker-compose logs -f hoymiles-smiles | grep -E "WebSocket|API Request"
```

You should see:
```
Registered WebSocket: Home Assistant -> ws://192.168.1.23:8123/...
[WebSocket] Connecting to Home Assistant (ws://...)
[WebSocket] ✓ Connected to: Home Assistant
Successfully pushed data via WebSocket to 1 connections  ← SUCCESS!
```

### Step 4: Verify It's Working

Run the diagnostic script:
```bash
./diagnose_websocket.sh
```

Or manually check:
```bash
# Bridge should show 1 connection now
docker logs hoymiles-smiles 2>&1 | grep "Successfully pushed data via WebSocket"

# Should see:
# Successfully pushed data via WebSocket to 1 connections
```

## If It's Still Not Working

### Check 1: Home Assistant can reach the bridge

From Home Assistant's terminal or Docker container:
```bash
curl http://192.168.1.191:8080/health
```

Should return JSON with `"healthy": true`

### Check 2: Custom component is loaded

In Home Assistant:
1. Go to **Settings → Devices & Services**
2. Look for "Hoymiles S-Miles" integration
3. Check if it shows your inverters
4. Look at **Settings → System → Logs** for any error messages

### Check 3: Network connectivity

Ensure both containers are on the same Docker network:
```bash
docker network inspect hoymiles-network
```

Both `hoymiles-smiles` and `homeassistant` should be listed.

## Expected Final State

Once working, you should see this pattern every 60 seconds:

**Bridge logs:**
```
[05:10:25] Querying DTU at 192.168.1.191:502
[05:10:31] Successfully queried DTU in 6.25s - Found 37 inverters
[05:10:31] Preparing WebSocket push: 11 inverters, 37 total ports
[05:10:31] [WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
[05:10:31] [WebSocket] ✓ Successfully sent update to Home Assistant
[05:10:31] Successfully pushed data via WebSocket to 1 connections
```

**Home Assistant logs:**
```
[05:10:31] [WebSocket Server] Received message type: update (size: 45231 bytes)
[05:10:31] [WebSocket Server] Processing update: 11 inverters, 37 ports
[05:10:31] [WebSocket Server] ✓ Update processed successfully
[05:10:31] [Coordinator] [Push] ✓ Received push update with 11 inverters
```

**Home Assistant sensors:**
- Should update immediately (within 1-2 seconds of DTU query)
- No more "[Poll] No push data available" warnings
- History should show continuous data every 60 seconds

## What To Report Back

After restarting Home Assistant, please share:

1. **Home Assistant startup logs** (first 100 lines after restart):
   ```bash
   docker logs homeassistant 2>&1 | head -100 | grep -i hoymiles
   ```

2. **Bridge logs** (showing WebSocket connection):
   ```bash
   docker logs hoymiles-smiles 2>&1 | grep -E "WebSocket|Registered"
   ```

3. **Current connection count**:
   ```bash
   docker logs hoymiles-smiles 2>&1 | tail -20 | grep "Successfully pushed"
   ```

This will tell us exactly where we are and what to fix next!

