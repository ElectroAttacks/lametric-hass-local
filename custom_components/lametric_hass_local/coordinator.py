"""Coordinator logic for LaMetric device state updates."""

from time import monotonic

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

from .const import APPS_REFRESH_INTERVAL, DOMAIN, LOGGER, UPDATE_INTERVAL

type LaMetricConfigEntry = ConfigEntry[LaMetricCoordinator]


class LaMetricCoordinator(DataUpdateCoordinator[DeviceState]):
    """Coordinator for polling a LaMetric device."""

    config_entry: LaMetricConfigEntry
    stream_state: StreamState | None
    apps: dict[str, App]
    _last_apps_refresh: float | None

    def __init__(self, hass: HomeAssistant, config_entry: LaMetricConfigEntry) -> None:
        """Set up the LaMetric device client and coordinator."""
        self.device = LaMetricDevice(
            host=config_entry.data[CONF_HOST],
            api_key=config_entry.data[CONF_API_KEY],
            session=async_get_clientsession(hass),
        )
        self.stream_state = None
        self.apps = {}
        self._last_apps_refresh = None

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
        device_state = await self._async_fetch_device_state()
        await self._async_refresh_apps_if_needed()
        await self._async_refresh_stream_state(device_state)

        return device_state

    async def _async_fetch_device_state(self) -> DeviceState:
        """Fetch the current device state required by all coordinator consumers."""
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

    async def _async_refresh_apps_if_needed(self) -> None:
        """Refresh installed apps on first load and then on a slower cadence."""
        if (
            self._last_apps_refresh is not None
            and monotonic() - self._last_apps_refresh
            < APPS_REFRESH_INTERVAL.total_seconds()
        ):
            return

        try:
            self.apps = await self.device.installed_apps
            self._last_apps_refresh = monotonic()
        except LaMetricAuthenticationError:
            LOGGER.debug(
                "Skipping installed apps refresh for %s because authentication "
                "failed outside the primary state poll",
                self.device.host,
            )
        except LaMetricApiError as error:
            LOGGER.debug(
                "Keeping cached installed apps for %s after refresh error: %s",
                self.device.host,
                error,
            )

    async def _async_refresh_stream_state(self, device_state: DeviceState) -> None:
        """Refresh SKY stream state without failing the primary coordinator poll."""
        if device_state.model != DeviceModels.SKY:
            self.stream_state = None
            return

        try:
            self.stream_state = await self.device.stream_state
        except LaMetricAuthenticationError:
            self.stream_state = None
            LOGGER.debug(
                "Skipping stream state refresh for %s because authentication "
                "failed outside the primary state poll",
                self.device.host,
            )
        except LaMetricApiError as error:
            self.stream_state = None
            LOGGER.debug(
                "Failed to refresh stream state for %s: %s",
                self.device.host,
                error,
            )
