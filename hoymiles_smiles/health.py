"""Health check HTTP server with Prometheus metrics."""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


# Prometheus metrics
QUERY_TOTAL = Counter('hoymiles_queries_total', 'Total number of DTU queries', ['dtu_name', 'status'])
QUERY_DURATION = Histogram('hoymiles_query_duration_seconds', 'DTU query duration', ['dtu_name'])
QUERY_ERRORS = Counter('hoymiles_query_errors_total', 'Total number of query errors', ['dtu_name', 'error_type'])
DTU_AVAILABLE = Gauge('hoymiles_dtu_available', 'DTU availability (1=available, 0=unavailable)', ['dtu_name'])
INVERTER_POWER = Gauge('hoymiles_inverter_power_watts', 'Current inverter power', ['serial_number', 'port'])
INVERTER_TEMPERATURE = Gauge('hoymiles_inverter_temperature_celsius', 'Inverter temperature', ['serial_number'])
INVERTER_STATUS = Gauge('hoymiles_inverter_status', 'Inverter operating status', ['serial_number'])
DTU_POWER = Gauge('hoymiles_dtu_power_watts', 'Total DTU power output', ['dtu_name'])
TODAY_PRODUCTION = Gauge('hoymiles_today_production_wh', 'Today energy production', ['dtu_name'])
TOTAL_PRODUCTION = Gauge('hoymiles_total_production_wh', 'Total lifetime production', ['dtu_name'])
UPTIME = Gauge('hoymiles_smiles_uptime_seconds', 'Application uptime')
CIRCUIT_BREAKER_STATE = Gauge('hoymiles_circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open)', ['dtu_name'])


class HealthMetrics:
    """Application health metrics."""
    
    def __init__(self):
        """Initialize health metrics."""
        self.start_time = time.time()
        self.last_successful_query: Dict[str, float] = {}
        self.last_error: Dict[str, str] = {}
        self.last_error_time: Dict[str, float] = {}
        self.query_count: Dict[str, int] = {}
        self.error_count: Dict[str, int] = {}
        self.dtu_status: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    def record_query_success(self, dtu_name: str, duration: float) -> None:
        """Record successful query.
        
        Args:
            dtu_name: DTU name
            duration: Query duration in seconds
        """
        with self._lock:
            self.last_successful_query[dtu_name] = time.time()
            self.query_count[dtu_name] = self.query_count.get(dtu_name, 0) + 1
            self.dtu_status[dtu_name] = 'online'
            
            QUERY_TOTAL.labels(dtu_name=dtu_name, status='success').inc()
            QUERY_DURATION.labels(dtu_name=dtu_name).observe(duration)
            DTU_AVAILABLE.labels(dtu_name=dtu_name).set(1)
    
    def record_query_error(self, dtu_name: str, error_type: str, error_msg: str) -> None:
        """Record query error.
        
        Args:
            dtu_name: DTU name
            error_type: Type of error
            error_msg: Error message
        """
        with self._lock:
            self.last_error[dtu_name] = error_msg
            self.last_error_time[dtu_name] = time.time()
            self.error_count[dtu_name] = self.error_count.get(dtu_name, 0) + 1
            self.dtu_status[dtu_name] = 'error'
            
            QUERY_TOTAL.labels(dtu_name=dtu_name, status='error').inc()
            QUERY_ERRORS.labels(dtu_name=dtu_name, error_type=error_type).inc()
            DTU_AVAILABLE.labels(dtu_name=dtu_name).set(0)
    
    def update_inverter_metrics(self, serial_number: str, port: Optional[int], 
                               power: Optional[float], temperature: Optional[float],
                               status: Optional[int]) -> None:
        """Update inverter metrics.
        
        Args:
            serial_number: Inverter serial number
            port: Port number (None for inverter-level metrics)
            power: Power output in watts
            temperature: Temperature in Celsius
            status: Operating status
        """
        if power is not None and port is not None:
            INVERTER_POWER.labels(serial_number=serial_number, port=str(port)).set(power)
        
        if temperature is not None:
            INVERTER_TEMPERATURE.labels(serial_number=serial_number).set(temperature)
        
        if status is not None:
            INVERTER_STATUS.labels(serial_number=serial_number).set(status)
    
    def update_dtu_metrics(self, dtu_name: str, power: float, 
                          today_production: int, total_production: int) -> None:
        """Update DTU-level metrics.
        
        Args:
            dtu_name: DTU name
            power: Current power output
            today_production: Today's production
            total_production: Total production
        """
        DTU_POWER.labels(dtu_name=dtu_name).set(power)
        TODAY_PRODUCTION.labels(dtu_name=dtu_name).set(today_production)
        TOTAL_PRODUCTION.labels(dtu_name=dtu_name).set(total_production)
    
    def update_circuit_breaker_state(self, dtu_name: str, is_open: bool) -> None:
        """Update circuit breaker state.
        
        Args:
            dtu_name: DTU name
            is_open: Whether circuit breaker is open
        """
        CIRCUIT_BREAKER_STATE.labels(dtu_name=dtu_name).set(1 if is_open else 0)
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        uptime = time.time() - self.start_time
        UPTIME.set(uptime)
        return uptime
    
    def is_healthy(self, dtu_offline_threshold: int = 300) -> bool:
        """Check if application is healthy.
        
        Args:
            dtu_offline_threshold: Seconds before considering DTU offline
            
        Returns:
            True if healthy
        """
        with self._lock:
            # If no queries have succeeded yet, we're not healthy
            if not self.last_successful_query:
                return False
            
            # Check if any DTU has had a recent successful query
            current_time = time.time()
            for dtu_name, last_query_time in self.last_successful_query.items():
                if current_time - last_query_time < dtu_offline_threshold:
                    return True
            
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Health status dictionary
        """
        # Copy data quickly while holding lock
        with self._lock:
            current_time = time.time()
            last_successful_query = self.last_successful_query.copy()
            last_error = self.last_error.copy()
            last_error_time = self.last_error_time.copy()
            query_count = self.query_count.copy()
            error_count = self.error_count.copy()
            dtu_status = self.dtu_status.copy()
        
        # Build response outside lock
        uptime = self.get_uptime()
        
        dtu_statuses = {}
        for dtu_name in set(list(last_successful_query.keys()) + list(last_error.keys())):
            last_success = last_successful_query.get(dtu_name)
            error_msg = last_error.get(dtu_name)
            error_time = last_error_time.get(dtu_name)
            
            dtu_statuses[dtu_name] = {
                'status': dtu_status.get(dtu_name, 'unknown'),
                'last_successful_query': datetime.fromtimestamp(last_success, tz=timezone.utc).isoformat() if last_success else None,
                'seconds_since_last_success': int(current_time - last_success) if last_success else None,
                'query_count': query_count.get(dtu_name, 0),
                'error_count': error_count.get(dtu_name, 0),
                'last_error': error_msg,
                'last_error_time': datetime.fromtimestamp(error_time, tz=timezone.utc).isoformat() if error_time else None,
            }
        
        # Return status built from copied data
        return {
            'healthy': self.is_healthy(),
            'uptime_seconds': int(uptime),
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'dtus': dtu_statuses,
        }


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks."""
    
    health_metrics: Optional[HealthMetrics] = None
    persistence_manager: Optional[Any] = None
    websocket_client: Optional[Any] = None
    
    def log_message(self, format: str, *args) -> None:
        """Override to use Python logging."""
        try:
            logger.debug(f"{self.address_string()} - {format % args}")
        except Exception:
            pass  # Silently ignore logging errors
    
    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            # Log API requests (but not health checks to avoid spam)
            if self.path.startswith('/api/'):
                logger.info(f"[API Request] GET {self.path} from {self.client_address[0]}")
            
            if self.path == '/health':
                self._handle_health()
            elif self.path == '/ready':
                self._handle_ready()
            elif self.path == '/metrics':
                self._handle_metrics()
            elif self.path == '/stats':
                self._handle_stats()
            elif self.path.startswith('/api/'):
                self._handle_api()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error(f"Error handling request {self.path}: {e}", exc_info=True)
            try:
                self.send_error(500, "Internal Server Error")
            except:
                pass  # Connection may be closed
    
    def do_POST(self) -> None:
        """Handle POST requests."""
        try:
            if self.path == '/api/websocket/register':
                self._handle_websocket_register()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error(f"Error handling POST {self.path}: {e}", exc_info=True)
            try:
                self.send_error(500, "Internal Server Error")
            except:
                pass  # Connection may be closed
    
    def _handle_health(self) -> None:
        """Handle /health endpoint."""
        if self.health_metrics:
            status = self.health_metrics.get_health_status()
            self.send_response(200 if status['healthy'] else 503)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode())
        else:
            self.send_error(503, "Health metrics not available")
    
    def _handle_ready(self) -> None:
        """Handle /ready endpoint (Kubernetes readiness probe)."""
        if self.health_metrics and self.health_metrics.is_healthy():
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_error(503, "Not Ready")
    
    def _handle_metrics(self) -> None:
        """Handle /metrics endpoint (Prometheus)."""
        self.send_response(200)
        self.send_header('Content-type', CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(generate_latest())
    
    def _handle_stats(self) -> None:
        """Handle /stats endpoint (database statistics)."""
        if self.persistence_manager:
            stats = self.persistence_manager.get_statistics()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode())
        else:
            self.send_error(503, "Persistence manager not available")
    
    def _handle_api(self) -> None:
        """Handle API endpoints for sensor data."""
        if not self.persistence_manager:
            self.send_error(503, "Persistence manager not available")
            return
        
        try:
            # Parse path
            parts = self.path.split('/')
            
            if self.path == '/api/inverters':
                # Get all inverters with enriched data (latest readings + ports)
                inverters = self.persistence_manager.get_all_inverters_with_data()
                self._send_json_response(inverters)
            
            elif self.path.startswith('/api/inverters/') and len(parts) >= 4:
                serial_number = parts[3]
                
                if len(parts) == 4:
                    # Get latest data for specific inverter with enriched data
                    all_inverters = self.persistence_manager.get_all_inverters_with_data()
                    inverter = next((inv for inv in all_inverters if inv.get('serial_number') == serial_number), None)
                    
                    if inverter:
                        self._send_json_response(inverter)
                    else:
                        self.send_error(404, "Inverter not found")
                
                elif parts[4] == 'history':
                    # Get historical data
                    limit = 100
                    if '?limit=' in self.path:
                        try:
                            limit = int(self.path.split('?limit=')[1].split('&')[0])
                        except:
                            pass
                    
                    inverter_data = self.persistence_manager.get_latest_inverter_data(
                        serial_number=serial_number,
                        limit=limit
                    )
                    self._send_json_response(inverter_data)
                
                elif parts[4] == 'ports':
                    # Get all ports for inverter
                    port_data = self.persistence_manager.get_latest_port_data(
                        serial_number=serial_number,
                        limit=10
                    )
                    self._send_json_response(port_data)
                
                else:
                    self.send_error(404, "Not Found")
            
            elif self.path == '/api/ports':
                # Get all port data
                port_data = self.persistence_manager.get_latest_port_data(limit=100)
                self._send_json_response(port_data)
            
            elif self.path == '/api/production/current':
                # Get current production cache
                cache = self.persistence_manager.load_production_cache()
                # Convert tuple keys to dict format
                production_data = []
                for (serial, port), (today, total) in cache.items():
                    production_data.append({
                        'serial_number': serial,
                        'port_number': port,
                        'today_production': today,
                        'total_production': total
                    })
                self._send_json_response(production_data)
            
            else:
                self.send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"Error handling API request {self.path}: {e}", exc_info=True)
            self.send_error(500, str(e))
    
    def _handle_websocket_register(self) -> None:
        """Handle WebSocket registration endpoint."""
        if not self.websocket_client:
            self.send_error(503, "WebSocket client not available")
            return
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            websocket_url = data.get('websocket_url')
            name = data.get('name', 'Unknown')
            
            if not websocket_url:
                self.send_error(400, "Missing websocket_url")
                return
            
            # Register WebSocket (use asyncio.run_coroutine_threadsafe for thread safety)
            import asyncio
            import threading
            
            # Get the event loop from the main thread
            loop = asyncio.new_event_loop()
            
            def register_in_thread():
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.websocket_client.register_websocket(websocket_url, name)
                )
                loop.close()
            
            thread = threading.Thread(target=register_in_thread, daemon=True)
            thread.start()
            thread.join(timeout=5)
            
            logger.info(f"Registered WebSocket: {name} -> {websocket_url}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "registered"}).encode())
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in WebSocket registration: {e}")
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error registering WebSocket: {e}", exc_info=True)
            self.send_error(500, str(e))
    
    def _send_json_response(self, data: Any, default=str) -> None:
        """Send JSON response with proper serialization.
        
        Args:
            data: Data to serialize
            default: Default serializer for complex types
        """
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Allow CORS for Home Assistant
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=default).encode())


class HealthCheckServer:
    """HTTP server for health checks and metrics."""
    
    def __init__(self, host: str, port: int, health_metrics: HealthMetrics,
                 persistence_manager: Optional[Any] = None,
                 websocket_client: Optional[Any] = None):
        """Initialize health check server.
        
        Args:
            host: Server host
            port: Server port
            health_metrics: Health metrics instance
            persistence_manager: Optional persistence manager
            websocket_client: Optional WebSocket client
        """
        self.host = host
        self.port = port
        self.health_metrics = health_metrics
        self.persistence_manager = persistence_manager
        self.websocket_client = websocket_client
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start the health check server."""
        try:
            # Set class variables for handler
            HealthCheckHandler.health_metrics = self.health_metrics
            HealthCheckHandler.persistence_manager = self.persistence_manager
            HealthCheckHandler.websocket_client = self.websocket_client
            
            self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
            
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            
            logger.info(f"Health check server started on {self.host}:{self.port}")
            logger.info(f"  Health: http://{self.host}:{self.port}/health")
            logger.info(f"  Ready: http://{self.host}:{self.port}/ready")
            logger.info(f"  Metrics: http://{self.host}:{self.port}/metrics")
            logger.info(f"  Stats: http://{self.host}:{self.port}/stats")
            logger.info(f"  API: http://{self.host}:{self.port}/api/...")
            
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
    
    def _run_server(self) -> None:
        """Run the HTTP server."""
        try:
            if self.server:
                logger.info("Health check server thread running")
                self.server.serve_forever()
        except Exception as e:
            logger.error(f"Health check server crashed: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop the health check server."""
        if self.server:
            logger.info("Stopping health check server...")
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Health check server stopped")

