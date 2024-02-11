import logging
from typing import Any
from .const import DOMAIN
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.components.climate import ClimateEntity, HVACMode, HVACAction, ClimateEntityFeature, PRESET_AWAY, PRESET_HOME

_LOGGER = logging.getLogger(__name__)

GRENTON_STATE_ATTR = 6
GRENTON_MODE_ATTR = 8
GRENTON_POINT_VALUE_ATTR = 3
GRENTON_AWAY_VALUE_ATTR = 4

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the thermostats from a config entry."""
    _LOGGER.debug("Setting up thermostats from config entry")

    client = hass.data[DOMAIN][config_entry.entry_id]['client']
    # Get list of connected modules
    modules = await client.list_modules()

    thermostats = []
    for module in modules:
        # Check if the module has thermostat capability
        if module['type'] == 'thermostat':
            new_thermostat = GrentonThermostat(client, module)
            thermostats.append(new_thermostat)

    if thermostats:
        _LOGGER.debug("Adding thermostat entities")
        async_add_entities(thermostats)
    else:
        _LOGGER.debug("No thermostat entities available")

class GrentonThermostat(ClimateEntity):
    """Representation of a thermostat."""
    _attr_has_entity_name = True
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_mode = HVACMode.OFF
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    _attr_preset_mode = PRESET_HOME
    _attr_preset_modes = [PRESET_HOME, PRESET_AWAY]

    def __init__(self, client, module):
        """Initialize the thermostat."""
        self._client = client
        self._module = module
        self._name = module['name']
        self._attr_unique_id = module['id']
        self._state = None

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def is_on(self):
        """Return true if the thermostat is on."""
        return self._state == 'on'

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            if self._attr_preset_mode == PRESET_AWAY:
                await self._client.set_module_value(self._module['id'], GRENTON_AWAY_VALUE_ATTR, temp)
            else:
                if self._attr_hvac_mode == HVACMode.AUTO:
                    await self.async_set_hvac_mode(HVACMode.HEAT)
                await self._client.set_module_value(self._module['id'], GRENTON_POINT_VALUE_ATTR, temp)
            self._attr_target_temperature = temp

    async def async_update(self) -> None:
        state = await self._client.get_thermo_values(self._module['id'])
        self._attr_current_temperature = state['currentTemp']

        self._attr_target_temperature = state['setTemp']
        if state['on']:
            if state['controlOut']:
                self._attr_hvac_action = HVACAction.HEATING
            else:
                self._attr_hvac_action = HVACAction.IDLE
            if state['mode'] == 0:
                self._attr_hvac_mode = HVACMode.HEAT
                self._attr_preset_mode = PRESET_HOME
            if state['mode'] == 1:
                self._attr_hvac_mode = HVACMode.AUTO
                self._attr_preset_mode = PRESET_AWAY
                self._attr_target_temperature = state['targetTemp']
            if state['mode'] == 2:
                self._attr_hvac_mode = HVACMode.AUTO
                self._attr_preset_mode = PRESET_HOME
                self._attr_target_temperature = state['targetTemp']
        else:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF


    async def async_turn_on(self) -> None:
        await self._client.set_module_value(self._module['id'], GRENTON_STATE_ATTR, 1)

    async def async_turn_off(self) -> None:
        await self._client.set_module_value(self._module['id'], GRENTON_STATE_ATTR, 0)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._client.set_module_value(self._module['id'], GRENTON_STATE_ATTR, 0)
        else:
            await self._client.set_module_value(self._module['id'], GRENTON_STATE_ATTR, 1)
            if hvac_mode == HVACMode.HEAT:
                await self._client.set_module_value(self._module['id'], GRENTON_MODE_ATTR, 0)
                await self.async_set_preset_mode(PRESET_HOME)
            if hvac_mode == HVACMode.AUTO:
                await self._client.set_module_value(self._module['id'], GRENTON_MODE_ATTR, 2)
                await self.async_set_preset_mode(PRESET_HOME)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_AWAY:
            await self._client.set_thermo_away_mode(self._module['id'], True)
        else:
            await self._client.set_thermo_away_mode(self._module['id'], False)

