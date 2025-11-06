"""Binary sensor platform for Hoymiles S-Miles."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HoymilesSmilesCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hoymiles S-Miles binary sensors from config entry."""
    coordinator: HoymilesSmilesCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HoymilesSmilesHealthBinarySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class HoymilesSmilesHealthBinarySensor(
    CoordinatorEntity[HoymilesSmilesCoordinator], BinarySensorEntity
):
    """Binary sensor representing overall health status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Hoymiles S-Miles Bridge"

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_healthy"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Hoymiles S-Miles Bridge",
            "manufacturer": "Hoymiles",
            "model": "S-Miles Bridge",
            "sw_version": "1.1.7",
        }
        self._last_availability = None  # Track availability changes

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        
        # Schedule initial state write after entity is fully registered
        # Add a small delay to ensure recorder is ready
        async def write_initial_state():
            """Write initial state after recorder is ready."""
            import asyncio
            # Wait a moment for recorder to fully register the entity
            await asyncio.sleep(0.5)
            
            _LOGGER.info(
                "[Initial State] Writing initial state for Hoymiles S-Miles Bridge sensor: %s (available=%s)",
                "on" if self.is_on else "off",
                self.available
            )
            self.async_write_ha_state()
            
            # Force another write after 1 second to be absolutely sure
            await asyncio.sleep(1)
            _LOGGER.debug("[Initial State] Writing second state to ensure history capture")
            self.async_write_ha_state()
        
        # Schedule for execution
        self.hass.async_create_task(write_initial_state())

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on (healthy)."""
        health = self.coordinator.get_health_data()
        if health:
            return health.get("healthy", False)
        return False

    @property
    def icon(self) -> str:
        """Return the icon based on state."""
        if self.is_on:
            return "mdi:check-circle"
        return "mdi:alert-circle"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        is_available = self.coordinator.last_update_success and self.coordinator.is_available()
        
        # Log availability changes for debugging
        if hasattr(self, '_last_availability') and self._last_availability != is_available:
            _LOGGER.info(
                "[Availability Change] Hoymiles S-Miles Bridge sensor: %s → %s (last_update_success=%s, coordinator_available=%s)",
                "available" if self._last_availability else "unavailable",
                "available" if is_available else "unavailable",
                self.coordinator.last_update_success,
                self.coordinator.is_available()
            )
        
        self._last_availability = is_available
        return is_available

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        health = self.coordinator.get_health_data()
        if not health:
            return {}

        dtu_data = self.coordinator.get_dtu_data()
        
        attributes = {
            "uptime_seconds": health.get("uptime_seconds"),
            "start_time": health.get("start_time"),
        }

        if dtu_data:
            attributes.update({
                "dtu_status": dtu_data.get("status", "unknown"),
                "dtu_last_query": dtu_data.get("seconds_since_last_success"),
                "dtu_query_count": dtu_data.get("query_count"),
                "dtu_error_count": dtu_data.get("error_count"),
            })

        return attributes

