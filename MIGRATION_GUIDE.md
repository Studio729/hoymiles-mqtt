# Migration Guide: Hoymiles MQTT to Hoymiles S-Miles v2.0

## Overview

Hoymiles S-Miles v2.0 represents a major architectural upgrade from the previous MQTT-based system to a database-centric architecture using PostgreSQL.

## Major Changes

### 1. Database Migration: SQLite → PostgreSQL
- **Old**: Data stored in local SQLite database `/data/hoymiles-smiles.db`
- **New**: Data stored in PostgreSQL database with configurable connection
- **Benefit**: Better scalability, concurrent access, and data integrity

### 2. MQTT Removal
- **Old**: Bridge push via WebSocket
- **New**: Bridge stores data in database, Home Assistant queries via REST API
- **Benefit**: Simpler architecture, no WebSocket needed, direct database access

### 3. Data Persistence
- **Old**: Some data treated as cache and periodically purged
- **New**: All data permanently stored (inverter readings, port data, metrics)
- **Benefit**: Complete historical data for analysis and trends

### 4. Component Rename
- **Old**: `hoymiles_smiles`
- **New**: `hoymiles_smiles`

## Migration Steps

### Step 1: Backup Your Data (Optional)
If you want to preserve historical data:
```bash
# Backup your SQLite database
cp data/hoymiles-smiles.db data/hoymiles-smiles.db.backup
```

### Step 2: Update Environment Variables
Remove MQTT-related variables and add database configuration:

**Remove:**
```bash
MQTT_BROKER=...
MQTT_PORT=...
MQTT_USER=...
MQTT_PASSWORD=...
MQTT_TLS=...
MQTT_CLIENT_ID=...
MQTT_TOPIC_PREFIX=...
DATABASE_PATH=/data/hoymiles-smiles.db
```

**Add:**
```bash
# Database Configuration
DB_TYPE=postgres
DB_HOST=postgres              # Use 'postgres' for docker service
DB_PORT=5432
DB_NAME=hoymiles
DB_USER=hoymiles
DB_PASSWORD=hoymiles_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# PostgreSQL Service (docker-compose)
POSTGRES_DB=hoymiles
POSTGRES_USER=hoymiles
POSTGRES_PASSWORD=hoymiles_password
POSTGRES_PORT=5432
```

### Step 3: Update Docker Compose
Use the new `docker-compose.yml` which includes PostgreSQL service:

```bash
docker-compose down
docker-compose up -d
```

The new setup includes:
- PostgreSQL 16 container
- Hoymiles S-Miles bridge (no MQTT dependency)
- Automatic database initialization

### Step 4: Update Home Assistant Custom Component
1. Remove old integration:
   - Go to Settings → Devices & Services
   - Remove "Hoymiles MQTT Bridge" integration

2. Delete old custom component:
   ```bash
   rm -rf /config/custom_components/hoymiles_smiles
   ```

3. Install new component:
   ```bash
   cp -r custom_components/hoymiles_smiles /config/custom_components/
   ```

4. Restart Home Assistant

5. Add new integration:
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Hoymiles S-Miles"
   - Enter bridge host and port (default: 8080)

### Step 5: Update Dependencies
If running outside Docker:
```bash
poetry install  # or
pip install -r requirements.txt
```

New dependencies:
- `psycopg2-binary` - PostgreSQL adapter
- `asyncpg` - Async PostgreSQL support

Removed dependencies:
- `paho-mqtt` - No longer needed

## Configuration Changes

### Database Configuration
```yaml
# Using Docker service (default)
DB_HOST: postgres
DB_PORT: 5432
DB_NAME: hoymiles
DB_USER: hoymiles
DB_PASSWORD: hoymiles_password

# Using external database
DB_HOST: your-postgres-server.com
DB_PORT: 5432
DB_NAME: hoymiles
DB_USER: your_user
DB_PASSWORD: your_password
```

### Port Configuration
- Health/API server: Port 8080 (unchanged)
- PostgreSQL: Port 5432 (exposed for external connections)

## API Endpoints

The bridge now exposes REST API endpoints for data access:

### Health & Monitoring
- `GET /health` - Health status
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Database statistics

### Data API
- `GET /api/inverters` - List all inverters
- `GET /api/inverters/{serial}` - Get latest inverter data
- `GET /api/inverters/{serial}/history?limit=100` - Get historical data
- `GET /api/inverters/{serial}/ports` - Get port data for inverter
- `GET /api/ports` - Get all port data
- `GET /api/production/current` - Get current production cache

## Database Schema

### New Tables
1. **inverters** - Inverter registry
2. **inverter_data** - All inverter readings (permanent)
3. **port_data** - All port/panel readings (permanent)
4. **production_cache** - Current production values
5. **config_cache** - Configuration storage
6. **system_metrics** - System metrics (permanent)

All historical data is retained permanently (no automatic purging).

## Breaking Changes

1. **Integration Name**: `hoymiles_smiles` → `hoymiles_smiles`
2. **Default Port**: Changed from 8090 to 8080
3. **Database**: SQLite → PostgreSQL (requires migration)
4. **MQTT**: Completely removed
5. **Data Retention**: All data now permanent

## Rollback Procedure

If you need to rollback to the old version:

1. Restore old docker-compose:
   ```bash
   git checkout HEAD~1 docker-compose.yml
   ```

2. Restore old environment variables

3. Restart containers:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. Reinstall old Home Assistant integration

## FAQ

**Q: Can I keep my historical SQLite data?**
A: The new version uses a different schema. If you need to migrate historical data, you'll need to write a custom migration script.

**Q: Can I use an external PostgreSQL database?**
A: Yes! Set `DB_HOST` to your PostgreSQL server address.

**Q: What happened to MQTT auto-discovery?**
A: No longer needed. The Home Assistant integration queries the bridge API directly.

**Q: Will my automation continue to work?**
A: Entity IDs will change (domain changed from `hoymiles_smiles` to `hoymiles_smiles`). Update your automations accordingly.

**Q: Can I still use Prometheus for monitoring?**
A: Yes! The `/metrics` endpoint still works.

## Support

For issues or questions:
- GitHub: https://github.com/hoymiles-smiles/hoymiles-smiles/issues
- Discussions: https://github.com/hoymiles-smiles/hoymiles-smiles/discussions

