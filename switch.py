import logging
from .const import DOMAIN
from homeassistant.components.switch import SwitchEntity

_LOGGER = logging.getLogger(__name__)
CONF_ENCRYPTION_KEY = 'encryption_key'
CONF_INIT_VECTOR = 'init_vector'

# Import your Python client here
from .grenton import GrentonClient

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the switches from a config entry."""
    _LOGGER.debug("Setting up switches from config entry")

    client = hass.data[DOMAIN][config_entry.entry_id]['client']
    # Get list of connected modules
    modules = await client.list_modules()

    switches = []
    for module in modules:
        # Check if the module has switch capability
        if module['type'] == 'd_out':
            new_switch = GrentonSwitch(client, module)
            switches.append(new_switch)

    if switches:
        _LOGGER.debug("Adding switch entities")
        async_add_entities(switches)
    else:
        _LOGGER.debug("No switch entities available")

class GrentonSwitch(SwitchEntity):
    """Representation of a switch."""
    _attr_has_entity_name = True

    def __init__(self, client, module):
        """Initialize the switch."""
        self._client = client
        self._module = module
        self._name = module['name']
        self._attr_unique_id = module['id']
        self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._state == 'on'

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch: %s", self._name)
        await self._client.set_switch_state(self._module['id'], True)
        self._state = 'on'

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch: %s", self._name)
        await self._client.set_switch_state(self._module['id'], False)
        self._state = 'off'

    async def async_update(self):
        """Fetch new state data for the switch."""
        _LOGGER.debug("Updating switch: %s", self._name)
        state = await self._client.get_switch_state(self._module['id'])
        self._state = 'on' if state else 'off'
