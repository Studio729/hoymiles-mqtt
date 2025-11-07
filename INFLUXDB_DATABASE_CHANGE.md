# InfluxDB Database Name Change

## Issue

User reported data not showing in InfluxDB despite logs showing successful writes.

## Resolution

Changed InfluxDB database name from `hoymiles` to `main` in configuration.

## Why This Happened

The default database name in the code was set to `hoymiles`, but the user's InfluxDB instance uses `main` as the database name.

## How to Configure

### Option 1: Environment Variable
```env
INFLUXDB_DATABASE=main
```

### Option 2: Docker Compose
```yaml
environment:
  INFLUXDB_DATABASE: main
```

### Option 3: Command Line
```bash
--influxdb-database main
```

## Verifying Data

### Using SQL Queries

```sql
-- Check DTU data
SELECT time, dtu_name, pv_power, today_production
FROM dtu
WHERE time > now() - interval '1 hour'
ORDER BY time DESC
LIMIT 10;

-- Check inverter data
SELECT time, serial_number, temperature, grid_voltage
FROM inverter
WHERE time > now() - interval '1 hour'
ORDER BY time DESC;

-- Check port data
SELECT time, serial_number, port_number, pv_power
FROM port
WHERE time > now() - interval '1 hour'
ORDER BY time DESC;
```

### Using Python

```python
from influxdb_client_3 import InfluxDBClient3

client = InfluxDBClient3(
    host="https://influxdb3.suttonclan.org",
    token="your_token",
    database="main"  # Changed to 'main'
)

# Check record counts
for measurement in ['dtu', 'inverter', 'port']:
    result = client.query(f"SELECT COUNT(*) FROM {measurement}")
    print(f"{measurement}: {result.to_pandas()}")
```

## Important Notes

1. **InfluxDB v3 Uses Measurements, Not Tables**
   - `dtu` - DTU-level aggregated data
   - `inverter` - Per-inverter metrics
   - `port` - Per-port/panel metrics

2. **Don't Look for "Tables"**
   - InfluxDB v3 doesn't show traditional SQL tables
   - Use `SELECT * FROM <measurement>` to query data

3. **Time Range Matters**
   - If inverters are offline (nighttime), no new data is written
   - Use appropriate time ranges in queries

4. **Verify Configuration**
   - Check logs: `docker logs hoymiles-smiles | grep InfluxDB`
   - Should show: `InfluxDB writer initialized: https://influxdb3.suttonclan.org/main`

## Database Name Configuration Priority

1. Environment variable: `INFLUXDB_DATABASE`
2. Default in code: `hoymiles`

**Recommendation**: Always set explicitly in `.env` file to match your InfluxDB setup.

## Resolution Date

November 7, 2025

**Status**: ✅ Resolved - Data now visible in InfluxDB after database name change

