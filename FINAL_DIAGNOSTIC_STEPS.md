# Final Diagnostic Steps - WebSocket Troubleshooting

## Changes Made

Added comprehensive logging to track:
1. **WebSocket message sending** (INFO level)
2. **WebSocket connection state**
3. **API requests from Home Assistant**

## Step 1: Restart Bridge

```bash
docker-compose restart
```

## Step 2: Watch Bridge Logs in Real-Time

```bash
docker-compose logs -f hoymiles-smiles
```

## What to Look For

### A. WebSocket Registration (happens ~10 seconds after bridge starts)

**✅ SUCCESS - Should see:**
```
[Thread-X] INFO Registered WebSocket: Home Assistant (ws://192.168.1.23:8123/...)
[Thread-X] INFO [WebSocket] ✓ Connected to: Home Assistant
```

**❌ PROBLEM - If you see:**
```
[Thread-X] ERROR WebSocket connection error for Home Assistant: ...
```
OR timeout/connection refused errors.

### B. WebSocket Message Sending (every 60 seconds after DTU query)

**✅ SUCCESS - Should see:**
```
[Thread-X] INFO Successfully queried DTU in X.XXs - Found 37 inverters
[Thread-Y] INFO [WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
[Thread-Y] INFO [WebSocket] ✓ Successfully sent update to Home Assistant
```

**❌ PROBLEM - If you see:**
```
[Thread-X] INFO Successfully queried DTU...
[Thread-Y] INFO Successfully pushed data via WebSocket to 0 connections  # <-- 0 connections!
```
OR no "[WebSocket] Sending update" messages at all.

### C. API Polling (should NOT see this if WebSocket working)

**✅ WEBSOCKET WORKING - Should NOT see:**
```
[API Request] GET /api/inverters from 192.168.1.23
[API Request] GET /api/stats from 192.168.1.23
```

**❌ WEBSOCKET NOT WORKING - If you see these every minute:**
```
[API Request] GET /api/health from 192.168.1.23
[API Request] GET /api/stats from 192.168.1.23
[API Request] GET /api/inverters from 192.168.1.23
```
This means HA is falling back to polling because WebSocket isn't delivering data.

## Step 3: Check Home Assistant Logs

After bridge restart, check HA logs for:

### Initial Connection
```
[WebSocket Server] ✓ Connection established from bridge (192.168.1.191)
```

### Message Receipt (every 60 seconds)
```
[WebSocket Server] Processing update: 37 inverters, 74 ports
[WebSocket Server] ✓ Update processed successfully
[WebSocket Push] ✓ Received data from bridge: 37 inverters, 74 ports
[Push Data] Using pushed data from bridge (age: 2.3s, inverters: 37)
```

## Common Scenarios

### Scenario 1: WebSocket Connects But No Messages Sent

**Bridge Logs:**
```
✓ [WebSocket] ✓ Connected to: Home Assistant
✗ (no "Sending update" messages)
✓ Successfully pushed data via WebSocket to 1 connections
```

**Diagnosis:** The connection counter thinks there's a connection, but messages aren't being sent.

**Fix:** This is a bug in the WebSocket send logic. The connection may be established but not properly stored for sending.

### Scenario 2: WebSocket Never Connects

**Bridge Logs:**
```
✓ Registered WebSocket: Home Assistant
✗ Connection timeout or error
```

**Diagnosis:** Bridge cannot reach Home Assistant WebSocket endpoint.

**Fix:**
- Check firewall rules
- Verify HA is accessible from bridge: `curl -I http://192.168.1.23:8123`
- Check WebSocket URL in registration

### Scenario 3: WebSocket Connects, Sends, But HA Doesn't Process

**Bridge Logs:**
```
✓ [WebSocket] ✓ Connected to: Home Assistant
✓ [WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
✓ [WebSocket] ✓ Successfully sent update to Home Assistant
```

**HA Logs:**
```
✗ (no "WebSocket Server Processing update" messages)
✓ [Poll] No push data available, polling API
```

**Diagnosis:** Messages are sent but not received/processed by HA.

**Possible Causes:**
1. Message format incompatibility
2. WebSocket server not handling messages
3. Messages queued but not delivered

**Fix:** Enable DEBUG logging in HA to see raw messages.

### Scenario 4: Everything Looks Good But Still Polling

**Bridge Logs:**
```
✓ [WebSocket] ✓ Connected to: Home Assistant
✓ [WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
✓ [WebSocket] ✓ Successfully sent update to Home Assistant
```

**HA Logs:**
```
✓ [WebSocket Server] Processing update: 37 inverters, 74 ports
✓ [WebSocket Server] ✓ Update processed successfully
✓ [WebSocket Push] ✓ Received data from bridge: 37 inverters, 74 ports
✗ [Poll] No push data available, polling API  # <-- Still happens!
```

**Diagnosis:** Messages are processed but `_last_push_update` timestamp not being set correctly, or coordinator is checking before push arrives.

**Fix:** Check timing - the coordinator polls every 60s, push happens every 60s. They might be out of sync.

## Enable DEBUG Logging

### Bridge

Set in docker-compose.yml or environment:
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

### Home Assistant

In configuration.yaml:
```yaml
logger:
  default: warning
  logs:
    custom_components.hoymiles_smiles: debug
    custom_components.hoymiles_smiles.websocket_server: debug
```

## Manual WebSocket Test

Test the WebSocket connection manually:

```python
import asyncio
import aiohttp
import json

async def test_websocket():
    token = "yfw1KAcDFtmFYwHXIqPxwX0kgwIublg6WjPkV6Rxe5A"  # From bridge logs
    url = f"ws://192.168.1.23:8123/api/hoymiles_smiles/ws?token={token}"
    
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            print("Connected!")
            
            # Send test message
            await ws.send_json({
                "type": "update",
                "data": {
                    "health": {},
                    "stats": {},
                    "inverters": [{"serial_number": "TEST", "ports": []}]
                }
            })
            print("Sent test update")
            
            # Wait for response
            async for msg in ws:
                print(f"Received: {msg.data}")
                break

asyncio.run(test_websocket())
```

## Next Steps Based on Logs

After restart, report what you see in logs and I'll provide specific fix based on the scenario.

**Key Questions:**
1. Does "[WebSocket] ✓ Connected" appear in bridge logs?
2. Does "[WebSocket] Sending update" appear every 60 seconds in bridge logs?
3. Does "[WebSocket Server] Processing update" appear in HA logs?
4. Do you see API request logs in bridge logs?

The answers to these 4 questions will pinpoint exactly where the issue is.

