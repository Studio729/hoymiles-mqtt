"""Sensor platform for Hoymiles S-Miles."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    INVERTER_SENSOR_TYPES,
    INVERTER_AGGREGATE_SENSORS,
    PORT_SENSOR_TYPES,
    DTU_SENSOR_TYPES,
    OPERATING_STATUS_MAP,
    LINK_STATUS_MAP,
    ALARM_CODE_MAP,
)
from .coordinator import HoymilesSmilesCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class HoymilesSmilesSensorEntityDescription(SensorEntityDescription):
    """Describe Hoymiles S-Miles sensor entity."""

    value_fn: Callable[[HoymilesSmilesCoordinator], StateType] = None
    attributes_fn: Callable[[HoymilesSmilesCoordinator], dict[str, Any]] = None


SENSOR_DESCRIPTIONS: tuple[HoymilesSmilesSensorEntityDescription, ...] = (
    HoymilesSmilesSensorEntityDescription(
        key="uptime",
        name="Uptime",
        icon="mdi:clock-outline",
        native_unit_of_measurement="s",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda coordinator: (
            coordinator.get_health_data().get("uptime_seconds")
            if coordinator.get_health_data()
            else None
        ),
        attributes_fn=lambda coordinator: {
            "start_time": (
                coordinator.get_health_data().get("start_time")
                if coordinator.get_health_data()
                else None
            ),
        },
    ),
    HoymilesSensorEntityDescription(
        key="dtu_query_count",
        name="DTU Query Count",
        icon="mdi:counter",
        native_unit_of_measurement="queries",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda coordinator: (
            coordinator.get_dtu_data().get("query_count")
            if coordinator.get_dtu_data()
            else None
        ),
        attributes_fn=lambda coordinator: {
            "dtu_status": (
                coordinator.get_dtu_data().get("status")
                if coordinator.get_dtu_data()
                else "unknown"
            ),
        },
    ),
    HoymilesSmilesSensorEntityDescription(
        key="dtu_error_count",
        name="DTU Error Count",
        icon="mdi:alert-circle",
        native_unit_of_measurement="errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda coordinator: (
            coordinator.get_dtu_data().get("error_count")
            if coordinator.get_dtu_data()
            else None
        ),
        attributes_fn=lambda coordinator: {
            "last_error": (
                coordinator.get_dtu_data().get("last_error")
                if coordinator.get_dtu_data()
                else None
            ),
            "last_error_time": (
                coordinator.get_dtu_data().get("last_error_time")
                if coordinator.get_dtu_data()
                else None
            ),
        },
    ),
    HoymilesSmilesSensorEntityDescription(
        key="dtu_last_query",
        name="DTU Last Query",
        icon="mdi:clock-check-outline",
        native_unit_of_measurement="s",
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda coordinator: (
            coordinator.get_dtu_data().get("seconds_since_last_success")
            if coordinator.get_dtu_data()
            else None
        ),
        attributes_fn=lambda coordinator: {
            "last_successful_query": (
                coordinator.get_dtu_data().get("last_successful_query")
                if coordinator.get_dtu_data()
                else None
            ),
        },
    ),
    HoymilesSmilesSensorEntityDescription(
        key="database_size",
        name="Database Size",
        icon="mdi:database",
        native_unit_of_measurement="MB",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        value_fn=lambda coordinator: (
            round(coordinator.get_stats_data().get("database_size_bytes", 0) / 1024 / 1024, 2)
            if coordinator.get_stats_data()
            else None
        ),
    ),
    HoymilesSmilesSensorEntityDescription(
        key="cached_records",
        name="Cached Records",
        icon="mdi:database-check",
        native_unit_of_measurement="records",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: (
            coordinator.get_stats_data().get("total_records")
            if coordinator.get_stats_data()
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hoymiles S-Miles sensors from config entry."""
    coordinator: HoymilesSmilesCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create system-level sensors
    entities = [
        HoymilesSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    # Get all inverters and group by DTU
    inverters = coordinator.get_inverters()
    _LOGGER.info("Setting up sensors for %d inverters", len(inverters))
    
    # Group inverters by DTU
    dtus = {}
    for inverter in inverters:
        dtu_name = inverter.get("dtu_name", "Unknown DTU")
        if dtu_name not in dtus:
            dtus[dtu_name] = []
        dtus[dtu_name].append(inverter)
    
    # Create DTU devices and sensors
    for dtu_name, dtu_inverters in dtus.items():
        _LOGGER.debug("Creating DTU device for %s with %d inverters", dtu_name, len(dtu_inverters))
        for sensor_key in DTU_SENSOR_TYPES:
            entities.append(
                DtuSensor(
                    coordinator=coordinator,
                    entry=entry,
                    dtu_name=dtu_name,
                    sensor_key=sensor_key,
                    inverter_count=len(dtu_inverters),
                )
            )
    
    # Create inverter and port sensors
    for inverter in inverters:
        serial_number = inverter.get("serial_number")
        if not serial_number:
            continue
        
        _LOGGER.debug("Creating sensors for inverter %s", serial_number)
        
        # Create inverter-level sensors
        for sensor_key in INVERTER_SENSOR_TYPES:
            entities.append(
                InverterSensor(
                    coordinator=coordinator,
                    entry=entry,
                    serial_number=serial_number,
                    sensor_key=sensor_key,
                    inverter_info=inverter,
                )
            )
        
        # Create aggregate sensors (totals across all ports)
        for sensor_key in INVERTER_AGGREGATE_SENSORS:
            entities.append(
                InverterAggregateSensor(
                    coordinator=coordinator,
                    entry=entry,
                    serial_number=serial_number,
                    sensor_key=sensor_key,
                    inverter_info=inverter,
                )
            )
        
        # Get port data to determine how many ports this inverter has
        # We'll create sensors for all ports that have data
        inverter_data = await coordinator.get_inverter_latest_data(serial_number)
        if inverter_data:
            ports = inverter_data.get("ports", [])
            port_numbers = set()
            for port in ports:
                port_num = port.get("port_number")
                if port_num is not None:
                    port_numbers.add(port_num)
            
            # Create port sensors for each port
            for port_number in sorted(port_numbers):
                _LOGGER.debug("Creating sensors for inverter %s port %d", serial_number, port_number)
                for sensor_key in PORT_SENSOR_TYPES:
                    entities.append(
                        PortSensor(
                            coordinator=coordinator,
                            entry=entry,
                            serial_number=serial_number,
                            port_number=port_number,
                            sensor_key=sensor_key,
                            inverter_info=inverter,
                        )
                    )

    async_add_entities(entities)


class HoymilesSensor(CoordinatorEntity[HoymilesSmilesCoordinator], SensorEntity):
    """Representation of a Hoymiles S-Miles sensor."""

    entity_description: HoymilesSensorEntityDescription

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
        description: HoymilesSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Hoymiles S-Miles",
            "manufacturer": "Hoymiles",
            "model": "S-Miles Bridge",
            "sw_version": "2.0.0",
        }

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
            
            _LOGGER.debug(
                "[Initial State] Writing initial state for %s sensor: %s (available=%s)",
                self.entity_description.name,
                self.native_value,
                self.available
            )
            self.async_write_ha_state()
            
            # Force another write after 1 second to be absolutely sure
            await asyncio.sleep(1)
            _LOGGER.debug("[Initial State] Writing second state for %s to ensure history capture", self.entity_description.name)
            self.async_write_ha_state()
        
        # Schedule for execution
        self.hass.async_create_task(write_initial_state())

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.coordinator)
        return {}

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.is_available()


class InverterSensor(CoordinatorEntity[HoymilesSmilesCoordinator], SensorEntity):
    """Representation of a Hoymiles inverter-level sensor."""

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
        serial_number: str,
        sensor_key: str,
        inverter_info: dict[str, Any],
    ) -> None:
        """Initialize the inverter sensor."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self._sensor_key = sensor_key
        self._inverter_info = inverter_info
        self._attr_has_entity_name = True
        
        # Get sensor configuration
        sensor_config = INVERTER_SENSOR_TYPES[sensor_key]
        
        # Set unique ID
        self._attr_unique_id = f"{entry.entry_id}_{serial_number}_{sensor_key}"
        
        # Set entity attributes from sensor configuration
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        
        # Device class
        if sensor_config.get("device_class"):
            self._attr_device_class = SensorDeviceClass(sensor_config["device_class"])
        
        # State class
        if sensor_config.get("state_class"):
            self._attr_state_class = SensorStateClass(sensor_config["state_class"])
        
        # Entity category
        if sensor_config.get("entity_category"):
            self._attr_entity_category = EntityCategory(sensor_config["entity_category"])
        
        # Device info - create a device for each inverter
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial_number)},
            "name": f"Inverter {serial_number}",
            "manufacturer": "Hoymiles",
            "model": inverter_info.get("inverter_type", "Unknown"),
            "via_device": (DOMAIN, entry.entry_id),
        }
        
        # Cache for latest data
        self._latest_data: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        
        # Fetch initial detailed data for this inverter
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)
        
        # Schedule initial state write
        async def write_initial_state():
            """Write initial state after recorder is ready."""
            import asyncio
            await asyncio.sleep(0.5)
            
            _LOGGER.debug(
                "[Initial State] Writing initial state for inverter %s sensor %s: %s",
                self._serial_number, self._sensor_key, self.native_value
            )
            self.async_write_ha_state()
            
            await asyncio.sleep(1)
            self.async_write_ha_state()
        
        self.hass.async_create_task(write_initial_state())

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()
        # Fetch latest detailed data for this inverter
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self._latest_data:
            return None
        
        # Map sensor keys to data fields (inverter-level only)
        if self._sensor_key == "grid_voltage":
            value = self._latest_data.get("grid_voltage")
            return round(value, 2) if value else None
        
        elif self._sensor_key == "grid_frequency":
            value = self._latest_data.get("grid_frequency")
            return round(value, 2) if value else None
        
        elif self._sensor_key == "temperature":
            value = self._latest_data.get("temperature")
            return round(value, 1) if value else None
        
        elif self._sensor_key == "operating_status":
            code = self._latest_data.get("operating_status")
            return OPERATING_STATUS_MAP.get(code, f"Unknown ({code})")
        
        elif self._sensor_key == "link_status":
            code = self._latest_data.get("link_status")
            return LINK_STATUS_MAP.get(code, f"Unknown ({code})")
        
        elif self._sensor_key == "alarm_code":
            code = self._latest_data.get("alarm_code")
            return ALARM_CODE_MAP.get(code, f"Unknown Alarm ({code})")
        
        elif self._sensor_key == "alarm_count":
            return self._latest_data.get("alarm_count")
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self._latest_data:
            return {}
        
        attributes = {
            "serial_number": self._serial_number,
            "dtu_name": self._inverter_info.get("dtu_name"),
            "last_seen": self._latest_data.get("timestamp"),
        }
        
        # Add port count
        ports = self._latest_data.get("ports", [])
        if ports:
            attributes["port_count"] = len(ports)
        
        # Add raw numeric codes for status sensors
        if self._sensor_key == "operating_status":
            attributes["status_code"] = self._latest_data.get("operating_status")
        elif self._sensor_key == "link_status":
            attributes["status_code"] = self._latest_data.get("link_status")
        elif self._sensor_key == "alarm_code":
            attributes["alarm_code_raw"] = self._latest_data.get("alarm_code")
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.is_available()
            and self._latest_data is not None
        )


class PortSensor(CoordinatorEntity[HoymilesSmilesCoordinator], SensorEntity):
    """Representation of a Hoymiles inverter port sensor."""

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
        serial_number: str,
        port_number: int,
        sensor_key: str,
        inverter_info: dict[str, Any],
    ) -> None:
        """Initialize the port sensor."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self._port_number = port_number
        self._sensor_key = sensor_key
        self._inverter_info = inverter_info
        self._attr_has_entity_name = True
        
        # Get sensor configuration
        sensor_config = PORT_SENSOR_TYPES[sensor_key]
        
        # Set unique ID
        self._attr_unique_id = f"{entry.entry_id}_{serial_number}_port{port_number}_{sensor_key}"
        
        # Set entity attributes from sensor configuration
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        
        # Device class
        if sensor_config.get("device_class"):
            self._attr_device_class = SensorDeviceClass(sensor_config["device_class"])
        
        # State class
        if sensor_config.get("state_class"):
            self._attr_state_class = SensorStateClass(sensor_config["state_class"])
        
        # Entity category
        if sensor_config.get("entity_category"):
            self._attr_entity_category = EntityCategory(sensor_config["entity_category"])
        
        # Device info - create a port device under the inverter
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{serial_number}_port{port_number}")},
            "name": f"Inverter {serial_number} Port {port_number}",
            "manufacturer": "Hoymiles",
            "model": f"Port {port_number}",
            "via_device": (DOMAIN, serial_number),  # Link to parent inverter
        }
        
        # Cache for latest data
        self._latest_data: dict[str, Any] | None = None
        self._port_data: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        
        # Fetch initial detailed data for this inverter
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)
        self._extract_port_data()
        
        # Schedule initial state write
        async def write_initial_state():
            """Write initial state after recorder is ready."""
            import asyncio
            await asyncio.sleep(0.5)
            
            _LOGGER.debug(
                "[Initial State] Writing initial state for inverter %s port %d sensor %s: %s",
                self._serial_number, self._port_number, self._sensor_key, self.native_value
            )
            self.async_write_ha_state()
            
            await asyncio.sleep(1)
            self.async_write_ha_state()
        
        self.hass.async_create_task(write_initial_state())

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()
        # Fetch latest detailed data for this inverter
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)
        self._extract_port_data()

    def _extract_port_data(self) -> None:
        """Extract data for this specific port."""
        if not self._latest_data:
            self._port_data = None
            return
        
        ports = self._latest_data.get("ports", [])
        for port in ports:
            if port.get("port_number") == self._port_number:
                self._port_data = port
                return
        
        self._port_data = None

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self._port_data:
            return None
        
        # Map sensor keys to port data fields
        if self._sensor_key == "pv_voltage":
            value = self._port_data.get("pv_voltage")
            return round(value, 2) if value else None
        
        elif self._sensor_key == "pv_current":
            value = self._port_data.get("pv_current")
            return round(value, 3) if value else None
        
        elif self._sensor_key == "pv_power":
            value = self._port_data.get("pv_power")
            return round(value, 2) if value else None
        
        elif self._sensor_key == "today_production":
            value = self._port_data.get("today_production")
            return int(value) if value else 0
        
        elif self._sensor_key == "total_production":
            value = self._port_data.get("total_production")
            # Convert Wh to kWh
            return round(value / 1000, 2) if value else 0
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self._port_data:
            return {}
        
        attributes = {
            "serial_number": self._serial_number,
            "port_number": self._port_number,
            "dtu_name": self._inverter_info.get("dtu_name"),
        }
        
        if self._latest_data:
            attributes["last_seen"] = self._latest_data.get("timestamp")
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.is_available()
            and self._port_data is not None
        )


class InverterAggregateSensor(CoordinatorEntity[HoymilesSmilesCoordinator], SensorEntity):
    """Representation of a Hoymiles inverter aggregate sensor (sum of all ports)."""

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
        serial_number: str,
        sensor_key: str,
        inverter_info: dict[str, Any],
    ) -> None:
        """Initialize the aggregate sensor."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self._sensor_key = sensor_key
        self._inverter_info = inverter_info
        self._attr_has_entity_name = True
        
        # Get sensor configuration
        sensor_config = INVERTER_AGGREGATE_SENSORS[sensor_key]
        
        # Set unique ID
        self._attr_unique_id = f"{entry.entry_id}_{serial_number}_{sensor_key}"
        
        # Set entity attributes from sensor configuration
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        
        # Device class
        if sensor_config.get("device_class"):
            self._attr_device_class = SensorDeviceClass(sensor_config["device_class"])
        
        # State class
        if sensor_config.get("state_class"):
            self._attr_state_class = SensorStateClass(sensor_config["state_class"])
        
        # Entity category
        if sensor_config.get("entity_category"):
            self._attr_entity_category = EntityCategory(sensor_config["entity_category"])
        
        # Device info - attach to inverter device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial_number)},
            "name": f"Inverter {serial_number}",
            "manufacturer": "Hoymiles",
            "model": inverter_info.get("inverter_type", "Unknown"),
            "via_device": (DOMAIN, entry.entry_id),
        }
        
        # Cache for latest data
        self._latest_data: dict[str, Any] | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)

    async def async_update(self) -> None:
        """Update the entity."""
        await super().async_update()
        self._latest_data = await self.coordinator.get_inverter_latest_data(self._serial_number)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self._latest_data:
            return None
        
        ports = self._latest_data.get("ports", [])
        if not ports:
            return 0 if self._sensor_key in ["total_power", "total_today_production"] else 0.0
        
        # Aggregate values across all ports
        if self._sensor_key == "total_power":
            total = sum(port.get("pv_power", 0) or 0 for port in ports)
            return round(total, 2)
        
        elif self._sensor_key == "total_today_production":
            total = sum(port.get("today_production", 0) or 0 for port in ports)
            return int(total)
        
        elif self._sensor_key == "total_lifetime_production":
            total = sum(port.get("total_production", 0) or 0 for port in ports)
            return round(total / 1000, 2)  # Convert Wh to kWh
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self._latest_data:
            return {}
        
        ports = self._latest_data.get("ports", [])
        attributes = {
            "serial_number": self._serial_number,
            "port_count": len(ports),
        }
        
        # Add per-port breakdown
        for idx, port in enumerate(ports, 1):
            port_num = port.get("port_number", idx)
            if self._sensor_key == "total_power":
                attributes[f"port_{port_num}_power"] = round(port.get("pv_power", 0) or 0, 2)
            elif self._sensor_key == "total_today_production":
                attributes[f"port_{port_num}_today"] = int(port.get("today_production", 0) or 0)
            elif self._sensor_key == "total_lifetime_production":
                attributes[f"port_{port_num}_total_kwh"] = round((port.get("total_production", 0) or 0) / 1000, 2)
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success 
            and self.coordinator.is_available()
            and self._latest_data is not None
        )


class DtuSensor(CoordinatorEntity[HoymilesSmilesCoordinator], SensorEntity):
    """Representation of a DTU-level sensor."""

    def __init__(
        self,
        coordinator: HoymilesSmilesCoordinator,
        entry: ConfigEntry,
        dtu_name: str,
        sensor_key: str,
        inverter_count: int,
    ) -> None:
        """Initialize the DTU sensor."""
        super().__init__(coordinator)
        self._dtu_name = dtu_name
        self._sensor_key = sensor_key
        self._inverter_count = inverter_count
        self._attr_has_entity_name = True
        
        # Get sensor configuration
        sensor_config = DTU_SENSOR_TYPES[sensor_key]
        
        # Set unique ID
        self._attr_unique_id = f"{entry.entry_id}_dtu_{dtu_name}_{sensor_key}"
        
        # Set entity attributes from sensor configuration
        self._attr_name = sensor_config["name"]
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        
        # Device class
        if sensor_config.get("device_class"):
            self._attr_device_class = SensorDeviceClass(sensor_config["device_class"])
        
        # State class
        if sensor_config.get("state_class"):
            self._attr_state_class = SensorStateClass(sensor_config["state_class"])
        
        # Entity category
        if sensor_config.get("entity_category"):
            self._attr_entity_category = EntityCategory(sensor_config["entity_category"])
        
        # Device info - create a DTU device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"dtu_{dtu_name}")},
            "name": f"DTU {dtu_name}",
            "manufacturer": "Hoymiles",
            "model": "DTU",
            "via_device": (DOMAIN, entry.entry_id),
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        health_data = self.coordinator.get_health_data()
        
        if self._sensor_key == "inverter_count":
            return self._inverter_count
        
        elif self._sensor_key == "total_power":
            # Sum power across all inverters on this DTU
            total_power = 0
            inverters = self.coordinator.get_inverters()
            for inverter in inverters:
                if inverter.get("dtu_name") == self._dtu_name:
                    # This would need actual power data - for now return 0
                    # We'd need to query each inverter's current power
                    pass
            return total_power
        
        # DTU-specific stats from health data
        if health_data and "dtus" in health_data:
            dtu_data = health_data.get("dtus", {}).get(self._dtu_name, {})
            
            if self._sensor_key == "last_query_time":
                last_query = dtu_data.get("last_successful_query")
                if last_query:
                    from datetime import datetime
                    try:
                        # Parse ISO format timestamp
                        return datetime.fromisoformat(last_query.replace('Z', '+00:00'))
                    except Exception:
                        return None
                return None
            
            elif self._sensor_key == "query_count":
                return dtu_data.get("query_count", 0)
            
            elif self._sensor_key == "error_count":
                return dtu_data.get("error_count", 0)
            
            elif self._sensor_key == "communication_status":
                status = dtu_data.get("status", "unknown")
                return status
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        health_data = self.coordinator.get_health_data()
        attributes = {
            "dtu_name": self._dtu_name,
            "inverter_count": self._inverter_count,
        }
        
        if health_data and "dtus" in health_data:
            dtu_data = health_data.get("dtus", {}).get(self._dtu_name, {})
            attributes.update({
                "last_error": dtu_data.get("last_error"),
                "last_error_time": dtu_data.get("last_error_time"),
                "seconds_since_last_success": dtu_data.get("seconds_since_last_success"),
            })
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.is_available()

