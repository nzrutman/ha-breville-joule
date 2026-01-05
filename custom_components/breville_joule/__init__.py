"""The Breville Joule integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BrevilleJouleDataUpdateCoordinator

if TYPE_CHECKING:
    from .models import BrevilleJouleConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: BrevilleJouleConfigEntry
) -> bool:
    """Set up Breville Joule from a config entry."""
    coordinator = BrevilleJouleDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BrevilleJouleConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if hasattr(entry.runtime_data, "client") and entry.runtime_data.client:
            await entry.runtime_data.client.async_disconnect()

    return unload_ok
