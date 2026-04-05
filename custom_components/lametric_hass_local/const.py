"""Constants for the LaMetric Home Assistant integration."""

import logging
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "lametric_hass_local"

# All platforms loaded by this integration. Add new platforms here and forward
# their setup in __init__.py (async_setup_entry / async_unload_entry).
PLATFORMS = [
    Platform.BUTTON,
    Platform.LIGHT,  # SKY only – guarded by device model check in light.py
    Platform.NUMBER,
    Platform.SCENE,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.UPDATE,
]

# How often the coordinator polls the device local API.
UPDATE_INTERVAL = timedelta(seconds=30)


LOGGER = logging.getLogger(__package__)


# Service field keys – shared between services.py and services.yaml.
CONF_CYCLES: Final = "cycles"
CONF_DATA: Final = "data"  # spike-chart data list
CONF_ICON_TYPE: Final = "icon_type"
CONF_LIFETIME: Final = "lifetime"  # reserved, not yet exposed in services
CONF_MESSAGE: Final = "message"
CONF_PRIORITY: Final = "priority"
CONF_SOUND: Final = "sound"

# Pixel-streaming service fields (SKY only).
CONF_STREAM_CONFIG: Final = "config"
CONF_STREAM_SESSION_ID: Final = "session_id"
CONF_STREAM_RGB_DATA: Final = "rgb_data"


# Service identifiers – must match the keys in services.yaml.
SERVICE_SHOW_MESSAGE: Final = "show_message"
SERVICE_SHOW_CHART: Final = "show_chart"
SERVICE_START_STREAM: Final = "start_stream"
SERVICE_STOP_STREAM: Final = "stop_stream"
SERVICE_SEND_STREAM_DATA: Final = "send_stream_data"

# URL shown to the user during manual setup so they can look up their API key.
DEVICES_URL: Final = "https://developer.lametric.com/user/devices"
