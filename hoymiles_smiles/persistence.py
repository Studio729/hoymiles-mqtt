"""Data persistence layer supporting PostgreSQL and MySQL/MariaDB."""

import json
import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hoymiles_smiles.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def normalize_db_value(value: Any) -> Any:
    """Normalize database value to JSON-serializable type.
    
    Converts:
    - Decimal -> float
    - datetime -> ISO format string
    - None -> None (preserved)
    
    Args:
        value: Value from database
        
    Returns:
        Normalized value
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        # Convert to ISO format string with timezone
        if value.tzinfo is None:
            # Naive datetime - assume UTC
            from datetime import timezone
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    # For other types, try to convert to string
    return str(value)


def normalize_db_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a database record to JSON-serializable format.
    
    Args:
        record: Database record dictionary
        
    Returns:
        Normalized record dictionary
    """
    normalized = {}
    for key, value in record.items():
        normalized[key] = normalize_db_value(value)
    return normalized


class PersistenceManager:
    """Manages persistent storage of solar production data in PostgreSQL or MySQL/MariaDB."""

    def __init__(self, enabled: bool = True, **db_config):
        """Initialize persistence manager.
        
        Args:
            enabled: Whether persistence is enabled
            **db_config: Database configuration (host, port, database, user, password, type, etc.)
        """
        self.enabled = enabled
        self.db_config = db_config
        self.db_type = os.getenv('DB_TYPE', db_config.get('type', 'postgres')).lower()
        self.connection_pool = None
        
        # Create database adapter
        try:
            self.adapter = DatabaseAdapter(self.db_type)
        except (ImportError, ValueError) as e:
            logger.error(f"Failed to initialize database adapter: {e}")
            self.enabled = False
        
        if self.enabled:
            self._initialize_database()
    
    def _get_db_config(self) -> Dict[str, Any]:
        """Get database configuration from environment or config."""
        return {
            'host': os.getenv('DB_HOST', self.db_config.get('host', 'localhost')),
            'port': int(os.getenv('DB_PORT', self.db_config.get('port', 5432))),
            'database': os.getenv('DB_NAME', self.db_config.get('database', 'hoymiles')),
            'user': os.getenv('DB_USER', self.db_config.get('user', 'hoymiles')),
            'password': os.getenv('DB_PASSWORD', self.db_config.get('password', 'hoymiles_password')),
        }
    
    def _initialize_database(self) -> None:
        """Initialize database connection pool and schema."""
        try:
            config = self._get_db_config()
            pool_size = int(os.getenv('DB_POOL_SIZE', 10))
            max_overflow = int(os.getenv('DB_MAX_OVERFLOW', 20))
            
            # Create connection pool using adapter
            self.connection_pool = self.adapter.create_pool(config, pool_size, max_overflow)
            
            logger.info(f"Connected to {self.db_type.upper()} at {config['host']}:{config['port']}/{config['database']}")
            
            # Create schema
            self._create_schema()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.enabled = False
    
    def _get_connection(self):
        """Get a connection from the pool."""
        if not self.connection_pool:
            raise Exception("Connection pool not initialized")
        return self.adapter.get_connection(self.connection_pool)
    
    def _return_connection(self, conn):
        """Return a connection to the pool."""
        if self.connection_pool:
            self.adapter.return_connection(self.connection_pool, conn)
    
    def _create_schema(self) -> None:
        """Create database schema with all necessary tables."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn)
            
            # Get schema SQL for this database type
            schema_sql = self.adapter.get_schema_sql()
            
            # Create tables in order (respecting foreign keys)
            table_order = ['inverters', 'inverter_data', 'port_data', 'production_cache', 'config_cache', 'system_metrics']
            
            for table_name in table_order:
                if table_name in schema_sql:
                    cursor.execute(schema_sql[table_name])
                    logger.debug(f"Created/verified table: {table_name}")
            
            conn.commit()
            logger.info("Database schema created successfully")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to create database schema: {e}")
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def save_inverter_data(self, serial_number: str, dtu_name: str, data: Dict[str, Any]) -> None:
        """Save inverter reading data.
        
        Args:
            serial_number: Inverter serial number
            dtu_name: DTU name
            data: Inverter data dictionary
        """
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Update or insert inverter record
            cursor.execute(self.adapter.upsert_inverter(), (serial_number, dtu_name))
            
            # Insert inverter data
            cursor.execute('''
                INSERT INTO inverter_data 
                (serial_number, grid_voltage, grid_frequency, temperature, 
                 operating_status, alarm_code, alarm_count, link_status, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                serial_number,
                data.get('grid_voltage'),
                data.get('grid_frequency'),
                data.get('temperature'),
                data.get('operating_status'),
                data.get('alarm_code'),
                data.get('alarm_count'),
                data.get('link_status'),
                json.dumps(data, cls=DecimalEncoder)
            ))
            
            conn.commit()
            logger.debug(f"Saved inverter data for {serial_number}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save inverter data: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def save_port_data(self, serial_number: str, port_number: int, data: Dict[str, Any]) -> None:
        """Save port/panel reading data.
        
        Args:
            serial_number: Inverter serial number
            port_number: Port number
            data: Port data dictionary
        """
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Ensure inverter exists (create if needed)
            cursor.execute(self.adapter.upsert_inverter(), (serial_number, None))
            
            # Insert port data
            cursor.execute('''
                INSERT INTO port_data 
                (serial_number, port_number, pv_voltage, pv_current, pv_power, 
                 today_production, total_production, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                serial_number,
                port_number,
                data.get('pv_voltage'),
                data.get('pv_current'),
                data.get('pv_power'),
                data.get('today_production'),
                data.get('total_production'),
                json.dumps(data, cls=DecimalEncoder)
            ))
            
            conn.commit()
            logger.debug(f"Saved port data for {serial_number} port {port_number}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save port data: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def save_production_cache(self, serial_number: str, port_number: int, 
                            today_production: int, total_production: int) -> None:
        """Save production cache for an inverter port.
        
        Args:
            serial_number: Inverter serial number
            port_number: Port number
            today_production: Today's production value
            total_production: Total production value
        """
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Ensure inverter exists (create if needed)
            cursor.execute(self.adapter.upsert_inverter(), (serial_number, None))
            
            cursor.execute(
                self.adapter.upsert_production_cache(),
                (serial_number, port_number, today_production, total_production)
            )
            
            conn.commit()
            logger.debug(f"Saved production cache for {serial_number} port {port_number}")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save production cache: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def load_production_cache(self) -> Dict[Tuple[str, int], Tuple[int, int]]:
        """Load production cache for all inverter ports.
        
        Returns:
            Dictionary mapping (serial_number, port_number) to (today_production, total_production)
        """
        if not self.enabled or not self.connection_pool:
            return {}
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            cursor.execute('SELECT * FROM production_cache')
            
            cache = {}
            for row in cursor.fetchall():
                key = (row['serial_number'], row['port_number'])
                value = (row['today_production'], row['total_production'])
                cache[key] = value
            
            logger.info(f"Loaded production cache for {len(cache)} inverter ports")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to load production cache: {e}")
            return {}
        finally:
            if conn:
                self._return_connection(conn)
    
    def clear_today_production(self) -> None:
        """Clear today's production values (called at daily reset)."""
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('UPDATE production_cache SET today_production = 0')
            conn.commit()
            logger.info("Cleared today's production cache")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to clear today's production: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_latest_inverter_data(self, serial_number: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get latest inverter data readings.
        
        Args:
            serial_number: Optional filter by serial number
            limit: Maximum number of records
            
        Returns:
            List of inverter data records
        """
        if not self.enabled or not self.connection_pool:
            return []
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            if serial_number:
                cursor.execute('''
                    SELECT * FROM inverter_data 
                    WHERE serial_number = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (serial_number, limit))
            else:
                cursor.execute('''
                    SELECT * FROM inverter_data 
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get inverter data: {e}")
            return []
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_latest_port_data(self, serial_number: Optional[str] = None, 
                            port_number: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Get latest port data readings.
        
        Args:
            serial_number: Optional filter by serial number
            port_number: Optional filter by port number
            limit: Maximum number of records
            
        Returns:
            List of port data records
        """
        if not self.enabled or not self.connection_pool:
            return []
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            if serial_number and port_number is not None:
                cursor.execute('''
                    SELECT * FROM port_data 
                    WHERE serial_number = %s AND port_number = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (serial_number, port_number, limit))
            elif serial_number:
                cursor.execute('''
                    SELECT * FROM port_data 
                    WHERE serial_number = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (serial_number, limit))
            else:
                cursor.execute('''
                    SELECT * FROM port_data 
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get port data: {e}")
            return []
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_all_inverters(self) -> List[Dict]:
        """Get all registered inverters.
        
        Returns:
            List of inverter records
        """
        if not self.enabled or not self.connection_pool:
            return []
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            cursor.execute('SELECT * FROM inverters ORDER BY serial_number')
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get inverters: {e}")
            return []
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_all_inverters_with_data(self) -> List[Dict]:
        """Get all inverters with their latest readings and port data.
        
        Returns:
            List of enriched inverter records with latest data and ports
            All values are normalized to JSON-serializable types (float, str, etc.)
        """
        if not self.enabled or not self.connection_pool:
            return []
        
        inverters = self.get_all_inverters()
        enriched_inverters = []
        
        for inverter in inverters:
            serial_number = inverter.get('serial_number')
            if not serial_number:
                continue
            
            # Get latest inverter reading
            latest_data = self.get_latest_inverter_data(serial_number=serial_number, limit=1)
            if latest_data:
                inverter_reading = latest_data[0]
                # Normalize and merge inverter metadata with latest reading
                enriched = normalize_db_record({**inverter, **inverter_reading})
            else:
                enriched = normalize_db_record(dict(inverter))
            
            # Get latest port data for all ports
            port_data = self.get_latest_port_data(serial_number=serial_number, limit=10)
            
            # Group port data by port number and get the latest for each port
            # Normalize each port record
            ports_by_number = {}
            for port in port_data:
                port_num = port.get('port_number')
                if port_num not in ports_by_number:
                    ports_by_number[port_num] = normalize_db_record(port)
            
            enriched['ports'] = list(ports_by_number.values())
            enriched_inverters.append(enriched)
        
        return enriched_inverters
    
    def save_config(self, key: str, value: Any) -> None:
        """Save configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value (will be JSON serialized)
        """
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                self.adapter.upsert_config(),
                (key, json.dumps(value, cls=DecimalEncoder))
            )
            
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save config: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def load_config(self, key: str, default: Any = None) -> Any:
        """Load configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self.enabled or not self.connection_pool:
            return default
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            cursor.execute('SELECT value FROM config_cache WHERE key = %s', (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['value']) if isinstance(row['value'], str) else row['value']
            return default
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default
        finally:
            if conn:
                self._return_connection(conn)
    
    def save_metric(self, metric_name: str, metric_value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Save a metric value (permanently stored).
        
        Args:
            metric_name: Metric name
            metric_value: Metric value
            tags: Optional tags for the metric
        """
        if not self.enabled or not self.connection_pool:
            return
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics (metric_name, metric_value, tags)
                VALUES (%s, %s, %s)
            ''', (metric_name, metric_value, json.dumps(tags, cls=DecimalEncoder) if tags else None))
            
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save metric: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_metrics(self, metric_name: str, since: Optional[datetime] = None, limit: int = 1000) -> List[Dict]:
        """Get historical metrics.
        
        Args:
            metric_name: Metric name to query
            since: Optional start time
            limit: Maximum number of records to return
            
        Returns:
            List of metric records
        """
        if not self.enabled or not self.connection_pool:
            return []
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = self.adapter.get_cursor(conn, dict_cursor=True)
            
            if since:
                cursor.execute('''
                    SELECT * FROM system_metrics 
                    WHERE metric_name = %s AND timestamp >= %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (metric_name, since, limit))
            else:
                cursor.execute('''
                    SELECT * FROM system_metrics 
                    WHERE metric_name = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (metric_name, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        if not self.enabled or not self.connection_pool:
            return {}
        
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get table counts
            cursor.execute('SELECT COUNT(*) FROM production_cache')
            production_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM config_cache')
            config_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM system_metrics')
            metrics_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inverter_data')
            inverter_data_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM port_data')
            port_data_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inverters')
            inverters_count = cursor.fetchone()[0]
            
            # Get database size (PostgreSQL only)
            db_size = 0
            size_sql = self.adapter.get_database_size_sql()
            if size_sql:
                cursor.execute(size_sql)
                db_size = cursor.fetchone()[0]
            
            return {
                'database_type': self.db_type.upper(),
                'database_size_bytes': db_size,
                'production_cache_entries': production_count,
                'config_cache_entries': config_count,
                'metrics_entries': metrics_count,
                'inverter_data_entries': inverter_data_count,
                'port_data_entries': port_data_count,
                'inverters_count': inverters_count,
                'total_records': production_count + config_count + metrics_count + inverter_data_count + port_data_count,
            }
            
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {}
        finally:
            if conn:
                self._return_connection(conn)
    
    def close(self) -> None:
        """Close database connection pool."""
        if self.connection_pool:
            try:
                self.adapter.close_pool(self.connection_pool)
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database connection pool: {e}")
            finally:
                self.connection_pool = None
