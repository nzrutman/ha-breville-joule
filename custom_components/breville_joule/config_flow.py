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
    client = BrevilleJouleClient(
        hass,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    # Test the connection
    try:
        await client.async_authenticate()
        appliances = await client.async_get_appliances()

        if not appliances:
            raise NoAppliances
    except BrevilleAuthenticationError as err:
        raise InvalidAuth from err
    except BrevilleConnectionError as err:
        raise CannotConnect from err

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
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoAppliances:
                errors["base"] = "no_appliances"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
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
        try:
            await validate_input(self.hass, {**reauth_entry.data, **user_input})
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except NoAppliances:
            errors["base"] = "no_appliances"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
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
