import logging
from .const import DOMAIN
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS

_LOGGER = logging.getLogger(__name__)
CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_INIT_VECTOR = 'init_vector'

# Import your Python client here
from .grenton import GrentonClient

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the lights from a config entry."""
    _LOGGER.debug("Setting up lights from config entry")

    client = hass.data[DOMAIN][config_entry.entry_id]['client']
    # Get list of connected modules
    modules = await client.list_modules()

    lights = []
    for module in modules:
        # Check if the module is an RGBW module
        if module['type'] == 'led':
            # Generate 4 light entities, 1 for each channel
            for channel in 'rgbw':
                new_light = GrentonLight(client, module, channel)
                lights.append(new_light)

    if lights:
        _LOGGER.debug("Adding light entities")
        async_add_entities(lights)
    else:
        _LOGGER.debug("No light entities available")

class GrentonLight(LightEntity):
    """Representation of a light."""
    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, client, module, channel):
        """Initialize the light."""
        self._client = client
        self._module = module
        self._channel = channel
        self._name = module['name'] + '_' + channel
        self._attr_unique_id = module['id'] + '_' + channel
        self._brightness = None

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def is_on(self):
        """Return true if the light is on."""
        if self._brightness:
            return self._brightness > 0
        return False

    @property
    def brightness(self):
        """Return the value of the light [0-255]"""
        return self._brightness


    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on light: %s", self._name)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if not brightness:
            brightness = 255
        await self._client.set_led_value(self._module['id'], self._channel, brightness)
        self._brightness = brightness

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off light: %s", self._name)
        await self._client.set_led_value(self._module['id'], self._channel, 0)
        self._brightness = 0

    async def async_update(self):
        """Fetch new state data for the switch."""
        _LOGGER.debug("Updating light: %s", self._name)
        self._brightness = int(await self._client.get_led_state(self._module['id'], self._channel))
