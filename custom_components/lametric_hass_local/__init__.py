"""LaMetric Local integration for Home Assistant.

Provides local polling of LaMetric devices via the device API and exposes
Button, Light (LaMetric SKY only), and Scene entity platforms.
"""

from homeassistant.components.notify.legacy import async_reload as notify_async_reload
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import LaMetricConfigEntry, LaMetricCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the LaMetric integration (config-entry only, no YAML setup)."""

    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: LaMetricConfigEntry
) -> bool:
    """Initialize the coordinator and forward platform setup."""

    coordinator = LaMetricCoordinator(hass, config_entry)

    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {CONF_NAME: coordinator.data.name, "entry_id": config_entry.entry_id},
            {},
        )
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: LaMetricConfigEntry
) -> bool:
    """Unload all platforms for the given config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        await notify_async_reload(hass, DOMAIN)

    return unload_ok
