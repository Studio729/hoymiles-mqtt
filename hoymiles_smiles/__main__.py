"""Enhanced Hoymiles S-Miles application with all features."""

import argparse
import logging
import sys
import threading
from pathlib import Path

import configargparse

from hoymiles_smiles import __version__
from hoymiles_smiles.circuit_breaker import ErrorRecoveryManager
from hoymiles_smiles.config import AppConfig
from hoymiles_smiles.health import HealthCheckServer, HealthMetrics
from hoymiles_smiles.logging_config import setup_logging
from hoymiles_smiles.persistence import PersistenceManager
from hoymiles_smiles.runners import (
    MultiDtuCoordinator,
    run_periodic_coordinator,
    setup_signal_handlers,
)
from hoymiles_smiles.websocket_client import WebSocketClient

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = configargparse.ArgParser(
        description=f'Hoymiles S-Miles Bridge v{__version__}',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='python3 -m hoymiles_smiles',
        config_file_parser_class=configargparse.YAMLConfigFileParser,
    )
    
    # Configuration file
    parser.add('-c', '--config', required=False, is_config_file=True, help='Config file path (YAML)')
    
    # DTU Configuration
    dtu_group = parser.add_argument_group('DTU Configuration')
    dtu_group.add('--dtu-host', env_var='DTU_HOST', help='DTU hostname or IP (single DTU mode)')
    dtu_group.add('--dtu-port', type=int, default=502, env_var='DTU_PORT', help='DTU Modbus port')
    dtu_group.add('--modbus-unit-id', type=int, default=1, env_var='MODBUS_UNIT_ID', help='Modbus unit ID')
    
    # Modbus Communication
    modbus_group = parser.add_argument_group('Modbus Communication')
    modbus_group.add('--comm-timeout', type=int, default=3, env_var='COMM_TIMEOUT',
                     help='Modbus request timeout (seconds)')
    modbus_group.add('--comm-retries', type=int, default=3, env_var='COMM_RETRIES',
                     help='Max Modbus retries per request')
    modbus_group.add('--comm-reconnect-delay', type=float, default=0, env_var='COMM_RECONNECT_DELAY',
                     help='Minimum reconnect delay (seconds)')
    modbus_group.add('--comm-reconnect-delay-max', type=float, default=300, env_var='COMM_RECONNECT_DELAY_MAX',
                     help='Maximum reconnect delay (seconds)')
    
    # Entity Filtering
    entity_group = parser.add_argument_group('Entity Filtering')
    entity_group.add('--mi-entities', nargs='+', env_var='MI_ENTITIES',
                     help='Microinverter entities to publish (space-separated)')
    entity_group.add('--port-entities', nargs='+', env_var='PORT_ENTITIES',
                     help='Port/panel entities to publish (space-separated)')
    entity_group.add('--exclude-inverters', nargs='+', default=[], env_var='EXCLUDE_INVERTERS',
                     help='Inverter serial numbers to exclude (space-separated)')
    
    # Timing
    timing_group = parser.add_argument_group('Timing Configuration')
    timing_group.add('--query-period', type=int, default=60, env_var='QUERY_PERIOD',
                     help='Query period in seconds')
    timing_group.add('--expire-after', type=int, default=0, env_var='EXPIRE_AFTER',
                     help='Entity expiration time (seconds, 0=never)')
    timing_group.add('--reset-hour', type=int, default=23, env_var='RESET_HOUR',
                     help='Hour to reset daily production (0-23)')
    timing_group.add('--timezone', default='UTC', env_var='TIMEZONE',
                     help='Timezone (e.g., America/New_York, Europe/London)')
    
    # Persistence
    persistence_group = parser.add_argument_group('Data Persistence')
    persistence_group.add('--persistence-enabled', action='store_true', default=True,
                          env_var='PERSISTENCE_ENABLED', help='Enable data persistence')
    persistence_group.add('--database-path', default='/data/hoymiles-smiles.db',
                          env_var='DATABASE_PATH', help='SQLite database path')
    
    # Health Check
    health_group = parser.add_argument_group('Health Monitoring')
    health_group.add('--health-enabled', action='store_true', default=True,
                     env_var='HEALTH_ENABLED', help='Enable health check server')
    health_group.add('--health-host', default='0.0.0.0', env_var='HEALTH_HOST', help='Health check server host')
    health_group.add('--health-port', type=int, default=8080, env_var='HEALTH_PORT', help='Health check server port')
    health_group.add('--metrics-enabled', action='store_true', default=True,
                     env_var='METRICS_ENABLED', help='Enable Prometheus metrics')
    
    # Alerts
    alerts_group = parser.add_argument_group('Alerts')
    alerts_group.add('--alerts-enabled', action='store_true', env_var='ALERTS_ENABLED', help='Enable alerts')
    alerts_group.add('--dtu-offline-threshold', type=int, default=300, env_var='DTU_OFFLINE_THRESHOLD',
                     help='DTU offline threshold (seconds)')
    alerts_group.add('--temperature-threshold', type=float, default=80.0, env_var='TEMPERATURE_THRESHOLD',
                     help='Temperature warning threshold (Celsius)')
    
    # Logging
    logging_group = parser.add_argument_group('Logging')
    logging_group.add('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='WARNING', env_var='LOG_LEVEL', help='Log level')
    logging_group.add('--log-format', choices=['standard', 'json'], default='standard',
                      env_var='LOG_FORMAT', help='Log format')
    logging_group.add('--log-file', env_var='LOG_FILE', help='Log file path')
    logging_group.add('--log-to-console', action='store_true', env_var='LOG_TO_CONSOLE',
                      help='Enable console logging')
    
    # Error Recovery
    recovery_group = parser.add_argument_group('Error Recovery')
    recovery_group.add('--exponential-backoff', action='store_true', default=True,
                       env_var='EXPONENTIAL_BACKOFF', help='Use exponential backoff for retries')
    recovery_group.add('--circuit-breaker-threshold', type=int, default=5,
                       env_var='CIRCUIT_BREAKER_THRESHOLD', help='Circuit breaker failure threshold')
    
    # Advanced Options
    advanced_group = parser.add_argument_group('Advanced Options')
    advanced_group.add('--dry-run', action='store_true', env_var='DRY_RUN',
                       help='Dry run mode (query but don\'t publish)')
    advanced_group.add('--dump-data', action='store_true', env_var='DUMP_DATA',
                       help='Dump raw DTU data to file')
    advanced_group.add('--dump-data-path', env_var='DUMP_DATA_PATH',
                       help='Path for data dump file')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Convert args to config
    config = AppConfig(**vars(args))
    
    # Setup logging
    logging_config = config.get_logging_config()
    setup_logging(
        level=logging_config.level,
        format_type=logging_config.format,
        log_file=logging_config.file,
        console=logging_config.console,
    )
    
    logger.info("=" * 60)
    logger.info(f"Hoymiles S-Miles Bridge v{__version__}")
    logger.info("=" * 60)
    
    # Validate configuration
    try:
        config.validate_config()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    
    # Log configuration summary
    dtu_configs = config.get_dtu_configs()
    logger.info(f"Configured DTUs: {len(dtu_configs)}")
    for dtu in dtu_configs:
        logger.info(f"  - {dtu.name}: {dtu.host}:{dtu.port}")
    
    db_config = config.get_database_config()
    logger.info(f"Database: {db_config.type}://{db_config.host}:{db_config.port}/{db_config.database}")
    logger.info(f"Query Period: {config.query_period}s")
    logger.info(f"Timezone: {config.timezone}")
    logger.info(f"Reset Hour: {config.reset_hour}:00")
    
    if config.dry_run:
        logger.warning("Running in DRY RUN mode - no data will be published")
    
    # Initialize components
    logger.info("Initializing components...")
    
    # Persistence
    persistence_config = config.get_persistence_config()
    db_config = config.get_database_config()
    
    persistence_manager = PersistenceManager(
        enabled=persistence_config.enabled,
        type=db_config.type,
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        user=db_config.user,
        password=db_config.password,
    )
    
    # Health metrics
    health_metrics = HealthMetrics()
    
    # WebSocket client for push updates
    websocket_client = WebSocketClient(enabled=True)
    logger.info("WebSocket client initialized for push updates")
    
    # Error recovery
    error_recovery = ErrorRecoveryManager(config)
    
    # Multi-DTU coordinator
    coordinator = MultiDtuCoordinator(
        config=config,
        persistence_manager=persistence_manager,
        health_metrics=health_metrics,
        error_recovery=error_recovery,
        websocket_client=websocket_client,
    )
    
    # Health check server
    health_server = None
    if config.health_enabled:
        health_server = HealthCheckServer(
            host=config.health_host,
            port=config.health_port,
            health_metrics=health_metrics,
            persistence_manager=persistence_manager,
            websocket_client=websocket_client,
        )
        health_server.start()
    
    # Setup graceful shutdown
    stop_event = threading.Event()
    setup_signal_handlers(stop_event)
    
    logger.info("All components initialized successfully")
    logger.info("Starting main loop...")
    
    try:
        # Run periodic coordinator
        run_periodic_coordinator(coordinator, config.query_period, stop_event)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("Shutting down...")
        
        # Stop components
        if health_server:
            health_server.stop()
        
        # Close WebSocket client
        if websocket_client:
            logger.info("Closing WebSocket client...")
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(websocket_client.close())
                loop.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket client: {e}")
        
        # Close persistence
        if persistence_manager:
            logger.info("Closing persistence...")
            persistence_manager.close()
        
        logger.info("Shutdown complete")
        logger.info("=" * 60)


if __name__ == '__main__':
    main()

