"""
Support for the Fujitsu General Split A/C Wifi platform AKA FGLair .

"""

import logging
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.components.climate.const import (FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO)
from homeassistant.const import (ATTR_TEMPERATURE, CONF_USERNAME, CONF_PASSWORD)
from homeassistant.const import UnitOfTemperature
import homeassistant.helpers.config_validation as cv

from pyfujitsu import SplitAC
from pyfujitsu import api
from pyfujitsu.Properties import BooleanProperty
from pyfujitsu.Properties import OperationMode
from pyfujitsu.Properties import FanSpeed
from pyfujitsu.Properties import VerticalSwingPosition as vsp
from pyfujitsu.Properties import OperationModeDescriptors as omd
from pyfujitsu.Properties import FanSpeedDescriptors as fsd
from pyfujitsu.Properties import BooleanDescriptors as bd
from pyfujitsu.Properties import VerticalPositionDescriptors as vpd

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
})

HA_STATE_TO_FUJITSU = {
    HVACMode.FAN_ONLY: OperationMode.FAN,
    HVACMode.DRY: OperationMode.DRY,
    HVACMode.COOL: OperationMode.COOL,
    HVACMode.HEAT: OperationMode.HEAT,
    HVACMode.AUTO: OperationMode.AUTO,
    HVACMode.OFF: OperationMode.OFF
}

FUJITSU_TO_HA_STATE = {
    omd.FAN: HVACMode.FAN_ONLY,
    omd.DRY: HVACMode.DRY,
    omd.COOL: HVACMode.COOL,
    omd.HEAT: HVACMode.HEAT,
    omd.AUTO: HVACMode.AUTO,
    omd.OFF: HVACMode.OFF
}

VERTICAL_SWING = 'Vertical Swing'
VERTICAL_HIGHEST = 'Highest'
VERTICAL_HIGH = 'High'
VERTICAL_CENTER_HIGH = 'Center High'
VERTICAL_CENTER_LOW = 'Center Low'
VERTICAL_LOW = 'Low'
VERTICAL_LOWEST = 'Lowest'

# The other fan states are defined in the const file
FAN_QUIET = 'Quiet'

HA_SWING_TO_FUJITSU = {
    VERTICAL_HIGHEST: vsp.HIGHEST,
    VERTICAL_HIGH: vsp.HIGH,
    VERTICAL_CENTER_HIGH: vsp.CENTER_HIGH,
    VERTICAL_CENTER_LOW: vsp.CENTER_LOW,
    VERTICAL_LOW: vsp.LOW,
    VERTICAL_LOWEST: vsp.LOWEST
}

FUJITSU_SWING_TO_HA = {
    vpd.HIGHEST: VERTICAL_HIGHEST,
    vpd.HIGH: VERTICAL_HIGH,
    vpd.CENTER_HIGH: VERTICAL_CENTER_HIGH,
    vpd.CENTER_LOW: VERTICAL_CENTER_LOW,
    vpd.LOW: VERTICAL_LOW,
    vpd.LOWEST: VERTICAL_LOWEST
}

FUJITSU_FAN_TO_HA = {
    fsd.QUIET: FAN_QUIET,
    fsd.LOW: FAN_LOW,
    fsd.MEDIUM: FAN_MEDIUM,
    fsd.HIGH: FAN_HIGH,
    fsd.AUTO: FAN_AUTO
}

HA_FAN_TO_FUJITSU = {
    FAN_QUIET: FanSpeed.QUIET,
    FAN_LOW: FanSpeed.LOW,
    FAN_MEDIUM: FanSpeed.MEDIUM,
    FAN_HIGH: FanSpeed.HIGH,
    FAN_AUTO: FanSpeed.AUTO
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Fujitsu Split platform."""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    _LOGGER.debug("Added Fujitsu Account for username: %s ", username)

    fglairapi = api.Api(username, password)
    if not fglairapi._authenticate():
        _LOGGER.error("Unable to authenticate with Fujistsu General")
        return

    devices = fglairapi.get_devices_dsn()
    add_entities(FujitsuClimate(fglairapi, dsn) for dsn in devices)


class FujitsuClimate(ClimateEntity):
    """Representation of a Fujitsu Heatpump."""

    def __init__(self, api, dsn):
        self._api = api
        self._dsn = dsn
        self._fujitsu_device = SplitAC.SplitAC(self._dsn, self._api)
        self._attr_name = self.name
        self._attr_fan_modes = [FAN_QUIET,
                                FAN_LOW,
                                FAN_MEDIUM,
                                FAN_HIGH,
                                FAN_AUTO]
        self._attr_hvac_modes = [FUJITSU_TO_HA_STATE[omd.HEAT],
                                 FUJITSU_TO_HA_STATE[omd.COOL],
                                 FUJITSU_TO_HA_STATE[omd.AUTO],
                                 FUJITSU_TO_HA_STATE[omd.DRY],
                                 FUJITSU_TO_HA_STATE[omd.FAN],
                                 FUJITSU_TO_HA_STATE[omd.OFF],
                                 FUJITSU_TO_HA_STATE[omd.ON]]
        self._attr_swing_modes = [VERTICAL_SWING,
                                  VERTICAL_HIGHEST,
                                  VERTICAL_HIGH,
                                  VERTICAL_CENTER_HIGH,
                                  VERTICAL_CENTER_LOW,
                                  VERTICAL_LOW,
                                  VERTICAL_LOWEST]
        self._attr_max_temp = 30
        self._attr_min_temp = 16
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE \
                                        | ClimateEntityFeature.SWING_MODE | ClimateEntityFeature.AUX_HEAT

        self.turn_on = self.activate
        self.turn_off = self.deactivate

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._fujitsu_device.get_device_name()

    @property
    def hvac_mode(self) -> HVACMode | str | None:
        """Return hvac operation ie. heat, cool mode."""
        return FUJITSU_TO_HA_STATE[self._fujitsu_device.get_operating_mode()]

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._fujitsu_device.set_operation_mode(HA_STATE_TO_FUJITSU[hvac_mode])

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._fujitsu_device.get_display_temperature()

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._fujitsu_device.get_target_temperature()

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._fujitsu_device.set_target_temperature(kwargs.get(ATTR_TEMPERATURE))

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.5

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting.

        Requires ClimateEntityFeature.FAN_MODE.
        """
        return FUJITSU_FAN_TO_HA[self._fujitsu_device.get_fan_speed()]

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._fujitsu_device.set_fan_speed(HA_FAN_TO_FUJITSU[fan_mode])

    @property
    def swing_mode(self) -> str | None:
        """Return the swing setting.

        Requires ClimateEntityFeature.SWING_MODE.
        """
        if self._fujitsu_device.get_vertical_swing() == bd.ON:
            return VERTICAL_SWING
        else:
            return FUJITSU_SWING_TO_HA[self._fujitsu_device.get_vertical_direction()]

    def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if swing_mode == VERTICAL_SWING:
            self._fujitsu_device.set_vertical_swing(BooleanProperty.ON)
        else:
            self._fujitsu_device.set_vertical_direction(HA_SWING_TO_FUJITSU[swing_mode])

    @property
    def is_aux_heat(self):
        """Reusing is for Powerful mode."""
        return self._fujitsu_device.get_powerful_mode() == bd.ON

    def turn_aux_heat_on(self):
        """Reusing is for Powerful mode."""
        self._fujitsu_device.set_powerful_mode(BooleanProperty.ON)

    def turn_aux_heat_off(self):
        """Reusing is for Powerful mode."""
        self._fujitsu_device.set_powerful_mode(BooleanProperty.OFF)

    def activate(self):
        """Turn device on."""
        return self._fujitsu_device.turn_on()

    def deactivate(self):
        """Turn device off."""
        return self._fujitsu_device.turn_off()

    def update(self):
        """Retrieve latest state."""
        self._fujitsu_device.refresh_properties()

    async def async_update(self):
        """Retrieve latest state asynchronously."""
        await self.hass.async_add_executor_job(self.update)
