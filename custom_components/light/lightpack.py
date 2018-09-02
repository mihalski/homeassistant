"""
Support for Lightpack remote.
"""

import logging
import sys

import voluptuous as vol

from homeassistant.components.light import (
    ATTR_EFFECT, ATTR_BRIGHTNESS,
    SUPPORT_EFFECT, SUPPORT_BRIGHTNESS,
    Light, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_HOST, CONF_PORT, CONF_NAME)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['py-lightpack==2.1.0']

_LOGGER = logging.getLogger(__name__)

SUPPORT_LIGHTPACK = (SUPPORT_BRIGHTNESS | SUPPORT_EFFECT)

DEFAULT_NAME = 'Lightpack'
DEFAULT_PORT = 3636

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

EFFECT_MOODLAMP = "moodlamp"
EFFECT_AMBILIGHT = "ambilight"

LIGHTPACK_EFFECT_LIST = [
    EFFECT_MOODLAMP,
    EFFECT_AMBILIGHT
]

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Lightpack remote."""
    _LOGGER.debug("%s: setup_platform()", config.get(CONF_NAME))
    import lightpack
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    update = lightpack.Lightpack(host=host, port=port)
    control = lightpack.Lightpack(host=host, port=port)

    device = Lightpack(update, control, config.get(CONF_NAME), host, port)

    if device.connect():
        add_devices([device])
        return True
    return False

class Lightpack(Light):
    """Representation of Lightpack remote."""

    def __init__(self, update, control, name, host, port):
        """Initialize the light."""
        _LOGGER.debug("%s: __init__", name)
        self._update = update
        self._control = control
        self._name = name
        self._host = host
        self._port = port
        self._available = False
        self._state = None 
        self._mode = None
        self._brightness = None

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def available(self):
        """Return True if available."""
        _LOGGER.debug("%s: available(); result: %s", self._name, self._available)
        if not self._available:
            self.connect()
        return self._available

    @property
    def is_on(self):
        """Return true if on."""
        _LOGGER.debug("%s: is_on(); state: %s", self._name, self._state)
        return self._state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_LIGHTPACK

    def turn_on(self, **kwargs):
        """Turn the lights on."""
        self.lock()
        _LOGGER.debug("%s: turn_on()", self._name)
        effect = kwargs.get(ATTR_EFFECT)
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if effect:
            _LOGGER.debug("%s: turn_on(); set_effect(); effect: %s)", self._name, effect)
            self.set_effect(effect)
        if brightness:
            _LOGGER.debug("%s: turn_on(); set_brightness(); brightness: %s)", self._name, brightness)
            self.set_brightness(brightness)
        self._control.turnOn()
        self.unlock()

    def turn_off(self):
        """Turn the lights on."""
        self.lock()
        _LOGGER.debug("%s: turn_off()", self._name)
        self._control.turnOff()
        self.unlock()

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return LIGHTPACK_EFFECT_LIST

    @property
    def effect(self):
        """Return the current effect (aka Lightpack mode)."""
        _LOGGER.debug("%s: effect(); mode: %s", self._name, self._mode)
        return self._mode

    @property
    def brightness(self):
        """Return the brightness."""
        _LOGGER.debug("%s: brightness(); brightness: %s", self._name, self._brightness)
        return self._brightness

    def set_effect(self, effect):
        """Activate effect."""
        _LOGGER.debug("%s: set_effect(); effect: %s", self._name, effect)
        try:
            self._control.setProfile(effect)
        except lightpack.CommandFailedError:
            pass

    def set_brightness(self, brightness):
        """Set backlight brightness."""
        adjusted_brightness = int(brightness / 255 * 100)
        _LOGGER.debug("%s: set_brightness(); original: %s; adjusted: %s", self._name, brightness, adjusted_brightness)
        try:
            self._control.setBrightness(adjusted_brightness)
        except lightpack.CommandFailedError:
            pass

    def lock(self):
        _LOGGER.debug("%s: lock()", self._name)
        try:
            self._control.lock()
        except lightpack.CommandFailedError:
            pass

    def unlock(self):
        _LOGGER.debug("%s: unlock()", self._name)
        try:
            self._control.unlock()
        except lightpack.CommandFailedError:
            pass

    def update(self):
        if self._available:
            try:
                self.connect()
            except Exception as e:
                _LOGGER.error("%s, %s", self._name, e)
                _LOGGER.error("Unexpected error:", sys.exc_info()[0])
            else:
                self._available = True
            
        # _LOGGER.debug("%s: update()", self._name)
        try:
            status = self._update.getStatus()
        except Exception as e:
            _LOGGER.error("%s, %s", self._name, e)
            _LOGGER.error("Unexpected error:", sys.exc_info()[0])
        except lightpack.CommandFailedError:
            self._available = False
            return False
        else:
            self._available = True

        if status == 'on':
            self._state = True
        elif status == 'off':
            self._state = False
        else:
            self._available = False

        self._mode = self._update.getMode()
        brightness = self._update.getBrightness()
        self._brightness = int(255 * brightness / 100)
        # rgb = self.uodate._sendAndReceivePayload('getcolors').split(';', 1)[0].split(';', 1)[0][2:]
        # self._rgb = tuple(map(int, rgb.split(',')))
        _LOGGER.debug("%s: update(); brightness: %s; mode: %s", self._name, self._brightness, self._mode)

    def connect(self):
        _LOGGER.debug("%s: connect()", self._name)
        try:
            self._update.connect()
            self._control.connect()
            self._available = True
            return True
        except lightpack.CannotConnectError as e:
            _LOGGER.error("%s:connect(); result: %s", self._name, repr(e))
            _LOGGER.error("Unexpected error:", sys.exc_info()[0])
            return False