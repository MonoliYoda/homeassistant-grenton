"""Config flow for grenton integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

from .grenton import GrentonClient

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need

CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_INIT_VECTOR = 'init_vector'
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_ENCRYPTION_KEY): str,
        vol.Required(CONF_INIT_VECTOR): str,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host
        self.client = GrentonClient(host)

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        self.client.update_keys(username, password)

        return await self.client.get_clu_id()


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_ENCRYPTION_KEY], data[CONF_INIT_VECTOR]
    # )

    hub = PlaceholderHub(data[CONF_HOST])

    if not await hub.authenticate(data[CONF_ENCRYPTION_KEY], data[CONF_INIT_VECTOR]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    sn = await hub.authenticate(data[CONF_ENCRYPTION_KEY], data[CONF_INIT_VECTOR])
    # Return info that you want to store in the config entry.
    return {"sn": sn}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for grenton."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = {}
            if len(user_input.get(CONF_ENCRYPTION_KEY, '')) != 24:
                errors[CONF_ENCRYPTION_KEY] = 'Invalid encryption key, must be 24 characters long'
            if len(user_input.get(CONF_INIT_VECTOR, '')) != 24:
                errors[CONF_INIT_VECTOR] = 'Invalid initialization vector, must be 24 characters long'
            if not errors: # We don't want to try and connect with invalid inputs
                try:
                    info = await validate_input(self.hass, user_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
            if errors:
                return self.async_show_form(
                    step_id='user',
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors
                )

            else:
            # Encryption key and initialization vector are valid, create config entry
                return self.async_create_entry(title=info["sn"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # async def async_step_entities(self, user_input=None):
    #     """Handle the entity selection."""
    #     if user_input is not None:
    #         # User has selected the entity type, proceed to next step
    #         return await self.async_step_entity_configuration(user_input)

    #     # Get list of discovered entities
    #     discovered_entities = await self._discover_entities()

    #     # Show form to select entity type for each discovered entity
    #     entity_schema = {}
    #     for entity in discovered_entities:
    #         entity_schema[vol.Required(entity['id'])] = vol.In(ENTITY_TYPES)

    #     return self.async_show_form(
    #         step_id='entities',
    #         data_schema=vol.Schema(entity_schema)
    #     )

    # async def async_step_entity_configuration(self, user_input):
    #     """Handle entity configuration."""
    #     # Store the entity configurations in the options for the entry
    #     return self.async_create_entry(title="My Smart Home", data=user_input)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
