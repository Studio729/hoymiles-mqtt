"""Database adapter layer to support both PostgreSQL and MySQL/MariaDB."""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Import database drivers
try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as pg_pool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import mysql.connector
    from mysql.connector import pooling as mysql_pool
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


class DatabaseAdapter:
    """Adapter to handle database-specific operations."""
    
    def __init__(self, db_type: str):
        """Initialize database adapter.
        
        Args:
            db_type: Database type ('postgres' or 'mysql')
        """
        self.db_type = db_type.lower()
        
    def create_pool(self, config: Dict[str, Any], pool_size: int, max_overflow: int):
        """Create database connection pool.
        
        Args:
            config: Database configuration
            pool_size: Minimum pool size
            max_overflow: Maximum pool overflow
            
        Returns:
            Connection pool object
        """
        if self.db_type in ['postgres', 'postgresql']:
            if not HAS_POSTGRES:
                raise ImportError("psycopg2 not installed for PostgreSQL support")
            return pg_pool.SimpleConnectionPool(
                minconn=1,
                maxconn=pool_size + max_overflow,
                **config
            )
        elif self.db_type in ['mysql', 'mariadb']:
            if not HAS_MYSQL:
                raise ImportError("mysql-connector-python not installed for MySQL support")
            return mysql_pool.MySQLConnectionPool(
                pool_name="hoymiles_pool",
                pool_size=pool_size,
                **config
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_connection(self, pool):
        """Get connection from pool.
        
        Args:
            pool: Connection pool
            
        Returns:
            Database connection
        """
        if self.db_type in ['postgres', 'postgresql']:
            return pool.getconn()
        else:  # MySQL
            return pool.get_connection()
    
    def return_connection(self, pool, conn):
        """Return connection to pool.
        
        Args:
            pool: Connection pool
            conn: Database connection
        """
        if self.db_type in ['postgres', 'postgresql']:
            pool.putconn(conn)
        else:  # MySQL
            conn.close()  # MySQL connector handles pool return on close
    
    def get_cursor(self, conn, dict_cursor: bool = False):
        """Get database cursor.
        
        Args:
            conn: Database connection
            dict_cursor: Whether to use dictionary cursor
            
        Returns:
            Database cursor
        """
        if self.db_type in ['postgres', 'postgresql']:
            if dict_cursor:
                return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            return conn.cursor()
        else:  # MySQL
            return conn.cursor(dictionary=dict_cursor)
    
    def get_schema_sql(self) -> Dict[str, str]:
        """Get schema creation SQL for the database type.
        
        Returns:
            Dictionary of table names to CREATE TABLE SQL
        """
        if self.db_type in ['postgres', 'postgresql']:
            return self._get_postgres_schema()
        else:  # MySQL
            return self._get_mysql_schema()
    
    def _get_postgres_schema(self) -> Dict[str, str]:
        """Get PostgreSQL schema SQL."""
        return {
            'inverters': '''
                CREATE TABLE IF NOT EXISTS inverters (
                    serial_number TEXT PRIMARY KEY,
                    dtu_name TEXT,
                    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
                    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
                    inverter_type TEXT,
                    metadata JSONB
                )
            ''',
            'inverter_data': '''
                CREATE TABLE IF NOT EXISTS inverter_data (
                    id BIGSERIAL PRIMARY KEY,
                    serial_number TEXT NOT NULL REFERENCES inverters(serial_number),
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    grid_voltage REAL,
                    grid_frequency REAL,
                    temperature REAL,
                    operating_status INTEGER,
                    alarm_code INTEGER,
                    alarm_count INTEGER,
                    link_status INTEGER,
                    raw_data JSONB
                )
            ''',
            'port_data': '''
                CREATE TABLE IF NOT EXISTS port_data (
                    id BIGSERIAL PRIMARY KEY,
                    serial_number TEXT NOT NULL REFERENCES inverters(serial_number),
                    port_number INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    pv_voltage REAL,
                    pv_current REAL,
                    pv_power REAL,
                    today_production INTEGER,
                    total_production INTEGER,
                    raw_data JSONB
                )
            ''',
            'production_cache': '''
                CREATE TABLE IF NOT EXISTS production_cache (
                    serial_number TEXT NOT NULL,
                    port_number INTEGER NOT NULL,
                    today_production INTEGER NOT NULL,
                    total_production INTEGER NOT NULL,
                    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (serial_number, port_number),
                    FOREIGN KEY (serial_number) REFERENCES inverters(serial_number)
                )
            ''',
            'config_cache': '''
                CREATE TABLE IF NOT EXISTS config_cache (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
                )
            ''',
            'system_metrics': '''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id BIGSERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    tags JSONB
                )
            '''
        }
    
    def _get_mysql_schema(self) -> Dict[str, str]:
        """Get MySQL schema SQL."""
        return {
            'inverters': '''
                CREATE TABLE IF NOT EXISTS inverters (
                    serial_number VARCHAR(255) PRIMARY KEY,
                    dtu_name VARCHAR(255),
                    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    inverter_type VARCHAR(255),
                    metadata JSON
                )
            ''',
            'inverter_data': '''
                CREATE TABLE IF NOT EXISTS inverter_data (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    serial_number VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    grid_voltage FLOAT,
                    grid_frequency FLOAT,
                    temperature FLOAT,
                    operating_status INT,
                    alarm_code INT,
                    alarm_count INT,
                    link_status INT,
                    raw_data JSON,
                    FOREIGN KEY (serial_number) REFERENCES inverters(serial_number),
                    INDEX idx_inverter_data_serial (serial_number),
                    INDEX idx_inverter_data_timestamp (timestamp DESC)
                )
            ''',
            'port_data': '''
                CREATE TABLE IF NOT EXISTS port_data (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    serial_number VARCHAR(255) NOT NULL,
                    port_number INT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    pv_voltage FLOAT,
                    pv_current FLOAT,
                    pv_power FLOAT,
                    today_production INT,
                    total_production INT,
                    raw_data JSON,
                    FOREIGN KEY (serial_number) REFERENCES inverters(serial_number),
                    INDEX idx_port_data_serial (serial_number),
                    INDEX idx_port_data_timestamp (timestamp DESC),
                    INDEX idx_port_data_serial_port (serial_number, port_number)
                )
            ''',
            'production_cache': '''
                CREATE TABLE IF NOT EXISTS production_cache (
                    serial_number VARCHAR(255) NOT NULL,
                    port_number INT NOT NULL,
                    today_production INT NOT NULL,
                    total_production INT NOT NULL,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (serial_number, port_number),
                    FOREIGN KEY (serial_number) REFERENCES inverters(serial_number)
                )
            ''',
            'config_cache': '''
                CREATE TABLE IF NOT EXISTS config_cache (
                    `key` VARCHAR(255) PRIMARY KEY,
                    value JSON NOT NULL,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''',
            'system_metrics': '''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metric_name VARCHAR(255) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    tags JSON,
                    INDEX idx_metrics_timestamp (timestamp DESC),
                    INDEX idx_metrics_name (metric_name)
                )
            '''
        }
    
    def upsert_inverter(self) -> str:
        """Get SQL for upserting inverter record."""
        if self.db_type in ['postgres', 'postgresql']:
            return '''
                INSERT INTO inverters (serial_number, dtu_name, first_seen, last_seen)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (serial_number) 
                DO UPDATE SET last_seen = NOW(), dtu_name = EXCLUDED.dtu_name
            '''
        else:  # MySQL
            return '''
                INSERT INTO inverters (serial_number, dtu_name, first_seen, last_seen)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE 
                    last_seen = CURRENT_TIMESTAMP,
                    dtu_name = VALUES(dtu_name)
            '''
    
    def upsert_production_cache(self) -> str:
        """Get SQL for upserting production cache."""
        if self.db_type in ['postgres', 'postgresql']:
            return '''
                INSERT INTO production_cache 
                (serial_number, port_number, today_production, total_production, last_updated)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (serial_number, port_number) 
                DO UPDATE SET 
                    today_production = EXCLUDED.today_production,
                    total_production = EXCLUDED.total_production,
                    last_updated = NOW()
            '''
        else:  # MySQL
            return '''
                INSERT INTO production_cache 
                (serial_number, port_number, today_production, total_production, last_updated)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE 
                    today_production = VALUES(today_production),
                    total_production = VALUES(total_production),
                    last_updated = CURRENT_TIMESTAMP
            '''
    
    def upsert_config(self) -> str:
        """Get SQL for upserting config."""
        if self.db_type in ['postgres', 'postgresql']:
            return '''
                INSERT INTO config_cache (key, value, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) 
                DO UPDATE SET value = EXCLUDED.value, last_updated = NOW()
            '''
        else:  # MySQL
            return '''
                INSERT INTO config_cache (`key`, value, last_updated)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE 
                    value = VALUES(value),
                    last_updated = CURRENT_TIMESTAMP
            '''
    
    def get_database_size_sql(self) -> Optional[str]:
        """Get SQL for database size query."""
        if self.db_type in ['postgres', 'postgresql']:
            return "SELECT pg_database_size(current_database())"
        else:  # MySQL
            return None  # MySQL requires schema-specific query
    
    def close_pool(self, pool):
        """Close connection pool."""
        try:
            if self.db_type in ['postgres', 'postgresql']:
                pool.closeall()
            else:  # MySQL - connection pool doesn't have explicit close
                pass
        except Exception as e:
            logger.error(f"Error closing pool: {e}")

