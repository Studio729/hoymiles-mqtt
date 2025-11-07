"""WebSocket server for receiving real-time updates from the bridge."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import web, WSMsgType
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HoymilesSmilesCoordinator

_LOGGER = logging.getLogger(__name__)

WEBSOCKET_PATH = "/api/hoymiles_smiles/ws"


class HoymilesWebSocketView(HomeAssistantView):
    """WebSocket view for receiving bridge updates."""

    url = WEBSOCKET_PATH
    name = "api:hoymiles_smiles:ws"
    requires_auth = False  # We'll implement token-based auth

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the WebSocket view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        # Get auth token from query params
        auth_token = request.query.get("token")
        
        # Find coordinator by matching auth token
        coordinator = self._find_coordinator_by_token(auth_token)
        
        if not coordinator:
            _LOGGER.error("Invalid or missing auth token for WebSocket connection")
            await ws.send_json({"error": "Invalid authentication token"})
            await ws.close()
            return ws

        coordinator_entry_id = None
        for entry_id, coord in self.hass.data[DOMAIN].items():
            if coord == coordinator:
                coordinator_entry_id = entry_id
                break

        _LOGGER.info(
            "[WebSocket Server] ✓ Connection established from bridge (%s) for entry %s",
            request.remote,
            coordinator_entry_id,
        )

        # Store WebSocket connection in coordinator
        coordinator.set_websocket(ws)
        
        # Send initial ack
        await ws.send_json({"type": "connected", "status": "ready"})

        try:
            # Handle messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(coordinator, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    _LOGGER.error(
                        "WebSocket connection error: %s",
                        ws.exception(),
                    )
                    break
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                    _LOGGER.info("WebSocket connection closing")
                    break

        except Exception as err:
            _LOGGER.exception("Error in WebSocket handler: %s", err)
        finally:
            # Clean up connection
            coordinator.set_websocket(None)
            _LOGGER.info("WebSocket connection closed for entry %s", coordinator_entry_id)

        return ws

    def _find_coordinator_by_token(self, token: str | None) -> HoymilesSmilesCoordinator | None:
        """Find coordinator by auth token.
        
        Args:
            token: Authentication token
            
        Returns:
            Coordinator if found, None otherwise
        """
        if not token or DOMAIN not in self.hass.data:
            return None

        for entry_id, coordinator in self.hass.data[DOMAIN].items():
            if isinstance(coordinator, HoymilesSmilesCoordinator):
                if coordinator.get_ws_token() == token:
                    return coordinator

        return None

    async def _handle_message(
        self,
        coordinator: HoymilesSmilesCoordinator,
        message: str,
    ) -> None:
        """Handle incoming WebSocket message.
        
        Args:
            coordinator: The coordinator instance
            message: Raw message string
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")

            _LOGGER.debug(
                "[WebSocket Server] Received message type: %s (size: %d bytes)",
                message_type, len(message)
            )

            if message_type == "update":
                # Data update from bridge
                payload = data.get("data", {})
                inverter_count = len(payload.get("inverters", []))
                
                _LOGGER.info(
                    "[WebSocket Server] Processing update: %d inverters, %d ports",
                    inverter_count,
                    sum(len(inv.get("ports", [])) for inv in payload.get("inverters", []))
                )
                
                await coordinator.async_handle_push_update(payload)
                
                _LOGGER.info("[WebSocket Server] ✓ Update processed successfully")

            elif message_type == "ping":
                # Respond to ping (coordinator stores the ws connection)
                _LOGGER.debug("[WebSocket Server] Ping received, sending pong")
                # The WebSocket response will be handled by the bridge's ping handler

            else:
                _LOGGER.warning(
                    "[WebSocket Server] Unknown message type: %s",
                    message_type
                )

        except json.JSONDecodeError as err:
            _LOGGER.error(
                "[WebSocket Server] Invalid JSON in message: %s",
                err
            )
            _LOGGER.debug("[WebSocket Server] Raw message: %s", message[:500])
        except Exception as err:
            _LOGGER.exception(
                "[WebSocket Server] Error handling message: %s",
                err
            )


async def async_setup_websocket(hass: HomeAssistant) -> None:
    """Set up WebSocket server.
    
    Args:
        hass: Home Assistant instance
    """
    view = HoymilesWebSocketView(hass)
    hass.http.register_view(view)
    
    _LOGGER.info(
        "[WebSocket Server] Server registered at %s - Ready to accept bridge connections",
        WEBSOCKET_PATH
    )

