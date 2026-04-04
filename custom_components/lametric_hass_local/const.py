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
