"""Support for Enigma2 STB"""

import logging
import sys

import voluptuous as vol

from homeassistant.components.media_player import (
    MEDIA_TYPE_CHANNEL, MEDIA_TYPE_MUSIC, SUPPORT_SELECT_SOURCE, MediaPlayerDevice, PLATFORM_SCHEMA,
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET)
from homeassistant.const import (CONF_HOST, STATE_OFF, STATE_ON, STATE_UNKNOWN, CONF_NAME)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['https://github.com/mihalski/enigma2_http_api/archive/python3.zip#enigma2_http_api==0.5.0']

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Enigma2 STB'

SUPPORT_ENIGMA2 = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
                  SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
                  SUPPORT_SELECT_SOURCE

MAX_VOLUME = 100

# POWERSTATE_TOGGLE_STANDBY = 0
# POWERSTATE_DEEPSTANDBY = 1
# POWERSTATE_REBOOT = 2
# POWERSTATE_RESTART = 3
POWERSTATE_WAKEUP = 4
POWERSTATE_STANDBY = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Enigma2 platform."""
    device = Enigma2Device(config.get(CONF_NAME),
                           config.get(CONF_HOST))

    if device.update():
        add_devices([device])
        return True
    return False


class Enigma2Device(MediaPlayerDevice):
    """Representation of a Enigma2 device."""

    def __init__(self, name, host):
        """Initialize the Enigma2 device."""
        _LOGGER.debug("__init__)")
        self._unique_id = None
        self._name = name
        self._powerstate = None
        self._volume = False
        self._muted = None
        self._current_channel = None
        self._current_program = None
        self._channel_list = []
        self._channel_dict = {}

        try:
            from enigma2_http_api.controller import Enigma2APIController
            self.enigma2 = Enigma2APIController(remote_addr=host)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])

        self.load_channels()

        if self._name == 'Enigma2 STB':
            try:
                about = self.enigma2.get_about()
                self._unique_id = 'enigma2' + about['info']['boxtype'] + about['info']['ifaces'][0]['mac'].replace(':', '')
                self._name = about['info']['brand'] + ' ' + about['info']['model']
            except Exception as e:
                _LOGGER.debug("Exception: %e", e)
                _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])

    def load_channels(self):
        """Load channels from first bouquet."""
        _LOGGER.debug("load_channels()")
        try:
            services = self.enigma2.get_getservices(self.enigma2.get_services()[0][1])
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False
        self._channel_list = [service['servicename'] for service in services if service['program'] != 0]
        self._channel_dict = {service['servicename']: service['servicereference'] for service in services if
                              service['program'] != 0}

    def update(self):
        """Get the latest details from the device."""
        _LOGGER.debug("update()")
        try:
            statusinfo = self.enigma2._apicall('statusinfo')
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False

        self._powerstate = statusinfo['inStandby']

        current_channel = 'N/A'
        if self._powerstate == 'false':
            if statusinfo['currservice_name'] != 'N/A':
                if statusinfo['currservice_filename']:
                    current_channel = 'Recorded'
                else:
                    current_channel = statusinfo['currservice_station']
                current_program = statusinfo['currservice_name']

                volcurrent = statusinfo['volume']
                volmuted = statusinfo['muted']

                self._volume = int(volcurrent) / MAX_VOLUME if volcurrent else None
                self._muted = (volmuted == 'true') if volmuted else None

                self._current_channel = current_channel
                self._current_program = current_program

        return True

    @property
    def unique_id(self):
        """Return the ID of this Enigma2."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device."""
        _LOGGER.debug("name()")
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        _LOGGER.debug("state()")
        if self._powerstate == 'true':
            return STATE_OFF
        if self._powerstate == 'false':
            return STATE_ON

        return STATE_UNKNOWN

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        _LOGGER.debug("volume_level()")
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        _LOGGER.debug("is_volume_muted()")
        return self._muted

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        _LOGGER.debug("supported_features()")
        return SUPPORT_ENIGMA2

    @property
    def media_title(self):
        """Title of current playing media."""
        _LOGGER.debug("media_title()")
        return self._current_program

    @property
    def media_artist(self):
        """Title of current playing media."""
        _LOGGER.debug("media_artist()")
        return self._current_channel

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        _LOGGER.debug("media_content_type()")
        return MEDIA_TYPE_MUSIC
        return MEDIA_TYPE_CHANNEL

    @property
    def source(self):
        """Return the current input source."""
        _LOGGER.debug("source()")
        return self._current_channel

    @property
    def source_list(self):
        """List of available input sources."""
        _LOGGER.debug("source_list()")
        return self._channel_list

    def select_source(self, source):
        """Select input source."""
        _LOGGER.debug("select_source()")
        try:
            result = self.enigma2.get_zap(self._channel_dict[source])
            _LOGGER.debug("%s", result)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        _LOGGER.debug("set_volume_level()")
        try:
            volset = str(round(volume * MAX_VOLUME))
            result = self.enigma2._apicall('vol', params='set=set' + volset)
            _LOGGER.debug("%s", result)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False

    def mute_volume(self, mute):
        """Mute or unmute media player."""
        _LOGGER.debug("mute_volume(); mute: %s", mute)
        try:
            result = self.enigma2._apicall('vol', params='set=mute')
            _LOGGER.debug("%s", result)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False

    def turn_on(self):
        """Turn the media player on."""
        _LOGGER.debug("turn_on()")
        try:
            result = self.enigma2.get_powerstate(POWERSTATE_WAKEUP)
            _LOGGER.debug("%s", result)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False

    def turn_off(self):
        """Turn off media player."""
        _LOGGER.debug("turn_off()")
        try:
            result = self.enigma2.get_powerstate(POWERSTATE_STANDBY)
            _LOGGER.debug("%s", result)
        except Exception as e:
            _LOGGER.debug("Exception: %e", e)
            _LOGGER.debug("Unexpected error: %s", sys.exc_info()[0])
            return False