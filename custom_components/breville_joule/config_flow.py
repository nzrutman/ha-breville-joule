"""Config flow for Breville Joule integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .client import (
    BrevilleJouleClient,
    BrevilleAuthenticationError,
    BrevilleConnectionError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    _LOGGER.debug("Validating input for username: %s", data[CONF_USERNAME])

    client = BrevilleJouleClient(
        hass,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    # Test the connection
    try:
        _LOGGER.debug("Attempting authentication for user: %s", data[CONF_USERNAME])
        await client.async_authenticate()

        _LOGGER.debug("Authentication successful, fetching appliances")
        appliances = await client.async_get_appliances()

        _LOGGER.debug("Found %d appliances", len(appliances))
        if not appliances:
            _LOGGER.warning("No appliances found for user: %s", data[CONF_USERNAME])
            raise NoAppliances

    except BrevilleAuthenticationError as err:
        _LOGGER.debug("Authentication failed for user %s: %s", data[CONF_USERNAME], err)
        raise InvalidAuth from err
    except BrevilleConnectionError as err:
        _LOGGER.debug("Connection failed for user %s: %s", data[CONF_USERNAME], err)
        raise CannotConnect from err

    _LOGGER.debug("Validation successful for user: %s", data[CONF_USERNAME])
    return {"title": f"Breville Joule ({data[CONF_USERNAME]})"}


class BrevilleJouleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Breville Joule."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug(
                "Processing config flow input for user: %s",
                user_input.get(CONF_USERNAME),
            )
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect as err:
                _LOGGER.warning(
                    "Cannot connect to Breville servers for user %s: %s",
                    user_input.get(CONF_USERNAME),
                    err,
                )
                errors["base"] = "cannot_connect"
            except NoAppliances as err:
                _LOGGER.warning(
                    "No appliances found for user %s: %s",
                    user_input.get(CONF_USERNAME),
                    err,
                )
                errors["base"] = "no_appliances"
            except InvalidAuth as err:
                _LOGGER.warning(
                    "Authentication failed for user %s: %s",
                    user_input.get(CONF_USERNAME),
                    err,
                )
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception(
                    "Unexpected exception during config flow for user %s: %s",
                    user_input.get(CONF_USERNAME),
                    err,
                )
                errors["base"] = "unknown"
            else:
                _LOGGER.debug("Config flow validation successful, creating entry")
                # Set unique ID based on username
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauth flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        reauth_entry = self._get_reauth_entry()

        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_USERNAME, default=reauth_entry.data[CONF_USERNAME]
                        ): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors={},
            )

        errors: dict[str, str] = {}
        _LOGGER.debug("Processing reauth for user: %s", user_input.get(CONF_USERNAME))
        try:
            await validate_input(self.hass, {**reauth_entry.data, **user_input})
        except CannotConnect as err:
            _LOGGER.warning(
                "Cannot connect during reauth for user %s: %s",
                user_input.get(CONF_USERNAME),
                err,
            )
            errors["base"] = "cannot_connect"
        except NoAppliances as err:
            _LOGGER.warning(
                "No appliances found during reauth for user %s: %s",
                user_input.get(CONF_USERNAME),
                err,
            )
            errors["base"] = "no_appliances"
        except InvalidAuth as err:
            _LOGGER.warning(
                "Authentication failed during reauth for user %s: %s",
                user_input.get(CONF_USERNAME),
                err,
            )
            errors["base"] = "invalid_auth"
        except Exception as err:
            _LOGGER.exception(
                "Unexpected exception during reauth for user %s: %s",
                user_input.get(CONF_USERNAME),
                err,
            )
            errors["base"] = "unknown"
        else:
            _LOGGER.debug("Reauth successful, updating entry")
            return self.async_update_reload_and_abort(
                reauth_entry,
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoAppliances(HomeAssistantError):
    """Error to indicate no appliances found."""
