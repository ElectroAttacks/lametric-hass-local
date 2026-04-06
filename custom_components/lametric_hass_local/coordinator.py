"""Coordinator logic for LaMetric device state updates."""

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from lametric import (
    App,
    DeviceModels,
    DeviceState,
    LaMetricApiError,
    LaMetricAuthenticationError,
    LaMetricDevice,
    StreamState,
)

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

type LaMetricConfigEntry = ConfigEntry[LaMetricCoordinator]


class LaMetricCoordinator(DataUpdateCoordinator[DeviceState]):
    """Coordinator for polling a LaMetric device."""

    config_entry: LaMetricConfigEntry
    stream_state: StreamState | None
    apps: dict[str, App]

    def __init__(self, hass: HomeAssistant, config_entry: LaMetricConfigEntry) -> None:
        """Set up the LaMetric device client and coordinator."""
        self.device = LaMetricDevice(
            host=config_entry.data[CONF_HOST],
            api_key=config_entry.data[CONF_API_KEY],
            session=async_get_clientsession(hass),
        )
        self.stream_state = None
        self.apps = {}

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
            device_state, apps = await asyncio.gather(
                self.device.state,
                self.device.installed_apps,
            )
            self.apps = apps
        except LaMetricAuthenticationError as error:
            # Invalid or revoked API key - trigger a re-auth flow
            raise ConfigEntryAuthFailed from error

        except LaMetricApiError as error:
            # Network or device error
            raise UpdateFailed(
                f"Failed to fetch data from LaMetric device at {self.device.host}"
            ) from error

        if device_state.model == DeviceModels.SKY:
            self.stream_state = await self.device.stream_state
        else:
            self.stream_state = None

        return device_state
