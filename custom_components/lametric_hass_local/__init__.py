"""LaMetric Local integration for Home Assistant.

Provides local polling of LaMetric devices via the device API and exposes
Button, Light (LaMetric SKY only), and Scene entity platforms.
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import LaMetricConfigEntry, LaMetricCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the LaMetric integration (config-entry only, no YAML setup)."""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: LaMetricConfigEntry) -> bool:
    """Initialize the coordinator and forward platform setup."""

    coordinator = LaMetricCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LaMetricConfigEntry) -> bool:
    """Unload all platforms for the given config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
