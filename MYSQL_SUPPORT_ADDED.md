# MySQL/MariaDB Support Added

## Overview

The Hoymiles S-Miles Bridge now supports **both PostgreSQL and MySQL/MariaDB** databases!

## Changes Made

### 1. Configuration Support (`config.py`)
- Updated `DatabaseConfig` validator to accept `mysql`, `mariadb`, `postgres`, and `postgresql`
- Automatically normalizes database types (`mariadb` → `mysql`, `postgresql` → `postgres`)

### 2. Database Abstraction Layer (`db_adapter.py`)
**NEW FILE** - Provides database-agnostic operations:
- Connection pool management for both databases
- Database-specific SQL generation (schema, upserts, queries)
- Cursor handling for both psycopg2 and mysql-connector
- Handles differences:
  - PostgreSQL: `JSONB`, `BIGSERIAL`, `ON CONFLICT`
  - MySQL: `JSON`, `AUTO_INCREMENT`, `ON DUPLICATE KEY UPDATE`

### 3. Persistence Layer (`persistence.py`)
- Updated to use `DatabaseAdapter` for all database operations
- Removed hard-coded PostgreSQL SQL
- Dynamic SQL generation based on database type
- Automatic driver detection and validation

### 4. Main Application (`__main__.py`)
- Added `type` parameter to `PersistenceManager` initialization
- Passes database type from configuration

### 5. Dependencies (`pyproject.toml`)
- Added `mysql-connector-python = "^9.1.0"`
- Both PostgreSQL and MySQL drivers are now included

### 6. Docker Support (`Dockerfile`)
- Added MySQL/MariaDB client libraries
- Includes both `postgresql-dev` and `mariadb-dev`

## Usage

### Environment Variables

For **MySQL/MariaDB**:
```env
DB_TYPE=mysql
DB_HOST=192.168.1.50
DB_PORT=3306
DB_NAME=hoymiles
DB_USER=hoymiles
DB_PASSWORD=your_password
```

For **PostgreSQL** (still supported):
```env
DB_TYPE=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hoymiles
DB_USER=hoymiles
DB_PASSWORD=your_password
```

### Docker Compose Example

```yaml
services:
  hoymiles-smiles:
    image: ghcr.io/studio729/hoymiles-bridge:latest
    environment:
      # MySQL Configuration
      DB_TYPE: mysql
      DB_HOST: 192.168.1.50
      DB_PORT: 3306
      DB_NAME: hoymiles
      DB_USER: hoymiles
      DB_PASSWORD: your_secure_password
      
      # DTU Configuration
      DTU_HOST: 192.168.1.191
      DTU_PORT: 502
```

## Database Setup

### MySQL/MariaDB Setup

Connect to your MySQL/MariaDB server (e.g., using Sequel Ace) and run:

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS hoymiles 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS 'hoymiles'@'%' 
  IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON hoymiles.* TO 'hoymiles'@'%';
FLUSH PRIVILEGES;
```

### Schema Auto-Creation

The application automatically creates all necessary tables on first run:
- `inverters` - Inverter information
- `inverter_data` - Inverter readings (historical)
- `port_data` - Port/panel readings (historical)
- `production_cache` - Current production values
- `config_cache` - Configuration cache
- `system_metrics` - System metrics

## Features

### Database-Agnostic
- Same API for both PostgreSQL and MySQL
- Automatic SQL generation based on database type
- No code changes needed to switch databases

### Schema Compatibility
- PostgreSQL uses `JSONB` for JSON storage
- MySQL uses `JSON` for JSON storage
- PostgreSQL uses `BIGSERIAL` for auto-increment
- MySQL uses `AUTO_INCREMENT`
- Both support full feature set

### Connection Pooling
- PostgreSQL: `psycopg2.pool.SimpleConnectionPool`
- MySQL: `mysql.connector.pooling.MySQLConnectionPool`
- Configurable pool sizes via environment variables

## Troubleshooting

### "psycopg2 not installed"
This is just a warning. If using MySQL, you can ignore it. The system checks for available drivers and uses what's needed.

### "mysql-connector-python not installed"
If you see this and want to use MySQL, rebuild the Docker image:
```bash
docker-compose build --no-cache
```

### Connection Refused
1. Verify MySQL is running: `mysql -h 192.168.1.50 -u hoymiles -p`
2. Check firewall: `telnet 192.168.1.50 3306`
3. Verify MySQL allows remote connections (check `bind-address` in MySQL config)

### Schema Creation Fails
- Ensure the MySQL user has `CREATE` privileges
- Check MySQL error logs for specific errors
- For MariaDB, ensure version >= 10.2 (for JSON support)

## Benefits of MySQL/MariaDB Support

✅ **Use Existing Infrastructure** - Connect to your existing MySQL server  
✅ **Sequel Ace Compatible** - Use your favorite database tool  
✅ **Shared Database** - Multiple applications can access the same data  
✅ **Better for Some Environments** - Some users prefer MySQL ecosystem  
✅ **Flexible Deployment** - Choose the database that fits your setup  

## Technical Details

### SQL Compatibility
The adapter handles these key differences:

| Feature | PostgreSQL | MySQL/MariaDB |
|---------|------------|---------------|
| Auto-increment | `BIGSERIAL` | `AUTO_INCREMENT` |
| JSON type | `JSONB` | `JSON` |
| Upsert | `ON CONFLICT` | `ON DUPLICATE KEY UPDATE` |
| Current time | `NOW()` | `CURRENT_TIMESTAMP` |
| String type | `TEXT` | `VARCHAR(255)` |
| Index creation | In CREATE TABLE | In CREATE TABLE |

### Driver Detection
The system automatically detects which database drivers are available:
- If only `psycopg2` is installed → PostgreSQL only
- If only `mysql-connector-python` is installed → MySQL only  
- If both installed → Uses `DB_TYPE` to choose

### Error Handling
- Graceful fallback if requested database type isn't available
- Clear error messages indicating missing drivers
- Connection pool errors logged with details

## Migration from PostgreSQL to MySQL

If you're switching from PostgreSQL to MySQL:

1. **Backup PostgreSQL data:**
   ```bash
   pg_dump -h localhost -U hoymiles hoymiles > backup.sql
   ```

2. **Create MySQL database** (see setup above)

3. **Update environment variables:**
   ```env
   DB_TYPE=mysql
   DB_HOST=192.168.1.50
   DB_PORT=3306
   ```

4. **Restart container:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

5. **Schema is auto-created** - No manual migration needed!

Note: You'll need to manually migrate data if you want to preserve history. For a fresh start, just change the configuration and run.

## Testing

To verify MySQL support is working:

1. **Check logs:**
   ```bash
   docker logs hoymiles-smiles | grep -i mysql
   ```
   
   Should see: `Connected to MYSQL at 192.168.1.50:3306/hoymiles`

2. **Check tables in MySQL:**
   ```sql
   USE hoymiles;
   SHOW TABLES;
   ```
   
   Should see all 6 tables listed.

3. **Verify data is being written:**
   ```sql
   SELECT * FROM inverters;
   SELECT COUNT(*) FROM inverter_data;
   ```

## Performance Considerations

- **Connection Pool Size**: Adjust `DB_POOL_SIZE` based on load (default: 10)
- **MySQL**: Consider enabling `innodb_buffer_pool_size` for better performance
- **PostgreSQL**: Generally faster for complex queries with JSONB
- **MySQL**: Generally faster for simple INSERT/SELECT operations

## Files Modified

- ✏️ `hoymiles_smiles/config.py` - Database type validation
- ✏️ `hoymiles_smiles/persistence.py` - Use adapter for all operations
- ✏️ `hoymiles_smiles/__main__.py` - Pass database type to persistence
- ✏️ `pyproject.toml` - Added MySQL connector dependency
- ✏️ `Dockerfile` - Added MySQL client libraries
- ✨ **NEW** `hoymiles_smiles/db_adapter.py` - Database abstraction layer

## Commit Message

```
feat: Add MySQL/MariaDB database support

- Add DatabaseAdapter abstraction layer for multi-database support
- Update config validation to accept mysql/mariadb types
- Modify persistence layer to use database-agnostic SQL
- Add mysql-connector-python dependency
- Update Dockerfile with MySQL client libraries
- Support both PostgreSQL and MySQL/MariaDB with same codebase

This allows users to connect to existing MySQL/MariaDB servers
and use tools like Sequel Ace for database management.

Closes: #[issue_number if applicable]
```

## Future Enhancements

Potential improvements for the future:
- [ ] Add SQLite support for embedded deployments
- [ ] Migration tool to transfer data between database types
- [ ] Performance benchmarks comparing PostgreSQL vs MySQL
- [ ] Database-specific optimizations (e.g., MySQL InnoDB tuning)

---

**Author**: AI Assistant  
**Date**: November 7, 2025  
**Version**: Added in v1.1.0+

