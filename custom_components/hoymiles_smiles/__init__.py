"""The Hoymiles S-Miles integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import HoymilesSmilesCoordinator
from .websocket_server import async_setup_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
WEBSOCKET_SETUP_DONE = "websocket_setup_done"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hoymiles S-Miles from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = HoymilesSmilesCoordinator(
        hass=hass,
        host=host,
        port=port,
        scan_interval=scan_interval,
        entry_id=entry.entry_id,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup WebSocket server (only once for all integrations)
    if WEBSOCKET_SETUP_DONE not in hass.data[DOMAIN]:
        await async_setup_websocket(hass)
        hass.data[DOMAIN][WEBSOCKET_SETUP_DONE] = True

    # Send WebSocket connection info to bridge
    ws_url = coordinator.get_websocket_url()
    await coordinator.register_websocket_with_bridge(ws_url)
    
    _LOGGER.info(
        "WebSocket available for push updates at: %s",
        ws_url
    )

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: HoymilesSmilesCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Cleanup coordinator resources (closes WebSocket if connected)
        await coordinator.async_shutdown()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

