"""Sensor platform for Breville Joule integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .models import BrevilleJouleData

if TYPE_CHECKING:
    from .coordinator import BrevilleJouleDataUpdateCoordinator
    from .models import BrevilleJouleConfigEntry

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="current_temperature",
        translation_key="current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="start_time",
        translation_key="start_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="end_time",
        translation_key="end_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="cooking_state",
        translation_key="cooking_state",
        device_class=SensorDeviceClass.ENUM,
        options=["idle", "active"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BrevilleJouleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Breville Joule sensor entities."""
    coordinator = config_entry.runtime_data

    entities = []

    # Create sensors for each appliance
    for serial_number in coordinator.data:
        entities.extend(
            BrevilleJouleSensor(coordinator, description, serial_number)
            for description in SENSOR_DESCRIPTIONS
        )

    async_add_entities(entities)


class BrevilleJouleSensor(
    CoordinatorEntity[BrevilleJouleDataUpdateCoordinator], SensorEntity
):
    """Representation of a Breville Joule sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrevilleJouleDataUpdateCoordinator,
        description: SensorEntityDescription,
        serial_number: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._serial_number = serial_number

        # Set unique ID
        self._attr_unique_id = f"{serial_number}_{description.key}"

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            name=f"Breville Joule {serial_number[-4:]}",
            manufacturer=MANUFACTURER,
            model="Joule (BSV600)",
            serial_number=serial_number,
        )

    @property
    def native_value(self) -> str | float | int | None:
        """Return the state of the sensor."""
        device_data = self.coordinator.get_device_data(self._serial_number)
        if not device_data:
            return None

        match self.entity_description.key:
            case "current_temperature":
                return device_data.current_temperature
            case "target_temperature":
                return device_data.target_temperature
            case "start_time":
                return device_data.start_time
            case "end_time":
                return device_data.end_time
            case "cooking_state":
                return "active" if device_data.is_active else "idle"
            case _:
                return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.get_device_data(self._serial_number) is not None
        )
