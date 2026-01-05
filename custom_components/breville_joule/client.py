"""Breville Joule API client."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import urllib.parse
from dataclasses import dataclass
from typing import Any

import aiohttp
import jwt
from websocket import WebSocketApp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import aiohttp_client

from .const import (
    APPLIANCES_URL,
    AUTH_AUDIENCE,
    AUTH_REALM,
    AUTH_SCOPE,
    AUTH_URL,
    CLIENT_ID,
    JOULE_MODEL,
    USER_AGENT,
    WEBSOCKET_URL,
)
from .models import BrevilleAppliance, BrevilleJouleData

_LOGGER = logging.getLogger(__name__)


class BrevilleAuthenticationError(HomeAssistantError):
    """Error to indicate authentication failure."""


class BrevilleConnectionError(HomeAssistantError):
    """Error to indicate connection failure."""


@dataclass
class BrevilleAppliance:
    """Represent a Breville appliance."""

    id: str
    name: str
    model: str
    serial_number: str  # Add this attribute
    # ... other existing fields ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrevilleAppliance":
        """Create BrevilleAppliance from dictionary data."""
        return cls(
            id=data["id"],
            name=data["name"],
            model=data.get("model", "Unknown"),
            serial_number=data["serialNumber"],
        )


class BrevilleJouleClient:
    """Client for communicating with Breville Joule API."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
    ) -> None:
        """Initialize the client."""
        self.hass = hass
        self.username = username
        self.password = password
        self.polling_interval = 30  # Fixed 30 second interval
        self._access_token: str | None = None
        self._user_id: str | None = None
        self._appliances: list[BrevilleAppliance] = []
        self._ws: WebSocketApp | None = None
        self._data: dict[str, BrevilleJouleData] = {}
        self._connected = False
        self._listeners: list = []

    async def async_authenticate(self) -> None:
        """Authenticate with Breville servers."""
        auth_payload = {
            "email": self.username,
            "password": self.password,
        }
        auth_headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

        def _handle_auth_response_error(status: int, response_text: str) -> None:
            """Handle authentication response errors."""
            if status in (400, 401, 403):
                _LOGGER.debug("Client error (%d): %s", status, response_text)
                raise BrevilleAuthenticationError(f"Authentication error ({status})")

        def _handle_unexpected_error(ex: Exception) -> None:
            """Handle unexpected errors during authentication."""
            _LOGGER.error("Unexpected error during authentication: %s", ex)
            raise BrevilleConnectionError("Unexpected authentication error") from ex

        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.post(
                AUTH_URL, json=auth_payload, headers=auth_headers
            ) as resp:
                # Read response text for error context
                response_text = ""
                try:
                    response_text = await resp.text()
                    _LOGGER.debug(
                        "Auth response status: %d, content length: %d",
                        resp.status,
                        len(response_text),
                    )
                except Exception as ex:
                    _LOGGER.debug("Could not read response text: %s", ex)

                _handle_auth_response_error(resp.status, response_text)
                resp.raise_for_status()

                token_data = await resp.json()
                id_token = token_data.get("id_token")
                if not id_token:
                    raise BrevilleAuthenticationError(
                        "No ID token received from server"
                    )

                self._access_token = id_token

                # Decode and validate JWT payload
                try:
                    jwt_payload = jwt.decode(
                        id_token,
                        options={"verify_signature": False},
                        algorithms=["RS256"],
                    )
                except jwt.InvalidTokenError as ex:
                    raise BrevilleAuthenticationError("Invalid ID token format") from ex

                if not isinstance(jwt_payload, dict) or "sub" not in jwt_payload:
                    raise BrevilleAuthenticationError(
                        "Invalid ID token: missing user ID"
                    )

                self._user_id = jwt_payload["sub"]
                _LOGGER.debug(
                    "Authentication successful for user ID: %s",
                    self._user_id[:8] + "..." if self._user_id else "unknown",
                )
        except (aiohttp.ClientError, TimeoutError) as ex:
            _LOGGER.error("Network error during authentication: %s", ex)
            raise BrevilleConnectionError("Cannot connect to Breville servers") from ex
        except (BrevilleAuthenticationError, BrevilleConnectionError):
            raise
        except Exception as ex:
            _handle_unexpected_error(ex)

    async def async_get_appliances(self) -> list[BrevilleAppliance]:
        """Get list of appliances."""
        if not self._access_token or not self._user_id:
            await self.async_authenticate()

        def _handle_response_error(status: int, response_text: str = "") -> None:
            """Handle HTTP response errors."""
            if status == 401:
                _LOGGER.debug("Token expired or invalid (401): %s", response_text)
                raise BrevilleAuthenticationError("Authentication token expired")
            elif status == 403:
                _LOGGER.debug("Access denied to appliances (403): %s", response_text)
                raise BrevilleAuthenticationError("Access denied to appliance data")
            elif status >= 500:
                _LOGGER.debug(
                    "Server error during appliance fetch (%d): %s",
                    status,
                    response_text,
                )
                raise BrevilleConnectionError("Server error while fetching appliances")

        def _handle_unexpected_error(ex: Exception) -> None:
            """Handle unexpected errors during appliance fetching."""
            _LOGGER.error("Unexpected error fetching appliances: %s", ex)
            raise BrevilleConnectionError(
                "Unexpected error fetching appliances"
            ) from ex

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "User-Agent": USER_AGENT,
        }

        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{APPLIANCES_URL}/{self._user_id}/appliances", headers=headers
            ) as resp:
                response_text = ""
                try:
                    response_text = await resp.text()
                except Exception as ex:
                    _LOGGER.debug("Could not read response text: %s", ex)

                _handle_response_error(resp.status, response_text)
                resp.raise_for_status()

                appliances_data = await resp.json()

                # Process and return the appliances list
                appliances = []
                for appliance_data in appliances_data.get("appliances", []):
                    try:
                        appliance = BrevilleAppliance.from_dict(appliance_data)
                        appliances.append(appliance)
                    except Exception as ex:
                        _LOGGER.warning("Failed to parse appliance data: %s", ex)
                        continue

            self._appliances = appliances
            return appliances

        except (aiohttp.ClientError, TimeoutError) as ex:
            _LOGGER.error("Network error during appliance fetch: %s", ex)
            raise BrevilleConnectionError("Cannot connect to Breville servers") from ex
        except (BrevilleAuthenticationError, BrevilleConnectionError):
            raise
        except Exception as ex:
            _handle_unexpected_error(ex)

        if not self._appliances:
            await self.async_get_appliances()

        if not self._access_token:
            raise BrevilleAuthenticationError(
                "No access token available for WebSocket connection"
            )

        try:
            ws = WebSocketApp(
                WEBSOCKET_URL,
                header={"sf-id-token": self._access_token},
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )

            if not ws:
                raise BrevilleConnectionError("Failed to create WebSocket connection")

            self._ws = ws

            # Run WebSocket in a separate thread
            def run_websocket():
                """Run WebSocket in thread."""
                if self._ws:
                    self._ws.run_forever()

            ws_thread = threading.Thread(target=run_websocket, daemon=True)
            ws_thread.start()

            # Wait a bit for connection to establish
            await asyncio.sleep(1)

        except Exception as ex:
            _LOGGER.error("Failed to connect WebSocket: %s", ex)
            raise HomeAssistantError("WebSocket connection failed") from ex

    def _on_open(self, ws) -> None:
        """Handle WebSocket open event."""
        _LOGGER.debug("WebSocket connection opened")
        self._connected = True

        # Add appliances to WebSocket
        for appliance in self._appliances:
            add_appliance = {
                "action": "addAppliance",
                "serialNumber": appliance.serial_number,
            }
            ws.send(json.dumps(add_appliance))

        # Start ping and polling tasks
        asyncio.run_coroutine_threadsafe(self._async_ping_loop(), self.hass.loop)
        asyncio.run_coroutine_threadsafe(self._async_poll_loop(), self.hass.loop)

    def _on_message(self, ws, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            asyncio.run_coroutine_threadsafe(
                self._handle_websocket_message(message), self.hass.loop
            )
        except Exception as ex:
            _LOGGER.error("Failed to handle WebSocket message: %s", ex)

    def _on_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        _LOGGER.error("WebSocket error: %s", error)
        self._connected = False

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket close."""
        _LOGGER.info("WebSocket connection closed: %s", close_msg)
        self._connected = False

    async def _handle_websocket_message(self, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            if data.get("messageType") != "stateReport":
                return

            reported = data.get("data", {}).get("reported", {})
            if not isinstance(reported, dict):
                return

            # Extract serial number (would need to be included in the message)
            # For now, update the first appliance
            if not self._appliances:
                return

            serial_number = self._appliances[0].serial_number
            device_data = self._data.get(serial_number)
            if not device_data:
                return

            # Parse timer information
            has_timer = False
            if timers := reported.get("timers"):
                if isinstance(timers, list) and timers:
                    timer = timers[0]
                    if "timestamp" in timer:
                        has_timer = True
                        device_data.start_time = timer.get("timestamp")
                    if "down_from_n" in timer:
                        device_data.end_time = timer.get("timestamp", 0) + timer.get(
                            "down_from_n", 0
                        )

            device_data.is_active = has_timer

            # Parse temperature information
            if heaters := reported.get("heaters"):
                if isinstance(heaters, list) and heaters:
                    heater = heaters[0]
                    device_data.target_temperature = heater.get("temp_sp")
                    device_data.current_temperature = heater.get("cur_temp")

            # Notify listeners
            for listener in self._listeners:
                listener()

        except Exception as ex:
            _LOGGER.error("Error parsing WebSocket message: %s", ex)

    async def _async_ping_loop(self) -> None:
        """Send periodic ping messages."""
        while self._connected and self._ws:
            await asyncio.sleep(20)
            if (
                self._ws
                and hasattr(self._ws, "sock")
                and self._ws.sock
                and self._ws.sock.connected
            ):
                try:
                    self._ws.send(json.dumps({"action": "ping"}))
                except Exception as ex:
                    _LOGGER.error("Failed to send ping: %s", ex)
                    break

    async def _async_poll_loop(self) -> None:
        """Send periodic polling messages."""
        while self._connected and self._ws:
            await asyncio.sleep(self.polling_interval)
            if (
                self._ws
                and hasattr(self._ws, "sock")
                and self._ws.sock
                and self._ws.sock.connected
            ):
                try:
                    for appliance in self._appliances:
                        add_appliance = {
                            "action": "addAppliance",
                            "serialNumber": appliance.serial_number,
                        }
                        self._ws.send(json.dumps(add_appliance))
                except Exception as ex:
                    _LOGGER.error("Failed to send poll message: %s", ex)
                    break

    def add_listener(self, listener) -> None:
        """Add a listener for data updates."""
        self._listeners.append(listener)

    def remove_listener(self, listener) -> None:
        """Remove a data update listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def get_data(self, serial_number: str) -> BrevilleJouleData | None:
        """Get data for a specific appliance."""
        return self._data.get(serial_number)

    def get_all_data(self) -> dict[str, BrevilleJouleData]:
        """Get data for all appliances."""
        return self._data.copy()

    async def async_disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self._connected = False
        if self._ws:
            await self.hass.async_add_executor_job(self._ws.close)
            self._ws = None
