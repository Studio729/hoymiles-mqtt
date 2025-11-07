"""Enhanced runners with multi-DTU support."""

import logging
import signal
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz
from hoymiles_modbus.client import HoymilesModbusTCP
from pymodbus import exceptions as pymodbus_exceptions

from hoymiles_smiles.circuit_breaker import ErrorRecoveryManager
from hoymiles_smiles.config import AppConfig, DtuConfig
from hoymiles_smiles.health import HealthMetrics
from hoymiles_smiles.persistence import PersistenceManager

logger = logging.getLogger(__name__)


class DtuQueryJob:
    """Query job for a single DTU - stores data in database."""
    
    def __init__(
        self,
        dtu_config: DtuConfig,
        modbus_client: HoymilesModbusTCP,
        health_metrics: HealthMetrics,
        error_recovery: ErrorRecoveryManager,
        persistence_manager: PersistenceManager,
        config: AppConfig,
    ):
        """Initialize DTU query job.
        
        Args:
            dtu_config: DTU configuration
            modbus_client: Modbus client
            health_metrics: Health metrics tracker
            error_recovery: Error recovery manager
            persistence_manager: Database persistence manager
            config: Application configuration
        """
        self.dtu_config = dtu_config
        self.modbus_client = modbus_client
        self.health_metrics = health_metrics
        self.error_recovery = error_recovery
        self.persistence = persistence_manager
        self.config = config
        self._lock = threading.Lock()
    
    def execute(self) -> bool:
        """Execute query job.
        
        Returns:
            True if successful
        """
        is_acquired = self._lock.acquire(blocking=False)
        if not is_acquired:
            logger.warning(
                f"Previous query for {self.dtu_config.name} not finished. "
                f"Query period may be too small."
            )
            return False
        
        try:
            start_time = time.time()
            
            # Query DTU through circuit breaker
            plant_data = self.error_recovery.execute_with_recovery(
                f"dtu_{self.dtu_config.name}",
                self._query_dtu,
            )
            
            if plant_data is None:
                logger.error(f"Failed to query DTU {self.dtu_config.name}")
                self.health_metrics.record_query_error(
                    self.dtu_config.name, 
                    "query_failed", 
                    "No data received from DTU"
                )
                return False
            
            # Save data to database
            self._save_plant_data(plant_data)
            
            elapsed = time.time() - start_time
            inverters = plant_data.inverters if hasattr(plant_data, 'inverters') else []
            logger.info(
                f"Successfully queried {self.dtu_config.name} in {elapsed:.2f}s - "
                f"Found {len(inverters)} inverters"
            )
            
            self.health_metrics.record_query_success(self.dtu_config.name, elapsed)
            return True
            
        except Exception as e:
            logger.exception(f"Unexpected error querying {self.dtu_config.name}: {e}")
            self.health_metrics.record_query_error(
                self.dtu_config.name,
                type(e).__name__,
                str(e)
            )
            return False
        finally:
            self._lock.release()
    
    def _query_dtu(self) -> Optional[Any]:
        """Query DTU for plant data (returns PlantData object)."""
        try:
            logger.info(f"Querying DTU {self.dtu_config.name} at {self.dtu_config.host}:{self.dtu_config.port}")
            
            # Access plant_data property (not a method!)
            plant_data = self.modbus_client.plant_data
            
            if not plant_data:
                logger.error(f"No data received from {self.dtu_config.name}")
                return None
            
            # Get inverters from plant_data
            inverters = plant_data.inverters if hasattr(plant_data, 'inverters') else []
            
            logger.debug(
                f"Received data from {self.dtu_config.name}: "
                f"{len(inverters)} inverters"
            )
            
            return plant_data
            
        except pymodbus_exceptions.ModbusException as e:
            logger.error(f"Modbus error querying {self.dtu_config.name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error querying {self.dtu_config.name}: {e}")
            raise
    
    def _save_plant_data(self, plant_data) -> None:
        """Save plant data to database.
        
        Args:
            plant_data: PlantData object from DTU
        """
        try:
            # plant_data is a PlantData object, not a dict
            inverters = plant_data.inverters if hasattr(plant_data, 'inverters') else []
            
            for inverter in inverters:
                serial_number = inverter.serial_number
                if not serial_number:
                    continue
                
                # Build inverter data dict
                inverter_data = {
                    'grid_voltage': getattr(inverter, 'grid_voltage', None),
                    'grid_frequency': getattr(inverter, 'grid_frequency', None),
                    'temperature': getattr(inverter, 'temperature', None),
                    'operating_status': getattr(inverter, 'operating_status', None),
                    'alarm_code': getattr(inverter, 'alarm_code', None),
                    'alarm_count': getattr(inverter, 'alarm_count', None),
                    'link_status': getattr(inverter, 'link_status', None),
                }
                
                # Save inverter data
                self.persistence.save_inverter_data(
                    serial_number=serial_number,
                    dtu_name=self.dtu_config.name,
                    data=inverter_data,
                )
                
                # Save port data
                port_num = getattr(inverter, 'port_number', 1)
                port_data = {
                    'pv_voltage': getattr(inverter, 'pv_voltage', None),
                    'pv_current': getattr(inverter, 'pv_current', None),
                    'pv_power': getattr(inverter, 'pv_power', None),
                    'today_production': getattr(inverter, 'today_production', 0),
                    'total_production': getattr(inverter, 'total_production', 0),
                }
                
                self.persistence.save_port_data(
                    serial_number=serial_number,
                    port_number=port_num,
                    data=port_data,
                )
                
                # Update production cache
                self.persistence.save_production_cache(
                    serial_number=serial_number,
                    port_number=port_num,
                    today_production=port_data['today_production'],
                    total_production=port_data['total_production'],
                )
            
            logger.debug(f"Saved data for {len(inverters)} inverters to database")
            
        except Exception as e:
            logger.error(f"Error saving plant data: {e}", exc_info=True)


class MultiDtuCoordinator:
    """Coordinator for managing multiple DTU query jobs."""
    
    def __init__(
        self,
        config: AppConfig,
        persistence_manager: PersistenceManager,
        health_metrics: HealthMetrics,
        error_recovery: ErrorRecoveryManager,
        websocket_client: Optional[Any] = None,
    ):
        """Initialize multi-DTU coordinator.
        
        Args:
            config: Application configuration
            persistence_manager: Database persistence manager
            health_metrics: Health metrics tracker
            error_recovery: Error recovery manager
            websocket_client: Optional WebSocket client for push updates
        """
        self.config = config
        self.persistence = persistence_manager
        self.health_metrics = health_metrics
        self.error_recovery = error_recovery
        self.websocket_client = websocket_client
        self.jobs: List[DtuQueryJob] = []
        self.last_reset_check = datetime.now()
        
        # Initialize jobs for each DTU
        self._initialize_jobs()
    
    def _initialize_jobs(self) -> None:
        """Initialize query jobs for all DTUs."""
        dtu_configs = self.config.get_dtu_configs()
        modbus_config = self.config.get_modbus_config()
        
        for dtu_config in dtu_configs:
            try:
                # Create Modbus client for this DTU
                modbus_client = HoymilesModbusTCP(
                    host=dtu_config.host,
                    port=dtu_config.port,
                    unit_id=dtu_config.unit_id,
                )
                
                # Create query job
                job = DtuQueryJob(
                    dtu_config=dtu_config,
                    modbus_client=modbus_client,
                    health_metrics=self.health_metrics,
                    error_recovery=self.error_recovery,
                    persistence_manager=self.persistence,
                    config=self.config,
                )
                
                self.jobs.append(job)
                logger.info(f"Initialized query job for DTU {dtu_config.name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize DTU {dtu_config.name}: {e}")
    
    def execute_all(self) -> Dict[str, bool]:
        """Execute all query jobs.
        
        Returns:
            Dictionary mapping DTU name to success status
        """
        results = {}
        threads = []
        
        # Check for daily reset
        self._check_daily_reset()
        
        # Execute jobs in parallel
        for job in self.jobs:
            thread = threading.Thread(
                target=lambda j=job: results.update({j.dtu_config.name: j.execute()}),
                daemon=True,
            )
            thread.start()
            threads.append(thread)
        
        # Wait for all jobs to complete
        for thread in threads:
            thread.join(timeout=60)  # 60 second timeout per job
        
        # Send WebSocket update if enabled and at least one job succeeded
        if self.websocket_client and any(results.values()):
            self._send_websocket_update()
        
        return results
    
    def _send_websocket_update(self) -> None:
        """Send update to registered WebSockets."""
        try:
            # Gather data to send - use enriched data with latest readings and ports
            inverters = self.persistence.get_all_inverters_with_data()
            stats = self.persistence.get_statistics()
            health_status = self.health_metrics.get_health_status()
            
            logger.debug(
                f"Preparing WebSocket push: {len(inverters)} inverters, "
                f"{sum(len(inv.get('ports', [])) for inv in inverters)} total ports"
            )
            
            # Create payload
            payload = {
                "health": health_status,
                "stats": stats,
                "inverters": inverters,
            }
            
            # Send WebSocket update asynchronously
            import asyncio
            import threading
            
            def send_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.websocket_client.send_update(payload))
                    logger.info(f"Successfully pushed data via WebSocket to {len(self.websocket_client.connections)} connections")
                except Exception as e:
                    logger.error(f"Error sending WebSocket update: {e}")
                finally:
                    loop.close()
            
            thread = threading.Thread(target=send_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logger.error(f"Error preparing WebSocket update: {e}", exc_info=True)
    
    def _check_daily_reset(self) -> None:
        """Check if daily production should be reset."""
        try:
            tz = pytz.timezone(self.config.timezone)
            now = datetime.now(tz)
            
            # Check if we've crossed the reset hour
            if (now.hour == self.config.reset_hour and 
                self.last_reset_check.hour != self.config.reset_hour):
                
                logger.info(f"Daily reset triggered at {now}")
                self.persistence.clear_today_production()
                self.last_reset_check = now
            else:
                self.last_reset_check = now
                
        except Exception as e:
            logger.error(f"Error checking daily reset: {e}")


def run_periodic_coordinator(
    coordinator: MultiDtuCoordinator,
    query_period: int,
    stop_event: threading.Event,
) -> None:
    """Run coordinator periodically until stop event is set.
    
    Args:
        coordinator: Multi-DTU coordinator
        query_period: Query period in seconds
        stop_event: Event to signal shutdown
    """
    logger.info(f"Starting periodic queries every {query_period}s")
    
    while not stop_event.is_set():
        try:
            # Execute all queries
            results = coordinator.execute_all()
            
            # Log results
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(
                f"Query cycle complete: {success_count}/{total_count} successful"
            )
            
        except Exception as e:
            logger.exception(f"Error in query cycle: {e}")
        
        # Wait for next cycle (check stop event periodically)
        for _ in range(query_period):
            if stop_event.is_set():
                break
            time.sleep(1)
    
    logger.info("Periodic query loop stopped")


def setup_signal_handlers(stop_event: threading.Event) -> None:
    """Setup signal handlers for graceful shutdown.
    
    Args:
        stop_event: Event to signal shutdown
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
