"""DataUpdateCoordinator for Breville Joule integration."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BrevilleJouleClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import BrevilleJouleData

if TYPE_CHECKING:
    from .models import BrevilleJouleConfigEntry

_LOGGER = logging.getLogger(__name__)


class BrevilleJouleDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, BrevilleJouleData]]
):
    """Class to manage fetching data from the Breville Joule API."""

    config_entry: BrevilleJouleConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: BrevilleJouleConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=config_entry,
        )
        self.config_entry = config_entry
        self.client = BrevilleJouleClient(
            hass,
            config_entry.data[CONF_USERNAME],
            config_entry.data[CONF_PASSWORD],
        )
        self._websocket_task: asyncio.Task | None = None

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        # Authenticate and get appliances
        _LOGGER.debug(
            "Setting up Breville Joule coordinator for entry: %s",
            self.config_entry.entry_id,
        )
        try:
            _LOGGER.debug("Authenticating client")
            await self.client.async_authenticate()

            _LOGGER.debug("Fetching appliances")
            appliances = await self.client.async_get_appliances()
            _LOGGER.debug(
                "Found %d appliances during coordinator setup", len(appliances)
            )

            # Set up WebSocket connection in background
            _LOGGER.debug("Starting WebSocket background task")
            self._websocket_task = self.hass.async_create_background_task(
                self._async_setup_websocket(), "breville_joule_websocket"
            )
        except Exception as ex:
            _LOGGER.error("Failed to setup coordinator: %s", ex)
            raise ConfigEntryAuthFailed("Authentication failed") from ex

    async def _async_setup_websocket(self) -> None:
        """Set up WebSocket connection."""
        try:
            _LOGGER.debug("Setting up WebSocket connection")
            # Add listener for real-time updates
            self.client.add_listener(self._handle_realtime_update)
            _LOGGER.debug("Added real-time update listener")

            # Connect WebSocket - this runs forever
            _LOGGER.debug("Connecting to WebSocket")
            await self.client.async_connect_websocket()
        except Exception as ex:
            _LOGGER.error("WebSocket setup failed: %s", ex)
            # Don't fail the entire setup if WebSocket fails
            # The integration can still work with polling

    @callback
    def _handle_realtime_update(self) -> None:
        """Handle real-time update from WebSocket."""
        _LOGGER.debug("Received real-time update from WebSocket")
        # Update coordinator data without triggering a fetch
        data = self.client.get_all_data()
        _LOGGER.debug(
            "Real-time update contains data for %d devices", len(data) if data else 0
        )
        self.async_set_updated_data(data)

    async def _async_update_data(self) -> dict[str, BrevilleJouleData]:
        """Update data via library."""
        try:
            _LOGGER.debug("Updating coordinator data")
            # Return current data from client
            # Real updates come from WebSocket
            data = self.client.get_all_data()
            _LOGGER.debug("Retrieved data for %d devices", len(data) if data else 0)
            return data
        except Exception as ex:
            _LOGGER.error("Error updating coordinator data: %s", ex)
            raise UpdateFailed(f"Error communicating with API: {ex}") from ex

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and setup."""
        _LOGGER.debug(
            "Performing first refresh for config entry: %s", self.config_entry.entry_id
        )
        await self._async_setup()
        await super().async_config_entry_first_refresh()
        _LOGGER.debug("First refresh completed successfully")

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        _LOGGER.debug(
            "Shutting down coordinator for entry: %s", self.config_entry.entry_id
        )
        if self._websocket_task:
            _LOGGER.debug("Cancelling WebSocket task")
            self._websocket_task.cancel()

        if self.client:
            _LOGGER.debug("Disconnecting client")
            await self.client.async_disconnect()

    def get_device_data(self, serial_number: str) -> BrevilleJouleData | None:
        """Get data for a specific device."""
        _LOGGER.debug("Getting device data for serial: %s", serial_number)
        if self.data:
            device_data = self.data.get(serial_number)
            if device_data:
                _LOGGER.debug("Found device data for %s", serial_number)
            else:
                _LOGGER.debug("No device data found for %s", serial_number)
            return device_data
        _LOGGER.debug("No coordinator data available")
        return None
