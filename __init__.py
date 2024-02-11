"""The grenton integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from homeassistant.const import CONF_HOST
from .grenton import GrentonClient

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.SWITCH]

CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_INIT_VECTOR = 'init_vector'


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up grenton from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    # Get the host, encryption key, and initialization vector from the config entry data
    host = entry.data.get(CONF_HOST)
    key = entry.data.get(CONF_ENCRYPTION_KEY)
    iv = entry.data.get(CONF_INIT_VECTOR)

    # Initialize your client using the host, encryption key, and initialization vector
    client = GrentonClient(host, base64_key=key, base64_iv=iv)

    # Store the client instance in hass.data under your integration's domain
    hass.data[DOMAIN][entry.entry_id] = {
        'client': client
    }
    # modules = await client.list_modules()
    # switches = []
    # lights = []
    # thermostats = []
    # sensors = []

    # hass.data[DOMAIN][entry.entry_id] = {
    #     'client': client,
    #     'module_list': modules,

    # }

    # Add platforms (e.g., switches, sensors) to Home Assistant
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "light")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
