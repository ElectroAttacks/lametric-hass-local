"""Constants for the LaMetric Home Assistant integration."""

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "lametric_hass_local"
PLATFORMS = [
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SCENE,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.UPDATE,
]

UPDATE_INTERVAL = timedelta(seconds=30)


LOGGER = logging.getLogger(__package__)


CONF_CYCLES: Final = "cycles"
CONF_DATA: Final = "data"
CONF_ICON_TYPE: Final = "icon_type"
CONF_LIFETIME: Final = "lifetime"
CONF_MESSAGE: Final = "message"
CONF_PRIORITY: Final = "priority"
CONF_SOUND: Final = "sound"

CONF_STREAM_CONFIG: Final = "config"
CONF_STREAM_SESSION_ID: Final = "session_id"
CONF_STREAM_RGB_DATA: Final = "rgb_data"


SERVICE_SHOW_MESSAGE: Final = "show_message"
SERVICE_SHOW_CHART: Final = "show_chart"
SERVICE_START_STREAM: Final = "start_stream"
SERVICE_STOP_STREAM: Final = "stop_stream"
SERVICE_SEND_STREAM_DATA: Final = "send_stream_data"

DEVICES_URL: Final = "https://developer.lametric.com/user/devices"
