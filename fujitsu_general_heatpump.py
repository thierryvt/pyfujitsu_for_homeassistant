"""
Support for the Fujitsu General Split A/C Wifi platform AKA FGLair .

"""

import logging
import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import (ATTR_TEMPERATURE, CONF_USERNAME, CONF_PASSWORD, TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv

from pyfujitseu import SplitAC
from pyfujitseu import api
from pyfujitseu.Properties import BooleanProperty
from pyfujitseu.Properties import OperationMode
from pyfujitseu.Properties import VerticalSwingPosition as vsp
from pyfujitseu.Properties import OperationModeDescriptors as omd
from pyfujitseu.Properties import FanSpeedDescriptors as fsd
from pyfujitseu.Properties import BooleanDescriptors as bd
from pyfujitseu.Properties import VerticalPositionDescriptors as vpd

REQUIREMENTS = ['pyfujitsu==91.9.4']

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
        self._name = self.name
        self._aux_heat = self.is_aux_heat_on
        self._target_temperature = self.target_temperature
        self._unit_of_measurement = self.unit_of_measurement
        self._current_fan_mode = self.current_fan_mode
        self._current_operation = self.current_operation
        self._current_swing_mode = self.current_swing_mode
        self._fan_list = [fsd.QUIET, fsd.LOW, fsd.MEDIUM, fsd.HIGH, fsd.AUTO]
        self._operation_list = [FUJITSU_TO_HA_STATE[omd.HEAT], FUJITSU_TO_HA_STATE[omd.COOL], FUJITSU_TO_HA_STATE[omd.AUTO],
                                FUJITSU_TO_HA_STATE[omd.DRY], FUJITSU_TO_HA_STATE[omd.FAN], FUJITSU_TO_HA_STATE[omd.OFF],
                                FUJITSU_TO_HA_STATE[omd.ON]]
        self._swing_list = [VERTICAL_SWING, VERTICAL_HIGHEST, VERTICAL_HIGH, VERTICAL_CENTER_HIGH, VERTICAL_CENTER_LOW, VERTICAL_LOW, VERTICAL_LOWEST]
        self._target_temperature_high = self.target_temperature_high
        self._target_temperature_low = self.target_temperature_low
        self._on = self.is_on
        self._supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE \
                                   | ClimateEntityFeature.SWING_MODE | ClimateEntityFeature.AUX_HEAT

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._fujitsu_device.get_device_name()

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return FUJITSU_TO_HA_STATE[self._fujitsu_device.get_operating_mode()]

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._operation_list

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._fujitsu_device.get_target_temperature()

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 0.5

    @property
    def powerful_mode(self):
        """ Return Powerfull mode state"""
        return self._fujitsu_device.get_powerful_mode()

    @property
    def is_on(self):
        """Return true if on."""
        if self._fujitsu_device.get_operating_mode() != omd.OFF:
            return True
        else:
            return False

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._fujitsu_device.get_fan_speed()

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._fan_list

    @property
    def current_swing_mode(self):
        """Return the fan setting."""
        if self._fujitsu_device.get_vertical_swing() == bd.ON:
            return VERTICAL_SWING
        else:
            return FUJITSU_SWING_TO_HA[self._fujitsu_device.get_vertical_direction()]

    @property
    def swing_list(self):
        """Return the list of available swing modes."""
        return self._swing_list

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._fujitsu_device.set_target_temperature(kwargs.get(ATTR_TEMPERATURE))

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        print(fan_mode)
        self._fujitsu_device.set_fan_speed(fan_mode)

    def set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        self._fujitsu_device.set_operation_mode(HA_STATE_TO_FUJITSU[operation_mode])

    def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if swing_mode == VERTICAL_SWING:
            self._fujitsu_device.set_vertical_swing(BooleanProperty.ON)
        else:
            self._fujitsu_device.set_vertical_direction(HA_SWING_TO_FUJITSU[swing_mode])

    def turn_on(self):
        """Turn device on."""
        return self._fujitsu_device.turn_on()

    def turn_off(self):
        """Turn device off."""
        return self._fujitsu_device.turn_off()

    @property
    def is_aux_heat_on(self):
        """Reusing is for Powerfull mode."""
        if self._fujitsu_device.get_powerful_mode() == bd.ON:
            return True
        else:
            return False

    def turn_aux_heat_on(self):
        """Reusing is for Powerfull mode."""
        self._fujitsu_device.set_powerful_mode(BooleanProperty.ON)

    def turn_aux_heat_off(self):
        """Reusing is for Powerfull mode."""
        self._fujitsu_device.set_powerful_mode(BooleanProperty.OFF)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._supported_features

    def update(self):
        """Retrieve latest state."""
        self._fujitsu_device.refresh_properties()
