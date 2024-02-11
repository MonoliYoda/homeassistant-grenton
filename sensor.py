import logging
from .const import DOMAIN
from homeassistant.components.sensor import SensorEntity, SensorStateClass

_LOGGER = logging.getLogger(__name__)

# Import your Python client here
from .grenton import GrentonClient

# Define constants for sensor types
SENSOR_TYPES = {
    'touch_senstemp': ['Temperature', '°C'],
    '1w_temp': ['Temperature', '°C'],
    'touch_senslight': ['Light', '%']
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the switches from a config entry."""
    _LOGGER.debug("Setting up sensors from config entry")

    client = hass.data[DOMAIN][config_entry.entry_id]['client']
    # Get list of connected modules
    modules = await client.list_modules()

    sensors = []
    for module in modules:
        # Check if the module has switch capability
        if module['type'] in SENSOR_TYPES:
            new_sensor = GrentonSensor(client, module)
            sensors.append(new_sensor)

    if sensors:
        _LOGGER.debug("Adding sensors entities")
        async_add_entities(sensors)
    else:
        _LOGGER.debug("No sensors entities available")

class GrentonSensor(SensorEntity):
    """Representation of a sensor."""
    _attr_has_entity_name = True
    _attr_state_class: SensorStateClass = SensorStateClass.MEASUREMENT

    def __init__(self, client, module):
        """Initialize the sensor."""
        self._client = client
        self._module = module
        self._sensor_type = module['type']
        self._name = f"{module['name']} {SENSOR_TYPES[module['type']][0]}"
        self._attr_unique_id = module['id']
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[module['type']][1]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Updating sensor: %s", self._name)
        self._state = await self._client.get_sensor_value(self._module['id'])