"""Coordinator logic for LaMetric device state updates."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from lametric import (
    DeviceState,
    LaMetricApiError,
    LaMetricAuthenticationError,
    LaMetricDevice,
)

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type LaMetricConfigEntry = ConfigEntry[LaMetricCoordinator]


class LaMetricCoordinator(DataUpdateCoordinator[DeviceState]):
    """Coordinator for polling a LaMetric device."""

    config_entry: LaMetricConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: LaMetricConfigEntry) -> None:
        """Set up the LaMetric device client and coordinator."""
        self.device = LaMetricDevice(
            host=config_entry.data[CONF_HOST],
            api_key=config_entry.data[CONF_API_KEY],
            session=async_get_clientsession(hass),
        )

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> DeviceState:
        """Fetch the latest device state from the local API.

        Raises ConfigEntryAuthFailed on authentication errors so Home Assistant
        can prompt the user to re-enter credentials. Maps other API errors to
        UpdateFailed so the coordinator can retry on the next poll interval.
        """
        try:
            return await self.device.state

        except LaMetricAuthenticationError as error:
            # Invalid or revoked API key - trigger a re-auth flow
            raise ConfigEntryAuthFailed from error

        except LaMetricApiError as error:
            # Network or device error
            raise UpdateFailed(
                f"Failed to fetch data from LaMetric device at {self.device.host}"
            ) from error
