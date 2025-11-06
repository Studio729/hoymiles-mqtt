# Home Assistant Integration - Comparison Guide

## 🤔 Which Approach Should You Use?

You have **two options** for integrating Hoymiles MQTT Bridge with Home Assistant:

1. **YAML Configuration** - Simple REST sensors
2. **Custom Integration** - Native Python integration

This guide helps you choose the best option for your needs.

---

## 📊 Quick Comparison

| Feature | YAML Config | Custom Integration |
|---------|-------------|-------------------|
| **Setup Difficulty** | Medium | Easy |
| **Configuration Method** | Edit YAML files | UI wizard |
| **Appearance in HA** | Scattered entities | Grouped under device |
| **Updates/Changes** | Edit YAML + restart | Click Configure button |
| **Visual Polish** | Basic | Professional |
| **Performance** | Good | Better (optimized) |
| **Installation** | Copy/paste to config | Copy folder + UI setup |
| **Learning Curve** | YAML/Jinja2 | Just use it |
| **Maintenance** | Manual | Automatic |

---

## 🎯 Decision Tree

### Choose **YAML Configuration** If:

✅ You're **comfortable with YAML**
✅ You want **minimal installation** (just paste config)
✅ You prefer **everything in configuration files**
✅ You're already familiar with **REST and template sensors**
✅ You want to **see the exact logic** in YAML
✅ You need to **customize templates heavily**
✅ You want **full control** over every detail

**→ Use:** `home_assistant_sensors.yaml`

---

### Choose **Custom Integration** If:

✅ You want a **professional, native experience**
✅ You prefer **UI-based configuration**
✅ You want **all entities grouped under one device**
✅ You don't want to edit YAML files
✅ You want **easy updates** via UI
✅ You're not comfortable with Jinja2 templates
✅ You want the **"official integration" feel**
✅ You plan to **share this with others** who aren't technical

**→ Use:** `custom_components/hoymiles_smiles/`

---

## 📝 Detailed Comparison

### 1. Installation Process

#### YAML Configuration
```bash
# 1. Edit configuration.yaml
homeassistant:
  packages: !include_dir_named packages

# 2. Copy sensor file
cp home_assistant_sensors.yaml /config/packages/hoymiles_smiles.yaml

# 3. Edit IP address in file
nano /config/packages/hoymiles_smiles.yaml

# 4. Restart Home Assistant
```

**Time:** ~5 minutes
**Difficulty:** Medium (need SSH/file access)

#### Custom Integration
```bash
# 1. Copy integration folder
cp -r custom_components/hoymiles_smiles/ /config/custom_components/

# 2. Restart Home Assistant

# 3. Add integration via UI
Settings → Devices & Services → Add Integration → Hoymiles MQTT Bridge

# 4. Enter IP and port in form
```

**Time:** ~5 minutes
**Difficulty:** Easy (mostly UI)

---

### 2. Configuration Changes

#### YAML Configuration

**Changing IP Address:**
```yaml
# Edit file
nano /config/packages/hoymiles_smiles.yaml

# Change line 7
resource: "http://192.168.1.50:8090/health"  # New IP

# Restart HA
```

**Changing Scan Interval:**
```yaml
# Edit scan_interval in file
scan_interval: 30  # Change from 60 to 30

# Restart HA
```

**Time per change:** ~2-3 minutes + restart

#### Custom Integration

**Changing Anything:**
1. Settings → Devices & Services
2. Find "Hoymiles MQTT Bridge"
3. Click "CONFIGURE"
4. Change settings in form
5. Click Submit (auto-reload)

**Time per change:** ~30 seconds

---

### 3. User Interface

#### YAML Configuration

**In Home Assistant:**
```
Developer Tools → States

sensor.hoymiles_smiles_health_status
sensor.hoymiles_smiles_uptime
sensor.hoymiles_smiles_uptime_formatted
sensor.hoymiles_dtu_status
...
(11 separate entities, not grouped)
```

**Entity IDs:** Based on sensor names in YAML

#### Custom Integration

**In Home Assistant:**
```
Settings → Devices & Services → Hoymiles MQTT Bridge

Device: Hoymiles MQTT Bridge
├── binary_sensor.hoymiles_smiles_bridge_application_healthy
├── sensor.hoymiles_smiles_bridge_uptime
├── sensor.hoymiles_smiles_bridge_mqtt_messages_published
├── sensor.hoymiles_smiles_bridge_mqtt_errors
├── sensor.hoymiles_smiles_bridge_dtu_query_count
├── sensor.hoymiles_smiles_bridge_dtu_error_count
├── sensor.hoymiles_smiles_bridge_dtu_last_query
├── sensor.hoymiles_smiles_bridge_database_size
└── sensor.hoymiles_smiles_bridge_cached_records
```

**Entity IDs:** Automatically generated, consistent

---

### 4. Entities Created

#### YAML Configuration (11 entities)

**Sensors:**
1. `sensor.hoymiles_smiles_health_status` - Raw health (True/False)
2. `sensor.hoymiles_smiles_uptime` - Uptime (seconds)
3. `sensor.hoymiles_smiles_uptime_formatted` - Uptime (human readable)
4. `sensor.hoymiles_dtu_status` - DTU status text
5. `sensor.hoymiles_dtu_last_query` - Seconds since last query
6. `sensor.hoymiles_dtu_query_count` - Total queries
7. `sensor.hoymiles_dtu_error_count` - Total errors
8. `sensor.hoymiles_smiles_messages_push via WebSocket messages
9. `sensor.hoymiles_smiles_errors` - MQTT errors
10. `sensor.hoymiles_smiles_database_size` - Database size
11. `sensor.hoymiles_smiles_cached_records` - Cached records

**Binary Sensors:**
- `binary_sensor.hoymiles_smiles_healthy` - On/Off status

#### Custom Integration (9 entities)

**Sensors:**
1. `sensor.hoymiles_smiles_bridge_uptime` - Uptime with start_time attribute
2. `sensor.hoymiles_smiles_bridge_mqtt_messages_push via WebSocket messages
3. `sensor.hoymiles_smiles_bridge_mqtt_errors` - MQTT errors
4. `sensor.hoymiles_smiles_bridge_dtu_query_count` - Queries with status attribute
5. `sensor.hoymiles_smiles_bridge_dtu_error_count` - Errors with last error attribute
6. `sensor.hoymiles_smiles_bridge_dtu_last_query` - Time with timestamp attribute
7. `sensor.hoymiles_smiles_bridge_database_size` - Database size (diagnostic)
8. `sensor.hoymiles_smiles_bridge_cached_records` - Records (diagnostic)

**Binary Sensors:**
- `binary_sensor.hoymiles_smiles_bridge_application_healthy` - Health with rich attributes

**Note:** Custom integration uses attributes more, resulting in fewer but richer entities.

---

### 5. Performance

#### YAML Configuration

**Update Process:**
```
Timer triggers
 ↓
REST sensor fetches /health (separate HTTP request)
 ↓
REST sensor fetches /stats (separate HTTP request)
 ↓
Template sensors process data
 ↓
States updated
```

**Efficiency:** Good, but 2 separate HTTP requests every scan interval

#### Custom Integration

**Update Process:**
```
Coordinator timer triggers
 ↓
Single batch: fetch /health AND /stats together
 ↓
Data stored in coordinator
 ↓
All entities read from coordinator (no extra requests)
 ↓
States updated atomically
```

**Efficiency:** Better, optimized with DataUpdateCoordinator

---

### 6. Error Handling

#### YAML Configuration

**When API is down:**
- Sensors show "unavailable" (with proper availability templates)
- Template errors can occur if not handled carefully
- Need manual error checking in templates

**Example:**
```yaml
value_template: "{{ value_json.uptime_seconds | int(0) }}"
availability: "{{ value_json.uptime_seconds is defined }}"
```

#### Custom Integration

**When API is down:**
- Coordinator handles errors automatically
- All entities show "unavailable" together
- Retry logic built-in
- Logs errors properly

**Example:**
```python
try:
    data = await self._fetch_endpoint(session, ENDPOINT_HEALTH)
except aiohttp.ClientError as err:
    raise UpdateFailed(f"Error: {err}") from err
```

---

### 7. Maintenance & Updates

#### YAML Configuration

**Updating:**
1. Download new `home_assistant_sensors.yaml`
2. Replace your file
3. Re-apply customizations (IP address, etc.)
4. Restart Home Assistant

**Breaking Changes:**
- Need to manually update syntax when HA changes
- Must track Home Assistant breaking changes

#### Custom Integration

**Updating:**
1. Replace files in `custom_components/hoymiles_smiles/`
2. Restart Home Assistant
3. Settings preserved automatically

**Breaking Changes:**
- Integration maintainer handles compatibility
- You just update files

---

### 8. Customization

#### YAML Configuration

**Flexibility:** ⭐⭐⭐⭐⭐ (Maximum)

**Easy to customize:**
- Change sensor names
- Add custom templates
- Modify calculations
- Add new sensors
- Custom attributes
- Full Jinja2 power

**Example:**
```yaml
template:
  - sensor:
      - name: "My Custom Calculation"
        state: >
          {{ states('sensor.hoymiles_smiles_uptime') | int / 3600 | round(2) }}
        unit_of_measurement: "hours"
```

#### Custom Integration

**Flexibility:** ⭐⭐⭐ (Good, requires Python)

**Requires Python knowledge to:**
- Add new sensors (edit `sensor.py`)
- Change calculations (edit `coordinator.py`)
- Add attributes (edit entity descriptions)

**Example:**
```python
HoymilesMqttSensorEntityDescription(
    key="my_custom",
    name="My Custom Calculation",
    native_unit_of_measurement="hours",
    value_fn=lambda coord: coord.get_health_data().get("uptime_seconds") / 3600,
)
```

---

### 9. Sharing & Distribution

#### YAML Configuration

**Sharing:**
1. Share `home_assistant_sensors.yaml` file
2. User copies to their config
3. User edits IP address
4. User restarts HA

**Ease:** ⭐⭐⭐⭐ (Easy, single file)

#### Custom Integration

**Sharing:**
1. Share `custom_components/hoymiles_smiles/` folder
2. User copies to their config
3. User restarts HA
4. User adds via UI (enters IP)

**Ease:** ⭐⭐⭐⭐⭐ (Very easy, UI-guided)

**Or via HACS:**
1. Add repository to HACS
2. User installs via HACS
3. User adds via UI

---

### 10. Use Cases

#### YAML Configuration - Best For:

✅ **Power users** who want full control
✅ **Custom dashboards** with specific templates
✅ **Learning** how REST and templates work
✅ **Quick prototyping** of sensor logic
✅ **Heavily customized** installations
✅ **Version control** of configuration
✅ **Complex calculations** in templates

#### Custom Integration - Best For:

✅ **Regular users** who want "it just works"
✅ **Family members/friends** you're setting up for
✅ **Production deployments** that need stability
✅ **Less technical users** uncomfortable with YAML
✅ **Clean integration** experience
✅ **Multiple instances** (easy to manage)
✅ **Sharing with community** (more professional)

---

## 💡 Recommendations

### For Most Users: **Custom Integration** 🌟

**Why?**
- Easier to set up and maintain
- Professional appearance
- UI-based configuration
- Better for sharing with others
- Automatic error handling
- Grouped entities

### For Power Users: **YAML Configuration** ⚙️

**Why?**
- Maximum flexibility
- See exactly what's happening
- Easy to customize templates
- Can modify on-the-fly
- Good for learning
- Version control friendly

### For Both: **Try Both!** 🎯

They can coexist! Try:
1. Install YAML config first (quick)
2. Test and learn how it works
3. Install custom integration
4. Compare the experiences
5. Remove the one you don't want

---

## 🔄 Migration Path

### From YAML to Custom Integration

1. **Install custom integration** (don't remove YAML yet)
2. **Verify entities created** and working
3. **Update dashboards** to use new entity IDs
4. **Update automations** to use new entity IDs
5. **Test thoroughly**
6. **Remove YAML config** once confident

### From Custom Integration to YAML

1. **Copy `home_assistant_sensors.yaml`** to packages
2. **Update IP address**
3. **Restart HA** to create YAML entities
4. **Update dashboards** with new entity IDs
5. **Update automations** with new entity IDs
6. **Remove custom integration**

---

## 📊 Entity ID Mapping

If you switch between approaches:

| YAML Entity | Custom Integration Entity |
|-------------|--------------------------|
| `sensor.hoymiles_smiles_health_status` | `binary_sensor.hoymiles_smiles_bridge_application_healthy` |
| `sensor.hoymiles_smiles_uptime` | `sensor.hoymiles_smiles_bridge_uptime` |
| `sensor.hoymiles_smiles_messages_published` | `sensor.hoymiles_smiles_bridge_mqtt_messages_published` |
| `sensor.hoymiles_smiles_errors` | `sensor.hoymiles_smiles_bridge_mqtt_errors` |
| `sensor.hoymiles_dtu_query_count` | `sensor.hoymiles_smiles_bridge_dtu_query_count` |
| `sensor.hoymiles_dtu_error_count` | `sensor.hoymiles_smiles_bridge_dtu_error_count` |
| `sensor.hoymiles_dtu_last_query` | `sensor.hoymiles_smiles_bridge_dtu_last_query` |
| `sensor.hoymiles_smiles_database_size` | `sensor.hoymiles_smiles_bridge_database_size` |
| `sensor.hoymiles_smiles_cached_records` | `sensor.hoymiles_smiles_bridge_cached_records` |

**Note:** Entity IDs are different! Update your dashboards and automations.

---

## ✅ Final Recommendation

### **Start with Custom Integration** if you're unsure!

**Reasons:**
1. Easier setup (UI wizard)
2. Professional appearance
3. Better for long-term use
4. Easy to configure
5. Can always switch to YAML later if needed

**Try YAML only if:**
- You're very comfortable with YAML/templates
- You need heavy customization
- You prefer file-based configuration
- You want to learn how it works

---

## 📚 Documentation

### YAML Configuration
- **Setup**: `HOME_ASSISTANT_SETUP.md`
- **Quick Start**: `QUICK_START_HOME_ASSISTANT.md`
- **Standards**: `HA_2024_STANDARDS.md`
- **Config File**: `home_assistant_sensors.yaml`

### Custom Integration
- **Installation**: `CUSTOM_INTEGRATION_INSTALL.md`
- **Developer Guide**: `CUSTOM_INTEGRATION_GUIDE.md`
- **Files**: `custom_components/hoymiles_smiles/`

---

## 🎉 Summary

Both approaches work great! Choose based on:

| If you value... | Choose... |
|----------------|-----------|
| **Ease of use** | Custom Integration |
| **UI configuration** | Custom Integration |
| **Professional look** | Custom Integration |
| **Maximum flexibility** | YAML Configuration |
| **File-based config** | YAML Configuration |
| **Learning/customization** | YAML Configuration |

**Can't decide? Go with Custom Integration!** 🚀 It's easier and you can always switch later.

