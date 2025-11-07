"""Data update coordinator for Hoymiles S-Miles."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, ENDPOINT_HEALTH, ENDPOINT_STATS, ENDPOINT_INVERTERS

_LOGGER = logging.getLogger(__name__)


class HoymilesSmilesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from Hoymiles S-Miles API."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        scan_interval: int,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.entry_id = entry_id
        self._session: aiohttp.ClientSession | None = None
        self._consecutive_failures = 0
        self._last_push_update: float = 0
        self._push_data: dict[str, Any] | None = None
        self._ws: Any = None  # WebSocket connection from bridge
        
        # Generate authentication token for WebSocket
        import secrets
        self._ws_token = secrets.token_urlsafe(32)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=15)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    limit=10,
                    ttl_dns_cache=300,
                    force_close=False,
                ),
            )
            _LOGGER.debug("Created new aiohttp session for %s:%s", self.host, self.port)
        return self._session

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API (used as fallback when push updates are stale)."""
        import time
        start_time = time.time()
        
        # Check if we have recent push data (less than 2x the update interval)
        time_since_push = time.time() - self._last_push_update
        max_push_age = self.update_interval.total_seconds() * 2
        
        if self._push_data and time_since_push < max_push_age:
            _LOGGER.info(
                "[Push Data] Using pushed data from bridge (age: %.1fs, max: %.1fs, inverters: %d)",
                time_since_push, max_push_age, len(self._push_data.get("inverters", []))
            )
            return self._push_data
        
        # Fall back to polling if push data is stale or missing
        if self._push_data:
            _LOGGER.warning(
                "[Fallback Poll] Push data is stale (%.1fs old), falling back to polling. "
                "Check if bridge WebSocket connection is working.",
                time_since_push
            )
        else:
            _LOGGER.warning(
                "[Poll] No push data available, polling API. "
                "WebSocket push may not be configured or connected."
            )
        
        _LOGGER.debug(
            "[API Call Start] Fetching data from %s:%s (session_active=%s, consecutive_failures=%d)",
            self.host, self.port,
            self._session is not None and not self._session.closed,
            self._consecutive_failures
        )
        
        try:
            session = await self._get_session()
            
            # Use a longer timeout - 20 seconds total
            async with async_timeout.timeout(20):
                # Fetch health data with retry
                _LOGGER.debug("[API Call] Fetching %s from %s:%s", ENDPOINT_HEALTH, self.host, self.port)
                health_data = await self._fetch_endpoint_with_retry(session, ENDPOINT_HEALTH)
                _LOGGER.debug("[API Call] Received health data: healthy=%s, uptime=%s",
                             health_data.get("healthy"), health_data.get("uptime_seconds"))
                
                # Fetch stats data with retry
                _LOGGER.debug("[API Call] Fetching %s from %s:%s", ENDPOINT_STATS, self.host, self.port)
                stats_data = await self._fetch_endpoint_with_retry(session, ENDPOINT_STATS)
                _LOGGER.debug("[API Call] Received stats data: records=%s", 
                             stats_data.get("total_records"))
                
                # Fetch inverters data with retry
                _LOGGER.debug("[API Call] Fetching %s from %s:%s", ENDPOINT_INVERTERS, self.host, self.port)
                inverters_data = await self._fetch_endpoint_with_retry(session, ENDPOINT_INVERTERS)
                _LOGGER.debug("[API Call] Received inverters data: count=%s", len(inverters_data) if inverters_data else 0)
                
                # Reset failure counter on success
                if self._consecutive_failures > 0:
                    _LOGGER.info(
                        "Successfully reconnected to %s:%s after %d failures",
                        self.host, self.port, self._consecutive_failures
                    )
                self._consecutive_failures = 0
                
                elapsed = time.time() - start_time
                _LOGGER.debug(
                    "[API Call Complete] Success in %.2fs from %s:%s",
                    elapsed, self.host, self.port
                )
                
                # Combine data
                return {
                    "health": health_data,
                    "stats": stats_data,
                    "inverters": inverters_data or [],
                    "available": True,
                }
        except asyncio.TimeoutError as err:
            import time
            elapsed = time.time() - start_time
            self._consecutive_failures += 1
            _LOGGER.warning(
                "[API Call Failed] Timeout after %.2fs from %s:%s (failure %d): %s",
                elapsed, self.host, self.port, self._consecutive_failures, err
            )
            _LOGGER.debug(
                "[API Call Failed] Session state: active=%s, closed=%s",
                self._session is not None,
                self._session.closed if self._session else "N/A"
            )
            # Close session on timeout to force fresh connection next time
            if self._session and not self._session.closed:
                _LOGGER.debug("[Session] Closing session due to timeout")
                await self._session.close()
                self._session = None
            raise UpdateFailed(f"Timeout communicating with API: {err}") from err
        except aiohttp.ClientError as err:
            import time
            elapsed = time.time() - start_time
            self._consecutive_failures += 1
            _LOGGER.warning(
                "[API Call Failed] Client error after %.2fs from %s:%s (failure %d): %s",
                elapsed, self.host, self.port, self._consecutive_failures, err
            )
            _LOGGER.debug(
                "[API Call Failed] Error type: %s, Session: %s",
                type(err).__name__,
                "active" if (self._session and not self._session.closed) else "closed/none"
            )
            # Close session on client error
            if self._session and not self._session.closed:
                _LOGGER.debug("[Session] Closing session due to client error")
                await self._session.close()
                self._session = None
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            import time
            elapsed = time.time() - start_time
            self._consecutive_failures += 1
            _LOGGER.error(
                "[API Call Failed] Unexpected error after %.2fs from %s:%s (failure %d): %s",
                elapsed, self.host, self.port, self._consecutive_failures, err,
                exc_info=True
            )
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_endpoint_with_retry(
        self, session: aiohttp.ClientSession, endpoint: str, max_retries: int = 2
    ) -> dict[str, Any]:
        """Fetch data from a specific endpoint with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self._fetch_endpoint(session, endpoint)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                last_error = err
                if attempt < max_retries - 1:
                    wait_time = 0.5 * (attempt + 1)  # 0.5s, 1s
                    _LOGGER.debug(
                        "Retry %d/%d for %s after %s, waiting %.1fs",
                        attempt + 1, max_retries, endpoint, err, wait_time
                    )
                    await asyncio.sleep(wait_time)
                else:
                    _LOGGER.warning(
                        "All %d retries failed for %s: %s",
                        max_retries, endpoint, err
                    )
        
        # All retries failed
        raise last_error

    async def _fetch_endpoint(
        self, session: aiohttp.ClientSession, endpoint: str
    ) -> dict[str, Any]:
        """Fetch data from a specific endpoint."""
        import time
        url = f"{self.base_url}{endpoint}"
        fetch_start = time.time()
        
        _LOGGER.debug("[HTTP] GET %s", url)
        
        try:
            async with session.get(url) as response:
                status = response.status
                fetch_time = time.time() - fetch_start
                
                _LOGGER.debug(
                    "[HTTP] Response %d from %s in %.3fs",
                    status, endpoint, fetch_time
                )
                
                response.raise_for_status()
                data = await response.json()
                
                _LOGGER.debug(
                    "[HTTP] Successfully parsed JSON from %s (%d bytes)",
                    endpoint, len(str(data))
                )
                
                return data
        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "[HTTP] Response error %d from %s: %s",
                err.status, endpoint, err.message
            )
            raise
        except asyncio.TimeoutError:
            _LOGGER.error("[HTTP] Timeout for %s", endpoint)
            raise
        except Exception as err:
            _LOGGER.error(
                "[HTTP] Unexpected error for %s: %s",
                endpoint, err, exc_info=True
            )
            raise

    def get_health_data(self) -> dict[str, Any] | None:
        """Get health data from coordinator."""
        if self.data and "health" in self.data:
            return self.data["health"]
        return None

    def get_stats_data(self) -> dict[str, Any] | None:
        """Get stats data from coordinator."""
        if self.data and "stats" in self.data:
            return self.data["stats"]
        return None

    def get_dtu_data(self, dtu_name: str = "DTU") -> dict[str, Any] | None:
        """Get DTU-specific data."""
        health = self.get_health_data()
        if health and "dtus" in health and dtu_name in health["dtus"]:
            return health["dtus"][dtu_name]
        return None

    def get_inverters(self) -> list[dict[str, Any]]:
        """Get all inverters data from coordinator."""
        if self.data and "inverters" in self.data:
            return self.data["inverters"]
        return []
    
    def get_inverter_data(self, serial_number: str) -> dict[str, Any] | None:
        """Get data for a specific inverter from cached coordinator data.
        
        This uses the pushed/cached data, not making API calls.
        
        Args:
            serial_number: Inverter serial number
            
        Returns:
            Inverter data dict or None if not found
        """
        inverters = self.get_inverters()
        for inverter in inverters:
            if inverter.get("serial_number") == serial_number:
                return inverter
        return None
    
    def get_port_data(self, serial_number: str, port_number: int) -> dict[str, Any] | None:
        """Get data for a specific port from cached coordinator data.
        
        This uses the pushed/cached data, not making API calls.
        
        Args:
            serial_number: Inverter serial number
            port_number: Port number
            
        Returns:
            Port data dict or None if not found
        """
        inverter = self.get_inverter_data(serial_number)
        if not inverter:
            return None
        
        ports = inverter.get("ports", [])
        for port in ports:
            if port.get("port_number") == port_number:
                return port
        return None

    async def get_inverter_latest_data(self, serial_number: str) -> dict[str, Any] | None:
        """Get latest data for a specific inverter including port data.
        
        DEPRECATED: This method makes API calls. Use get_inverter_data() instead for cached data.
        This is only used during initial setup to discover port numbers.
        """
        try:
            session = await self._get_session()
            endpoint = f"/api/inverters/{serial_number}"
            
            # Fetch inverter data
            inverter_data = await self._fetch_endpoint(session, endpoint)
            
            # Fetch port data
            ports_endpoint = f"{endpoint}/ports"
            try:
                ports_data = await self._fetch_endpoint(session, ports_endpoint)
                inverter_data["ports"] = ports_data
            except Exception as err:
                _LOGGER.debug("Could not fetch port data for %s: %s", serial_number, err)
                inverter_data["ports"] = []
            
            return inverter_data
        except Exception as err:
            _LOGGER.error("Failed to get inverter data for %s: %s", serial_number, err)
            return None

    def is_available(self) -> bool:
        """Check if the API is available."""
        return self.data is not None and self.data.get("available", False)

    async def async_handle_push_update(self, data: dict[str, Any]) -> None:
        """Handle pushed data update from webhook.
        
        Args:
            data: Pushed data from the bridge
        """
        import time
        
        inverters = data.get("inverters", [])
        total_ports = sum(len(inv.get("ports", [])) for inv in inverters)
        
        _LOGGER.info(
            "[WebSocket Push] ✓ Received data from bridge: %d inverters, %d ports",
            len(inverters), total_ports
        )
        
        # Store push data
        self._push_data = {
            "health": data.get("health", {}),
            "stats": data.get("stats", {}),
            "inverters": inverters,
            "available": True,
        }
        self._last_push_update = time.time()
        
        # Reset consecutive failures on successful push
        if self._consecutive_failures > 0:
            _LOGGER.info(
                "[WebSocket Push] Connection restored after %d failures",
                self._consecutive_failures
            )
            self._consecutive_failures = 0
        
        # Update coordinator data and notify listeners
        self.async_set_updated_data(self._push_data)
        
        _LOGGER.debug(
            "[WebSocket Push] Successfully updated %d sensors", 
            len(self._listeners)
        )

    def get_ws_token(self) -> str:
        """Get WebSocket authentication token."""
        return self._ws_token
    
    def get_websocket_url(self) -> str:
        """Get WebSocket URL for bridge to connect to."""
        # Get Home Assistant external URL or internal URL
        from homeassistant.helpers.network import get_url
        
        try:
            base_url = get_url(self.hass, prefer_external=False)
        except Exception:
            # Fallback to internal URL
            base_url = f"http://{self.hass.config.internal_url or 'homeassistant.local:8123'}"
        
        # Construct WebSocket URL
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_url}/api/hoymiles_smiles/ws?token={self._ws_token}"
    
    def set_websocket(self, ws: Any) -> None:
        """Set WebSocket connection.
        
        Args:
            ws: WebSocket connection or None to clear
        """
        self._ws = ws
        if ws:
            _LOGGER.info("WebSocket connection established")
        else:
            _LOGGER.info("WebSocket connection closed")
    
    async def register_websocket_with_bridge(self, ws_url: str) -> None:
        """Send WebSocket URL to bridge for connection.
        
        Args:
            ws_url: Full WebSocket URL for the bridge to connect to
        """
        try:
            session = await self._get_session()
            endpoint = "/api/websocket/register"
            url = f"{self.base_url}{endpoint}"
            
            payload = {
                "websocket_url": ws_url,
                "name": "Home Assistant",
            }
            
            _LOGGER.info(
                "[WebSocket Registration] Registering with bridge at %s:%s",
                self.host, self.port
            )
            _LOGGER.debug("[WebSocket Registration] URL: %s", ws_url)
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.info(
                        "[WebSocket Registration] ✓ Successfully registered with bridge. "
                        "Push updates are enabled."
                    )
                elif response.status == 404:
                    _LOGGER.error(
                        "[WebSocket Registration] ✗ Bridge does not support WebSocket endpoint (/api/websocket/register). "
                        "Push updates will NOT work - sensors will poll API instead. "
                        "This may cause performance issues."
                    )
                else:
                    _LOGGER.error(
                        "[WebSocket Registration] ✗ Failed to register with bridge (HTTP %d). "
                        "Push updates will NOT work - falling back to polling only.",
                        response.status
                    )
        except Exception as err:
            _LOGGER.error(
                "[WebSocket Registration] ✗ Could not register with bridge: %s. "
                "Push updates will NOT work - falling back to polling only. "
                "Check bridge connectivity.",
                err
            )

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and cleanup resources."""
        if self._session and not self._session.closed:
            _LOGGER.debug("Closing aiohttp session for %s:%s", self.host, self.port)
            await self._session.close()
            self._session = None

