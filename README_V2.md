# Hoymiles S-Miles v2.0

> **Major Update**: Version 2.0 represents a complete architectural redesign, moving from MQTT-based communication to a database-centric approach with PostgreSQL.

## What's New in v2.0

### Architecture Changes
- ✅ **PostgreSQL Database**: Replaced SQLite with PostgreSQL for better scalability and concurrent access
- ✅ **No MQTT Required**: Removed MQTT dependency - data flows directly from bridge to database
- ✅ **REST API**: New API endpoints for querying sensor data
- ✅ **Permanent Storage**: All data now permanently stored (no automatic purging)
- ✅ **New Name**: "Hoymiles S-Miles" (S for Storage/SQL)

### Key Benefits
1. **Simpler Setup**: No WebSocket needed
2. **Better Performance**: Direct database access with connection pooling
3. **Complete History**: All inverter data, port readings, and metrics permanently stored
4. **Scalability**: PostgreSQL handles larger datasets and concurrent access better
5. **Flexibility**: Can use external PostgreSQL database or Docker service

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and configure**:
```bash
git clone https://github.com/your-repo/hoymiles-smiles
cd hoymiles-smiles
cp env.example .env
# Edit .env with your DTU settings
```

2. **Start services**:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Hoymiles S-Miles bridge (port 8080)

3. **Install Home Assistant Integration**:
```bash
# Copy to Home Assistant config directory
cp -r custom_components/hoymiles_smiles /config/custom_components/

# Restart Home Assistant
# Then add integration via UI: Settings → Devices & Services → Add Integration → Hoymiles S-Miles
```

## Configuration

### Environment Variables

```bash
# Database Configuration
DB_TYPE=postgres                    # Database type (only postgres supported)
DB_HOST=postgres                    # Database host (use 'postgres' for Docker service)
DB_PORT=5432                        # Database port
DB_NAME=hoymiles                    # Database name
DB_USER=hoymiles                    # Database user
DB_PASSWORD=hoymiles_password       # Database password
DB_POOL_SIZE=10                     # Connection pool size
DB_MAX_OVERFLOW=20                  # Maximum pool overflow

# DTU Configuration
DTU_HOST=192.168.1.100             # Your DTU IP address
DTU_PORT=502                        # DTU Modbus port
MODBUS_UNIT_ID=1                    # Modbus unit ID

# Timing
QUERY_PERIOD=60                     # Query period in seconds
RESET_HOUR=23                       # Hour to reset daily production (0-23)
TIMEZONE=UTC                        # Your timezone

# Health & API
HEALTH_ENABLED=true                 # Enable health check server
HEALTH_PORT=8080                    # API server port
METRICS_ENABLED=true                # Enable Prometheus metrics

# Logging
LOG_LEVEL=INFO                      # Log level (DEBUG, INFO, WARNING, ERROR)
LOG_TO_CONSOLE=true                 # Log to console
```

### Using External PostgreSQL Database

To use an external database instead of the Docker service:

```bash
DB_HOST=your-postgres-server.com
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_secure_password
```

Then modify `docker-compose.yml` to remove the `postgres` service and dependency.

## API Endpoints

The bridge exposes a REST API for querying data:

### Health & Monitoring
- `GET /health` - Application health status
- `GET /ready` - Readiness probe (for Kubernetes)
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Database statistics

### Data API
- `GET /api/inverters` - List all inverters
- `GET /api/inverters/{serial}` - Get latest data for specific inverter
- `GET /api/inverters/{serial}/history?limit=100` - Get historical inverter data
- `GET /api/inverters/{serial}/ports` - Get port data for inverter
- `GET /api/ports` - Get all port data
- `GET /api/production/current` - Get current production cache

### Example API Usage

```bash
# Get all inverters
curl http://localhost:8080/api/inverters

# Get latest data for specific inverter
curl http://localhost:8080/api/inverters/123456789012

# Get historical data
curl http://localhost:8080/api/inverters/123456789012/history?limit=100

# Get current production
curl http://localhost:8080/api/production/current
```

## Database Schema

### Tables

1. **inverters** - Inverter registry
   - Stores basic inverter information (serial, DTU, first/last seen)

2. **inverter_data** - All inverter readings
   - Grid voltage, frequency, temperature, status, alarms
   - Permanently stored with timestamps

3. **port_data** - All port/panel readings
   - PV voltage, current, power per port
   - Today/total production per port
   - Permanently stored with timestamps

4. **production_cache** - Current production values
   - Quick access to latest production figures

5. **system_metrics** - System metrics
   - Application metrics and statistics
   - Permanently stored

6. **config_cache** - Configuration storage
   - Runtime configuration values

## Home Assistant Integration

### Installation

1. Copy custom component:
```bash
cp -r custom_components/hoymiles_smiles /config/custom_components/
```

2. Restart Home Assistant

3. Add Integration:
   - Settings → Devices & Services → Add Integration
   - Search for "Hoymiles S-Miles"
   - Enter bridge host (e.g., `192.168.1.100`) and port (`8080`)

### Available Sensors

The integration provides these sensors:
- **Uptime** - Application uptime
- **DTU Query Count** - Number of successful queries
- **DTU Error Count** - Number of failed queries
- **DTU Last Query** - Time since last successful query
- **Database Size** - Current database size
- **Cached Records** - Number of cached records
- **Application Healthy** - Binary sensor for health status

## Monitoring

### Prometheus Metrics

Expose metrics at `http://localhost:8080/metrics` for Prometheus scraping:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hoymiles-smiles'
    static_configs:
      - targets: ['hoymiles-smiles:8080']
```

Available metrics:
- `hoymiles_queries_total` - Total DTU queries
- `hoymiles_query_duration_seconds` - Query duration
- `hoymiles_query_errors_total` - Query errors
- `hoymiles_dtu_available` - DTU availability
- `hoymiles_inverter_power_watts` - Current inverter power
- `hoymiles_inverter_temperature_celsius` - Inverter temperature
- `hoymiles_today_production_wh` - Today's production
- `hoymiles_total_production_wh` - Total production
- `hoymiles_smiles_uptime_seconds` - Application uptime

## Migration from v1.x

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration instructions from the old MQTT-based version.

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs hoymiles-smiles

# Verify connection
docker-compose exec postgres psql -U hoymiles -d hoymiles
```

### API Not Responding

```bash
# Check if bridge is running
curl http://localhost:8080/health

# Check bridge logs
docker-compose logs hoymiles-smiles

# Restart bridge
docker-compose restart hoymiles-smiles
```

### Home Assistant Integration Issues

1. Check bridge is accessible from Home Assistant
2. Verify correct host and port in integration config
3. Check Home Assistant logs for errors
4. Ensure custom component is properly installed

## Development

### Requirements

```bash
poetry install
# or
pip install -r requirements.txt
```

### Dependencies

- Python 3.10+
- PostgreSQL 12+
- psycopg2-binary - PostgreSQL adapter
- hoymiles-modbus - Hoymiles DTU communication
- aiohttp - Async HTTP client
- prometheus-client - Metrics
- pydantic - Configuration validation

### Running Tests

```bash
pytest tests/
```

### Building Docker Image

```bash
docker build -t hoymiles-smiles:latest .
```

## Architecture

```
┌─────────────────┐
│   Hoymiles DTU  │
│   (Modbus TCP)  │
└────────┬────────┘
         │ Modbus/TCP
         │
┌────────▼─────────────────────────────┐
│   Hoymiles S-Miles Bridge            │
│   ┌──────────────────────────────┐   │
│   │  Modbus Client               │   │
│   └──────────┬───────────────────┘   │
│              │                        │
│   ┌──────────▼───────────────────┐   │
│   │  Data Processor              │   │
│   └──────────┬───────────────────┘   │
│              │                        │
│   ┌──────────▼───────────────────┐   │
│   │  Persistence Layer           │   │
│   │  (PostgreSQL Client)         │   │
│   └──────────┬───────────────────┘   │
│              │                        │
│   ┌──────────▼───────────────────┐   │
│   │  REST API Server             │   │
│   │  + Prometheus Metrics        │   │
│   └──────────────────────────────┘   │
└───────────────┬──────────────────────┘
                │
                │ TCP:5432
                │
┌───────────────▼──────────────────────┐
│     PostgreSQL Database              │
│  ┌────────────────────────────────┐  │
│  │  • inverters                   │  │
│  │  • inverter_data               │  │
│  │  • port_data                   │  │
│  │  • production_cache            │  │
│  │  • system_metrics              │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
                │
                │ REST API :8080
                │
┌───────────────▼──────────────────────┐
│   Home Assistant                     │
│   Custom Component                   │
│   (Hoymiles S-Miles)                 │
└──────────────────────────────────────┘
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- **Issues**: https://github.com/hoymiles-smiles/hoymiles-smiles/issues
- **Discussions**: https://github.com/hoymiles-smiles/hoymiles-smiles/discussions
- **Documentation**: https://github.com/hoymiles-smiles/hoymiles-smiles/wiki

## Acknowledgments

- Original Hoymiles MQTT project
- hoymiles-modbus library
- Home Assistant community

