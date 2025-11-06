# Home Assistant Health Monitoring Setup

This guide shows you how to add health monitoring sensors for your Hoymiles MQTT application in Home Assistant.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Sensor Overview](#sensor-overview)
4. [Dashboard Setup](#dashboard-setup)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- ✅ Hoymiles MQTT application running with health endpoint enabled
- ✅ Health endpoint accessible from Home Assistant at `http://192.168.1.31:8090`
- ✅ **Home Assistant 2024.2 or newer** (uses latest standards)

> 📌 **Note:** Configuration uses Home Assistant 2024.x standards. See `HA_2024_STANDARDS.md` for details.

### Verify Health Endpoint

Before proceeding, verify the endpoint is accessible:

```bash
# From Home Assistant machine or Docker container
curl http://192.168.1.31:8090/health
```

You should see JSON response with health data.

---

## Installation Methods

### Method 1: Using Packages (Recommended)

This keeps your main `configuration.yaml` clean.

#### Step 1: Enable Packages

Edit `configuration.yaml` and add (if not already present):

```yaml
homeassistant:
  packages: !include_dir_named packages
```

#### Step 2: Create Package File

1. Create directory: `config/packages/`
2. Copy `home_assistant_sensors.yaml` to `config/packages/hoymiles_smiles.yaml`
3. Edit the file and update the IP address if needed:
   ```yaml
   resource: http://192.168.1.31:8090/health  # ← Update this
   ```

#### Step 3: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Or use the service: `homeassistant.restart`

---

### Method 2: Direct Configuration

Add directly to `configuration.yaml`.

#### Step 1: Backup Configuration

```bash
# Make a backup first
cp configuration.yaml configuration.yaml.backup
```

#### Step 2: Add Sensors

Open `configuration.yaml` and add the contents of `home_assistant_sensors.yaml`.

**Important:** Update the IP address:
```yaml
resource: http://YOUR_DOCKER_HOST_IP:8090/health
```

#### Step 3: Check Configuration

1. Go to **Developer Tools** → **YAML**
2. Click **Check Configuration**
3. Fix any errors shown

#### Step 4: Restart

Restart Home Assistant to load the new sensors.

---

### Method 3: Using File Editor Add-on

If you have the File Editor add-on:

1. **Settings** → **Add-ons** → **File editor**
2. Navigate to `config/` directory
3. Create new file: `packages/hoymiles_smiles.yaml`
4. Paste contents from `home_assistant_sensors.yaml`
5. Update IP address
6. Save and restart Home Assistant

---

## Sensor Overview

After installation, you'll have these sensors:

### Core Health Sensors

| Entity ID | Description | Updates |
|-----------|-------------|---------|
| `sensor.hoymiles_smiles_health_status` | Overall health (True/False) | 60s |
| `binary_sensor.hoymiles_smiles_healthy` | Binary health status | Real-time |
| `sensor.hoymiles_smiles_uptime` | Uptime in seconds | 60s |
| `sensor.hoymiles_smiles_uptime_formatted` | Human-readable uptime | 60s |

### MQTT Monitoring

| Entity ID | Description | Updates |
|-----------|-------------|---------|
| `sensor.hoymiles_smiles_messages_push via WebSocket messages sent | 60s |
| `sensor.hoymiles_smiles_errors` | Total MQTT errors | 60s |

### DTU Monitoring

| Entity ID | Description | Updates |
|-----------|-------------|---------|
| `sensor.hoymiles_dtu_status` | DTU connection status | 60s |
| `sensor.hoymiles_dtu_last_query` | Seconds since last query | 60s |
| `sensor.hoymiles_dtu_query_count` | Total queries executed | 60s |
| `sensor.hoymiles_dtu_error_count` | Total query errors | 60s |

### Database Stats

| Entity ID | Description | Updates |
|-----------|-------------|---------|
| `sensor.hoymiles_smiles_database_size` | Database size in MB | 5min |
| `sensor.hoymiles_smiles_cached_records` | Number of cached records | 5min |

---

## Dashboard Setup

### Quick Glance Card

Add this to your dashboard:

```yaml
type: entities
title: Hoymiles MQTT Health
entities:
  - entity: binary_sensor.hoymiles_smiles_healthy
    name: Status
  - entity: sensor.hoymiles_smiles_uptime_formatted
    name: Uptime
  - entity: sensor.hoymiles_dtu_status
    name: DTU Status
  - entity: sensor.hoymiles_dtu_last_query
    name: Last Query
    secondary_info: relative-time
  - entity: sensor.hoymiles_smiles_messages_published
    name: Messages Published
  - entity: sensor.hoymiles_smiles_errors
    name: Errors
```

### Detailed Monitoring Card

```yaml
type: vertical-stack
cards:
  - type: entities
    title: 🏥 Health Status
    entities:
      - entity: binary_sensor.hoymiles_smiles_healthy
        name: Application Health
      - entity: sensor.hoymiles_smiles_uptime_formatted
        name: Uptime
      - type: divider
      - entity: sensor.hoymiles_dtu_status
        name: DTU Connection
      - entity: sensor.hoymiles_dtu_last_query
        name: Last Query
        icon: mdi:clock-outline
      - entity: sensor.hoymiles_dtu_query_count
        name: Total Queries
      - entity: sensor.hoymiles_dtu_error_count
        name: Query Errors

  - type: entities
    title: 📊 MQTT Statistics
    entities:
      - entity: sensor.hoymiles_smiles_messages_published
        name: Messages Published
        icon: mdi:message-arrow-right
      - entity: sensor.hoymiles_smiles_errors
        name: MQTT Errors
        icon: mdi:alert-circle

  - type: entities
    title: 💾 Database
    entities:
      - entity: sensor.hoymiles_smiles_database_size
        name: Database Size
      - entity: sensor.hoymiles_smiles_cached_records
        name: Cached Records
```

### History Graph Card

Track metrics over time:

```yaml
type: history-graph
title: Hoymiles MQTT Performance
hours_to_show: 24
entities:
  - entity: sensor.hoymiles_dtu_last_query
    name: Query Age
  - entity: sensor.hoymiles_smiles_messages_published
    name: Messages
  - entity: sensor.hoymiles_dtu_error_count
    name: Errors
```

### Statistics Card

```yaml
type: statistic
entity: sensor.hoymiles_smiles_uptime
name: Application Uptime
stat_type: mean
period:
  calendar:
    period: day
```

### Gauge Card (Query Health)

```yaml
type: gauge
entity: sensor.hoymiles_dtu_last_query
name: Time Since Last Query
unit: seconds
min: 0
max: 600
severity:
  green: 0
  yellow: 300
  red: 420
needle: true
```

---

## Automations

The configuration includes these automations using **2024.x standards**:

> 📌 **What's New:** Automations now use `action:` instead of `service:` (2024.x standard), include `mode:` parameter, and have robust error handling.

### 1. Unhealthy Alert

Triggers when application becomes unhealthy for 2+ minutes.

**Customize:**
```yaml
action:
  - action: notify.mobile_app_your_phone  # ← Change this (uses 2024.x 'action:' syntax)
    data:
      title: "Hoymiles MQTT Unhealthy"
      message: "Check your solar monitoring"
```

### 2. High Error Rate

Triggers when 5+ errors occur quickly.

### 3. Restart Notification

Notifies you when the application restarts.

---

## Advanced Configuration

### Change Update Frequency

Edit the `scan_interval` values:

```yaml
rest:
  - resource: http://192.168.1.31:8090/health
    scan_interval: 30  # ← Change from 60 to 30 seconds
```

**Note:** Lower values = more frequent updates = more HTTP requests.

### Add Custom Attributes

Extract more data from the health endpoint:

```yaml
template:
  - sensor:
      - name: "Hoymiles DTU Last Error"
        unique_id: hoymiles_dtu_last_error
        state: >-
          {% set dtus = state_attr('sensor.hoymiles_smiles_health_status', 'dtus') %}
          {% if dtus and dtus.DTU and dtus.DTU.last_error %}
            {{ dtus.DTU.last_error }}
          {% else %}
            none
          {% endif %}
        icon: mdi:alert
```

### Monitor Multiple DTUs

If you have multiple DTUs configured:

```yaml
template:
  - sensor:
      - name: "Hoymiles DTU2 Status"
        unique_id: hoymiles_dtu2_status
        state: >-
          {% set dtus = state_attr('sensor.hoymiles_smiles_health_status', 'dtus') %}
          {% if dtus and dtus.DTU2 %}
            {{ dtus.DTU2.status | default('unknown') }}
          {% else %}
            unknown
          {% endif %}
```

---

## Troubleshooting

### Sensors Show "Unknown"

**Problem:** Sensors not updating or showing "unknown"

**Solutions:**

1. **Check endpoint accessibility:**
   ```bash
   # From HA container
   docker exec homeassistant curl http://192.168.1.31:8090/health
   ```

2. **Check HA logs:**
   - **Settings** → **System** → **Logs**
   - Look for "rest" or "RESTful" errors

3. **Verify IP address in config**
4. **Check firewall rules**

### "Connection Refused" Errors

**Problem:** Cannot connect to health endpoint

**Solutions:**

1. **Verify Hoymiles MQTT is running:**
   ```bash
   docker ps | grep hoymiles_smiles
   ```

2. **Check health server is listening:**
   ```bash
   docker exec hoymiles_smiles netstat -tuln | grep 8090
   ```

3. **Test from HA host:**
   ```bash
   curl http://192.168.1.31:8090/ready
   ```

### Binary Sensor Always "Off"

**Problem:** `binary_sensor.hoymiles_smiles_healthy` shows unavailable

**Solution:** This depends on `sensor.hoymiles_smiles_health_status`. Check that sensor first.

### Template Errors

**Problem:** Template sensors show errors

**Solutions:**

1. **Developer Tools** → **Template**
2. Paste template and test:
   ```jinja
   {% set dtus = state_attr('sensor.hoymiles_smiles_health_status', 'dtus') %}
   {{ dtus }}
   ```
3. Check if attribute exists

### High Resource Usage

**Problem:** Too many REST requests

**Solutions:**

1. Increase `scan_interval`:
   ```yaml
   scan_interval: 120  # Check every 2 minutes instead of 1
   ```

2. Remove sensors you don't need

---

## Example Dashboard Screenshot

After setup, your dashboard could look like this:

```
┌─────────────────────────────────────┐
│    Hoymiles MQTT Health             │
├─────────────────────────────────────┤
│ ✓ Status            Healthy         │
│ ⏱ Uptime            2d 14h 23m      │
│ 🔌 DTU Status       connected       │
│ 🕐 Last Query       45s ago         │
│ 📤 Messages         125,847         │
│ ⚠ Errors            3               │
└─────────────────────────────────────┘
```

---

## Next Steps

1. ✅ **Test**: Verify all sensors are updating
2. ✅ **Customize**: Adjust automations for your notification preferences
3. ✅ **Dashboard**: Create cards to visualize the data
4. ✅ **Monitor**: Watch for alerts and adjust thresholds

---

## Support

- **Health Endpoint Docs**: See `WEB_SERVER_CONFIG.md`
- **Issues**: Check Hoymiles MQTT logs
- **Testing**: Use Developer Tools → Template editor

---

## Quick Verification Checklist

After installation, verify:

- [ ] `sensor.hoymiles_smiles_health_status` shows "True"
- [ ] `sensor.hoymiles_smiles_uptime` is counting up
- [ ] `binary_sensor.hoymiles_smiles_healthy` shows "on"
- [ ] `sensor.hoymiles_dtu_status` shows "connected"
- [ ] `sensor.hoymiles_smiles_messages_published` is increasing
- [ ] No errors in Home Assistant logs
- [ ] Dashboard card displays correctly

If all checked, you're successfully monitoring your Hoymiles MQTT application! 🎉

