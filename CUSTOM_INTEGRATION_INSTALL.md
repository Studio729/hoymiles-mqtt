# Hoymiles MQTT Custom Integration - Installation Guide

## 🎉 Custom Home Assistant Integration

This is a **native Home Assistant integration** for monitoring your Hoymiles MQTT Bridge. It appears in the Home Assistant UI just like any official integration!

---

## 📦 What You Get

### ✅ Native UI Configuration
- Configure through Home Assistant UI (no YAML editing required)
- Appears in Settings → Devices & Services
- Easy setup wizard

### ✅ 8 Sensor Entities
1. **Uptime** - Application uptime in seconds
2. **MQTT Messages Published** - Total messages sent
3. **MQTT Errors** - Total MQTT errors
4. **DTU Query Count** - Total DTU queries
5. **DTU Error Count** - Total DTU errors  
6. **DTU Last Query** - Seconds since last successful query
7. **Database Size** - SQLite database size (MB)
8. **Cached Records** - Number of cached records

### ✅ 1 Binary Sensor
- **Application Healthy** - Overall health status (on/off)

### ✅ Device Integration
- All entities grouped under one device
- Device info with model, manufacturer, version
- Easy management in device registry

---

## 📋 Prerequisites

- ✅ Home Assistant 2024.2 or newer
- ✅ Hoymiles MQTT application running with health endpoint enabled (`HEALTH_ENABLED: true`)
- ✅ Health API accessible from Home Assistant

---

## 🚀 Installation Methods

### Method 1: Manual Installation (Recommended)

#### Step 1: Copy Files

Copy the entire `custom_components/hoymiles_smiles/` directory to your Home Assistant `config` directory:

```bash
# Option A: Using SSH/SCP
scp -r custom_components/hoymiles_smiles/ root@homeassistant:/config/custom_components/

# Option B: Using File Editor Add-on
# Upload folder through Home Assistant File Editor

# Option C: Direct copy (if you have access)
cp -r custom_components/hoymiles_smiles/ /config/custom_components/
```

Your directory structure should look like:
```
/config/
├── configuration.yaml
└── custom_components/
    └── hoymiles_smiles/
        ├── __init__.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        └── .translations/
            └── en.json
```

#### Step 2: Restart Home Assistant

**Settings → System → Restart**

#### Step 3: Add Integration

1. Go to **Settings → Devices & Services**
2. Click **+ ADD INTEGRATION** (bottom right)
3. Search for **"Hoymiles MQTT Bridge"**
4. Click on it
5. Enter your details:
   - **Host**: Your Docker host IP (e.g., `192.168.1.31`)
   - **Port**: Health API port (e.g., `8090`)
6. Click **Submit**

✅ Done! The integration will appear with all sensors.

---

### Method 2: Using HACS (If Available)

If you want to make this available through HACS:

1. Create a GitHub repository with this integration
2. Add it as a custom repository in HACS
3. Install through HACS interface

---

## ⚙️ Configuration

### Initial Setup

When adding the integration, you'll be prompted for:

| Field | Description | Example |
|-------|-------------|---------|
| **Host** | IP address of Hoymiles MQTT container | `192.168.1.31` |
| **Port** | Health API port | `8090` |

### Options (After Setup)

Click **CONFIGURE** on the integration to adjust:

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| **Scan Interval** | How often to poll API (seconds) | `60` | `10-300` |

---

## 📊 Entities Created

After installation, you'll have these entities:

### Sensors

| Entity ID | Name | Unit | Description |
|-----------|------|------|-------------|
| `sensor.hoymiles_smiles_bridge_uptime` | Uptime | s | Application uptime |
| `sensor.hoymiles_smiles_bridge_mqtt_messages_push via WebSocket Messages Published | - | Total messages sent |
| `sensor.hoymiles_smiles_bridge_mqtt_errors` | MQTT Errors | - | Total MQTT errors |
| `sensor.hoymiles_smiles_bridge_dtu_query_count` | DTU Query Count | queries | Total DTU queries |
| `sensor.hoymiles_smiles_bridge_dtu_error_count` | DTU Error Count | errors | Total DTU errors |
| `sensor.hoymiles_smiles_bridge_dtu_last_query` | DTU Last Query | s | Time since last query |
| `sensor.hoymiles_smiles_bridge_database_size` | Database Size | MB | Database file size |
| `sensor.hoymiles_smiles_bridge_cached_records` | Cached Records | records | Cached record count |

### Binary Sensors

| Entity ID | Name | Description |
|-----------|------|-------------|
| `binary_sensor.hoymiles_smiles_bridge_application_healthy` | Application Healthy | Overall health (on/off) |

### Device

All entities are grouped under one device:
- **Name**: Hoymiles MQTT Bridge
- **Manufacturer**: Hoymiles
- **Model**: MQTT Bridge
- **Software Version**: 0.12.0

---

## 🎨 Dashboard Examples

### Quick Glance Card

```yaml
type: entities
title: Hoymiles MQTT Bridge
entities:
  - entity: binary_sensor.hoymiles_smiles_bridge_application_healthy
    name: Status
  - entity: sensor.hoymiles_smiles_bridge_uptime
    name: Uptime
  - entity: sensor.hoymiles_smiles_bridge_dtu_last_query
    name: Last Query
  - entity: sensor.hoymiles_smiles_bridge_mqtt_messages_published
    name: Messages
  - entity: sensor.hoymiles_smiles_bridge_mqtt_errors
    name: Errors
```

### Gauge Card (Query Health)

```yaml
type: gauge
entity: sensor.hoymiles_smiles_bridge_dtu_last_query
name: Query Freshness
unit: seconds
min: 0
max: 600
severity:
  green: 0
  yellow: 300
  red: 420
```

### Statistics Card

```yaml
type: statistics-graph
title: MQTT Messages
entities:
  - sensor.hoymiles_smiles_bridge_mqtt_messages_published
stat_types:
  - mean
  - change
period: day
```

---

## 🔔 Automation Examples

### Alert on Unhealthy Status

```yaml
automation:
  - id: hoymiles_unhealthy_alert
    alias: "Hoymiles MQTT - Unhealthy Alert"
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.hoymiles_smiles_bridge_application_healthy
        to: "off"
        for:
          minutes: 2
    action:
      - action: notify.mobile_app_iphone
        data:
          title: "⚠️ Solar Monitor Unhealthy"
          message: "Hoymiles MQTT Bridge is unhealthy"
```

### Alert on High Errors

```yaml
automation:
  - id: hoymiles_high_errors
    alias: "Hoymiles MQTT - High Error Rate"
    mode: single
    trigger:
      - platform: numeric_state
        entity_id: sensor.hoymiles_smiles_bridge_mqtt_errors
        above: 10
    action:
      - action: persistent_notification.create
        data:
          title: "High Error Rate"
          message: "Hoymiles MQTT has {{ states('sensor.hoymiles_smiles_bridge_mqtt_errors') }} errors"
```

---

## 🔧 Troubleshooting

### Integration Not Showing Up

**Problem:** Can't find "Hoymiles MQTT Bridge" in integration list

**Solutions:**
1. Verify files are in `/config/custom_components/hoymiles_smiles/`
2. Check Home Assistant logs for errors
3. Restart Home Assistant again
4. Clear browser cache

### "Cannot Connect" Error During Setup

**Problem:** Setup wizard shows "Cannot connect" error

**Solutions:**

1. **Verify endpoint is accessible:**
   ```bash
   # From HA container
   docker exec homeassistant curl http://192.168.1.31:8090/health
   ```

2. **Check Hoymiles MQTT is running:**
   ```bash
   docker ps | grep hoymiles_smiles
   docker logs hoymiles_smiles | grep "Health check server"
   ```

3. **Verify health server is enabled:**
   Check `docker-compose.yml`:
   ```yaml
   environment:
     HEALTH_ENABLED: true
     HEALTH_PORT: 8090
   ```

4. **Check network connectivity:**
   - Use same network mode (host or bridge)
   - Verify firewall rules
   - Test from HA host machine

### Sensors Show "Unavailable"

**Problem:** Entities exist but show "unavailable"

**Solutions:**

1. **Check coordinator updates:**
   - Go to **Settings → System → Logs**
   - Filter for "hoymiles_smiles"
   - Look for connection errors

2. **Verify API is responding:**
   ```bash
   curl http://192.168.1.31:8090/health
   curl http://192.168.1.31:8090/stats
   ```

3. **Check scan interval:**
   - Go to integration
   - Click **CONFIGURE**
   - Increase scan interval if needed

### Integration Won't Load After Update

**Problem:** Integration stops working after HA update

**Solutions:**

1. **Check compatibility:**
   - Requires HA 2024.2+
   - Check release notes

2. **Clear cache:**
   ```bash
   # Restart HA in safe mode
   # Then restart normally
   ```

3. **Check logs:**
   - **Settings → System → Logs**
   - Look for Python errors

---

## 🔄 Updating the Integration

### Manual Update

1. Stop Home Assistant (optional)
2. Replace files in `/config/custom_components/hoymiles_smiles/`
3. Restart Home Assistant
4. Check logs for errors

### Via HACS (If Using)

1. Go to HACS
2. Click on Hoymiles MQTT Bridge
3. Click **Update**
4. Restart Home Assistant

---

## 🗑️ Uninstalling

### Step 1: Remove Integration

1. **Settings → Devices & Services**
2. Find **Hoymiles MQTT Bridge**
3. Click ⋮ (three dots)
4. Click **Delete**

### Step 2: Remove Files

```bash
rm -rf /config/custom_components/hoymiles_smiles/
```

### Step 3: Restart Home Assistant

---

## 📚 Additional Resources

### Documentation
- **Main README**: `README.md`
- **YAML Configuration**: `home_assistant_sensors.yaml` (alternative approach)
- **Custom Integration Guide**: `CUSTOM_INTEGRATION_GUIDE.md`
- **Health API Docs**: `WEB_SERVER_CONFIG.md`

### Home Assistant Resources
- [Integration Development](https://developers.home-assistant.io/docs/development_index/)
- [Data Update Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)

---

## 🎯 Advantages Over YAML Configuration

| Feature | Custom Integration | YAML Config |
|---------|-------------------|-------------|
| **UI Setup** | ✅ Yes | ❌ No (manual YAML) |
| **Device Registry** | ✅ Yes | ❌ No |
| **Entity Registry** | ✅ Yes | ⚠️ Partial |
| **Options Flow** | ✅ Yes (scan interval) | ❌ No |
| **Easy Updates** | ✅ Yes | ⚠️ Manual |
| **Grouped Entities** | ✅ Yes (under device) | ❌ No |
| **Native Experience** | ✅ Yes | ⚠️ Basic |

---

## ✅ Quick Verification

After installation, verify:

- [ ] Integration appears in **Settings → Devices & Services**
- [ ] Device "Hoymiles MQTT Bridge" is present
- [ ] All 9 entities are created (8 sensors + 1 binary sensor)
- [ ] `binary_sensor.hoymiles_smiles_bridge_application_healthy` shows correct state
- [ ] Sensors are updating (not "unavailable")
- [ ] No errors in Home Assistant logs
- [ ] Can add entities to dashboard

If all checked: **Installation successful! 🎉**

---

## 🆘 Getting Help

1. **Check logs**: Settings → System → Logs
2. **Test API**: `curl http://YOUR_IP:8090/health`
3. **Verify files**: Check all files are in `custom_components/hoymiles_smiles/`
4. **Review config**: Settings → Devices & Services → Hoymiles MQTT Bridge

---

## 📝 Summary

✅ **Native Home Assistant integration**
✅ **UI-based configuration**
✅ **9 entities (8 sensors + 1 binary sensor)**
✅ **Device registry integration**
✅ **Configurable scan interval**
✅ **Professional appearance**
✅ **Easy to use and maintain**

**Enjoy your native Home Assistant integration!** 🚀

