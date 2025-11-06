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
            "WebSocket connection established from %s for entry %s",
            request.remote,
            coordinator_entry_id,
        )

        # Store WebSocket connection in coordinator
        coordinator.set_websocket(ws)

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

            if message_type == "update":
                # Data update from bridge
                payload = data.get("data", {})
                _LOGGER.debug(
                    "Received WebSocket update with %d inverters",
                    len(payload.get("inverters", [])),
                )
                await coordinator.async_handle_push_update(payload)

            elif message_type == "ping":
                # Respond to ping
                if coordinator._ws:
                    await coordinator._ws.send_json({"type": "pong"})

            else:
                _LOGGER.warning("Unknown WebSocket message type: %s", message_type)

        except json.JSONDecodeError as err:
            _LOGGER.error("Invalid JSON in WebSocket message: %s", err)
        except Exception as err:
            _LOGGER.exception("Error handling WebSocket message: %s", err)


async def async_setup_websocket(hass: HomeAssistant) -> None:
    """Set up WebSocket server.
    
    Args:
        hass: Home Assistant instance
    """
    view = HoymilesWebSocketView(hass)
    hass.http.register_view(view)
    
    _LOGGER.info("WebSocket server registered at %s", WEBSOCKET_PATH)

