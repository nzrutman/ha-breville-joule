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
    _LOGGER.debug("Setting up Breville Joule integration for entry: %s", entry.entry_id)

    coordinator = BrevilleJouleDataUpdateCoordinator(hass, entry)
    _LOGGER.debug("Created coordinator for entry: %s", entry.entry_id)

    _LOGGER.debug("Starting first refresh for coordinator")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("First refresh completed for entry: %s", entry.entry_id)

    entry.runtime_data = coordinator
    _LOGGER.debug("Set runtime data for entry: %s", entry.entry_id)

    _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug(
        "Successfully set up Breville Joule integration for entry: %s", entry.entry_id
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BrevilleJouleConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Breville Joule integration for entry: %s", entry.entry_id)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        _LOGGER.debug("Successfully unloaded platforms for entry: %s", entry.entry_id)

        if hasattr(entry.runtime_data, "client") and entry.runtime_data.client:
            _LOGGER.debug("Disconnecting client for entry: %s", entry.entry_id)
            await entry.runtime_data.client.async_disconnect()

        # Also call the coordinator shutdown
        if hasattr(entry.runtime_data, "async_shutdown"):
            _LOGGER.debug("Shutting down coordinator for entry: %s", entry.entry_id)
            await entry.runtime_data.async_shutdown()
    else:
        _LOGGER.warning("Failed to unload platforms for entry: %s", entry.entry_id)

    _LOGGER.debug(
        "Unload completed for entry: %s, success: %s", entry.entry_id, unload_ok
    )
    return unload_ok
