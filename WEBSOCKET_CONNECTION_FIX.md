# WebSocket Connection Fix - FINAL

## What the Logs Revealed

Your bridge logs show the exact problem:

```
✓ Registered WebSocket: Home Assistant
✓ Connecting to WebSocket: Home Assistant (ws://192.168.1.23:8123/...)
✗ [NEVER APPEARS] [WebSocket] ✓ Connected to: Home Assistant
✓ Successfully pushed data via WebSocket to 0 connections  <-- 0 because not connected!
```

**The bridge is trying to connect but the connection is failing silently!**

## The Root Cause

The `ws_connect()` call is timing out (60 second timeout) but the error isn't being logged properly. The connection attempt hangs and eventually times out, but the code wasn't catching and logging the error correctly.

## What I Fixed

### Better Error Handling & Logging

**Changed** (`hoymiles_smiles/websocket_client.py`):
1. **Added explicit error handling** for WebSocket connection failures
2. **Reduced timeout** from 60s to 10s for faster retry
3. **Added warning logs** when connection fails showing the exact error
4. **Fixed exception handling** so errors are properly caught and logged

Now when connection fails, you'll see:
```
[WebSocket] Connection failed for Home Assistant: [error details] (attempt 1)
```

And it will retry with exponential backoff.

## Why It's Failing

The WebSocket is failing to connect because **Home Assistant's WebSocket endpoint might not be ready yet** when the bridge tries to connect, OR there's a network/firewall issue.

## Next Step: Restart & Check Logs

### Step 1: Restart Bridge
```bash
docker-compose restart
```

### Step 2: Watch Logs
```bash
docker-compose logs -f hoymiles-smiles | grep -i websocket
```

### What You Should See

**Scenario A: Connection Succeeds** (GOOD!)
```
[WebSocket] Connecting to Home Assistant (ws://192.168.1.23:8123/...)
[WebSocket] ✓ Connected to: Home Assistant
[WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
[WebSocket] ✓ Successfully sent update to Home Assistant
```

**Scenario B: Connection Fails** (shows the error now!)
```
[WebSocket] Connecting to Home Assistant (ws://192.168.1.23:8123/...)
[WebSocket] Connection failed for Home Assistant: Cannot connect to host 192.168.1.23:8123 ... (attempt 1)
[WebSocket] Reconnecting to Home Assistant in 1 seconds (attempt 2)...
[WebSocket] Connecting to Home Assistant (ws://192.168.1.23:8123/...)
[WebSocket] Connection failed for Home Assistant: ... (attempt 2)
```

## If You See Scenario B (Connection Failures)

### Common Error Messages & Fixes

**Error: "Cannot connect to host"**
- **Cause:** Bridge can't reach Home Assistant
- **Fix:** Check network connectivity: `docker exec hoymiles-smiles ping 192.168.1.23`

**Error: "Connection refused"**
- **Cause:** Home Assistant not accepting connections on port 8123
- **Fix:** Verify HA is running: `curl http://192.168.1.23:8123`

**Error: "Timeout"**
- **Cause:** Firewall blocking or HA overloaded
- **Fix:** Check firewall rules, check HA system load

**Error: "401 Unauthorized" or "403 Forbidden"**
- **Cause:** Token authentication failing
- **Fix:** This shouldn't happen with token in URL, but check WebSocket server setup

**Error: "404 Not Found"**
- **Cause:** WebSocket endpoint doesn't exist
- **Fix:** Verify custom component loaded properly in HA logs

### If No Errors But Still No Connection

If you see:
```
[WebSocket] Connecting to Home Assistant ...
(then nothing - no success, no error)
```

This means the connection is hanging. Possible causes:
1. **Network issue** - packets being dropped silently
2. **Proxy/Load balancer** - something between bridge and HA interfering
3. **DNS issue** - IP resolves but connection hangs

**Debug:**
```bash
# Test connectivity from bridge container
docker exec hoymiles-smiles telnet 192.168.1.23 8123

# Test WebSocket directly
docker exec hoymiles-smiles wget -O- http://192.168.1.23:8123/api/hoymiles_smiles/ws?token=...
```

## Alternative: Use Polling Mode

If WebSocket continues to fail, the integration will fall back to polling mode automatically. This works but:
- ❌ More API calls (3 per minute vs 0)
- ❌ Slightly higher load
- ✅ But sensors will still work and update!

The polling fallback uses the enriched `/api/inverters` endpoint now, so it includes all data (readings + ports).

## Success Criteria

After restart, within 2 minutes you should see **ONE** of these:

**SUCCESS Path:**
```
[WebSocket] ✓ Connected to: Home Assistant
[WebSocket] Sending update to Home Assistant: 37 inverters, 74 ports
```
AND in Home Assistant logs:
```
[WebSocket Server] ✓ Connection established from bridge
[WebSocket Server] Processing update: 37 inverters, 74 ports
[WebSocket Push] ✓ Received data from bridge
```

**FALLBACK Path (if WebSocket fails):**
```
[WebSocket] Connection failed for Home Assistant: [error]
[API Request] GET /api/inverters from 192.168.1.23  <-- HA polling
```
Sensors will still work via polling!

## Report Back

After restart, please share:

1. **Do you see "[WebSocket] Connection failed" with an error message?**
   - If YES: Share the exact error message
   
2. **Do you see "[WebSocket] ✓ Connected to: Home Assistant"?**
   - If YES: Perfect! Check if you then see "Sending update" messages
   
3. **Do you see neither** (just "Connecting..." then nothing)?
   - If YES: Run the debug telnet/wget commands above

With this information, I can provide the exact fix for your specific situation!

