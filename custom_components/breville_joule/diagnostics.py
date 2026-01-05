"""Diagnostics support for Breville Joule integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data

    return {
        "config_entry_data": async_redact_data(config_entry.data, {CONF_PASSWORD}),
        "appliances": [
            {
                "serial_number": appliance.serial_number,
                "model": appliance.model,
                "name": appliance.name,
            }
            for appliance in coordinator.client._appliances
        ],
        "device_data": {
            serial_number: {
                "current_temperature": data.current_temperature,
                "target_temperature": data.target_temperature,
                "is_active": data.is_active,
                "start_time": data.start_time,
                "end_time": data.end_time,
            }
            for serial_number, data in coordinator.data.items()
        }
        if coordinator.data
        else {},
        "websocket_connected": coordinator.client._connected,
    }
