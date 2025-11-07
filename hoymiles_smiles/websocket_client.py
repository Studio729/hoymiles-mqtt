"""WebSocket client for pushing real-time updates to Home Assistant."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class WebSocketClient:
    """Client for maintaining WebSocket connections to Home Assistant."""
    
    def __init__(self, enabled: bool = True):
        """Initialize WebSocket client.
        
        Args:
            enabled: Whether WebSocket is enabled
        """
        self.enabled = enabled
        self.connections: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._tasks: List[asyncio.Task] = []
    
    async def register_websocket(self, ws_url: str, name: str = "Unknown") -> None:
        """Register a WebSocket endpoint and maintain connection.
        
        Args:
            ws_url: Full WebSocket URL
            name: Name/description of the connection
        """
        async with self._lock:
            # Check if already registered
            for conn in self.connections:
                if conn["url"] == ws_url:
                    logger.debug("WebSocket %s already registered", ws_url)
                    return
            
            connection = {
                "url": ws_url,
                "name": name,
                "connected": False,
                "ws": None,
                "reconnect_attempts": 0,
            }
            
            self.connections.append(connection)
            
            logger.info("Registered WebSocket: %s (%s)", name, ws_url)
            
            # Start connection task
            task = asyncio.create_task(self._maintain_connection(connection))
            self._tasks.append(task)
    
    async def _maintain_connection(self, connection: Dict[str, Any]) -> None:
        """Maintain WebSocket connection with automatic reconnection.
        
        Args:
            connection: Connection configuration
        """
        ws_url = connection["url"]
        name = connection["name"]
        
        while self.enabled:
            try:
                # Calculate backoff delay
                if connection["reconnect_attempts"] > 0:
                    # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
                    delay = min(2 ** (connection["reconnect_attempts"] - 1), 30)
                    logger.info(
                        "Reconnecting to %s in %d seconds (attempt %d)...",
                        name, delay, connection["reconnect_attempts"] + 1
                    )
                    await asyncio.sleep(delay)
                
                logger.info("[WebSocket] Connecting to %s (%s)", name, ws_url)
                
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.ws_connect(
                            ws_url,
                            heartbeat=30,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as ws:
                            connection["ws"] = ws
                            connection["connected"] = True
                            connection["reconnect_attempts"] = 0
                            
                            logger.info("[WebSocket] ✓ Connected to: %s", name)
                            
                            # Send initial ping
                            logger.debug("[WebSocket] Sending initial ping to %s", name)
                            await ws.send_json({"type": "ping"})
                            
                            # Keep connection alive and handle messages
                            logger.debug("[WebSocket] Listening for messages from %s", name)
                            async for msg in ws:
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    logger.debug("[WebSocket] Received message from %s: %d bytes", name, len(msg.data))
                                    await self._handle_message(connection, msg.data)
                                elif msg.type == aiohttp.WSMsgType.ERROR:
                                    logger.error(
                                        "[WebSocket] Error for %s: %s",
                                        name, ws.exception()
                                    )
                                    break
                                elif msg.type in (
                                    aiohttp.WSMsgType.CLOSE,
                                    aiohttp.WSMsgType.CLOSED,
                                    aiohttp.WSMsgType.CLOSING,
                                ):
                                    logger.info("[WebSocket] Connection closed: %s", name)
                                    break
                            
                            connection["connected"] = False
                            connection["ws"] = None
                    
                    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                        connection["connected"] = False
                        connection["ws"] = None
                        connection["reconnect_attempts"] += 1
                        logger.warning(
                            "[WebSocket] Connection failed for %s: %s (attempt %d)",
                            name, err, connection["reconnect_attempts"]
                        )
                        # Raise to trigger reconnect
                        raise
                        
            except asyncio.CancelledError:
                logger.info("WebSocket connection task cancelled for %s", name)
                break
            
            except Exception as err:
                connection["connected"] = False
                connection["ws"] = None
                connection["reconnect_attempts"] += 1
                logger.exception(
                    "Unexpected error in WebSocket connection for %s: %s",
                    name, err
                )
            
            # If we get here, connection was lost
            if self.enabled:
                logger.warning("[WebSocket] Disconnected from %s, will reconnect", name)
    
    async def _handle_message(self, connection: Dict[str, Any], message: str) -> None:
        """Handle incoming WebSocket message.
        
        Args:
            connection: Connection configuration
            message: Raw message string
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "pong":
                # Pong response
                logger.debug("Received pong from %s", connection["name"])
            else:
                logger.debug(
                    "Received message from %s: %s",
                    connection["name"], message_type
                )
        
        except json.JSONDecodeError as err:
            logger.error("Invalid JSON from %s: %s", connection["name"], err)
        except Exception as err:
            logger.exception("Error handling message from %s: %s", connection["name"], err)
    
    async def send_update(self, data: Dict[str, Any]) -> None:
        """Send data update to all connected WebSockets.
        
        Args:
            data: Data to send
        """
        if not self.enabled:
            return
        
        # Send to all connected WebSockets
        tasks = []
        for connection in self.connections:
            if connection["connected"] and connection["ws"]:
                tasks.append(self._send_to_connection(connection, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_connection(
        self, connection: Dict[str, Any], data: Dict[str, Any]
    ) -> None:
        """Send data to a specific WebSocket connection.
        
        Args:
            connection: Connection configuration
            data: Data to send
        """
        ws = connection["ws"]
        name = connection["name"]
        
        if not ws:
            return
        
        try:
            message = {
                "type": "update",
                "data": data,
            }
            
            inverter_count = len(data.get("inverters", []))
            port_count = sum(len(inv.get("ports", [])) for inv in data.get("inverters", []))
            
            logger.info(
                "[WebSocket] Sending update to %s: %d inverters, %d ports",
                name, inverter_count, port_count
            )
            
            await ws.send_json(message)
            
            logger.info("[WebSocket] ✓ Successfully sent update to %s", name)
        
        except Exception as err:
            logger.error(
                "Failed to send WebSocket message to %s: %s",
                name, err
            )
            connection["connected"] = False
            connection["ws"] = None
    
    async def close(self) -> None:
        """Close all WebSocket connections and cleanup resources."""
        self.enabled = False
        
        # Cancel all connection tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close all WebSocket connections
        for connection in self.connections:
            if connection["ws"] and not connection["ws"].closed:
                await connection["ws"].close()
        
        self.connections.clear()
        self._tasks.clear()
        
        logger.info("WebSocket client closed")

