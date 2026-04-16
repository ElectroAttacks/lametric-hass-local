"""Tests for the LaMetric coordinator."""

import asyncio
from dataclasses import replace as dc_replace
from typing import Any, cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from lametric import DeviceModels, LaMetricApiError, LaMetricAuthenticationError
from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.const import APPS_REFRESH_INTERVAL
from custom_components.lametric_hass_local.coordinator import LaMetricCoordinator


class _FakeDevice:
    """Simple LaMetric device double with async properties."""

    def __init__(
        self,
        *,
        host: str = "192.168.1.100",
        state: DeviceState | Exception,
        apps: dict[str, Any] | Exception | None = None,
        stream_state: Any | Exception | None = None,
    ) -> None:
        self.host = host
        self._state = state
        self._apps = {} if apps is None else apps
        self._stream_state = stream_state

    @property
    def state(self):
        async def _coro() -> DeviceState:
            if isinstance(self._state, Exception):
                raise self._state
            return self._state

        return _coro()

    @property
    def installed_apps(self):
        async def _coro() -> dict[str, Any]:
            if isinstance(self._apps, Exception):
                raise self._apps
            return self._apps

        return _coro()

    @property
    def stream_state(self):
        async def _coro() -> Any:
            if isinstance(self._stream_state, Exception):
                raise self._stream_state
            return self._stream_state

        return _coro()


def _make_coordinator(device: _FakeDevice) -> LaMetricCoordinator:
    """Create a coordinator instance backed by a fake device."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {CONF_HOST: device.host, CONF_API_KEY: "secret-key"}

    with (
        patch(
            "custom_components.lametric_hass_local.coordinator.LaMetricDevice",
            return_value=device,
        ),
        patch(
            "custom_components.lametric_hass_local.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        return LaMetricCoordinator(hass, config_entry)


def test_coordinator_init_creates_device_with_correct_host() -> None:
    """Coordinator init should build the LaMetric client from entry data."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.data = {CONF_HOST: "10.0.0.1", CONF_API_KEY: "secret-key"}

    with (
        patch(
            "custom_components.lametric_hass_local.coordinator.LaMetricDevice"
        ) as mock_device,
        patch(
            "custom_components.lametric_hass_local.coordinator.async_get_clientsession"
        ),
    ):
        LaMetricCoordinator(hass, config_entry)

    call_kwargs = mock_device.call_args.kwargs
    assert call_kwargs["host"] == "10.0.0.1"
    assert call_kwargs["api_key"] == "secret-key"


def test_update_data_returns_device_state(device_state: DeviceState) -> None:
    """Coordinator should return the current DeviceState on success."""
    coordinator = _make_coordinator(
        _FakeDevice(state=device_state, apps={"clock": MagicMock()})
    )

    result = asyncio.run(coordinator._async_update_data())

    assert result == device_state


def test_update_data_raises_auth_failed_on_state_authentication_error() -> None:
    """Authentication errors on the primary state poll should trigger reauth."""
    coordinator = _make_coordinator(
        _FakeDevice(state=LaMetricAuthenticationError("bad key"))
    )

    with pytest.raises(ConfigEntryAuthFailed):
        asyncio.run(coordinator._async_update_data())


def test_update_data_raises_update_failed_on_state_api_error() -> None:
    """Generic API errors on the primary state poll should raise UpdateFailed."""
    coordinator = _make_coordinator(
        _FakeDevice(state=LaMetricApiError("device unreachable"))
    )

    with pytest.raises(UpdateFailed):
        asyncio.run(coordinator._async_update_data())


def test_update_failed_message_contains_host() -> None:
    """UpdateFailed message should include the device host for debugging."""
    coordinator = _make_coordinator(_FakeDevice(state=LaMetricApiError("boom")))

    with pytest.raises(UpdateFailed, match="192.168.1.100"):
        asyncio.run(coordinator._async_update_data())


def test_apps_are_refreshed_on_first_successful_update(
    device_state: DeviceState,
) -> None:
    """The first successful poll should populate the app cache."""
    apps = {"clock": MagicMock()}
    coordinator = _make_coordinator(_FakeDevice(state=device_state, apps=apps))

    asyncio.run(coordinator._async_update_data())

    assert coordinator.apps == apps
    assert coordinator._last_apps_refresh is not None


def test_apps_are_not_refreshed_again_inside_ttl(device_state: DeviceState) -> None:
    """Installed apps should be cached until the refresh interval expires."""
    device = _FakeDevice(state=device_state, apps={"clock": MagicMock()})
    coordinator = _make_coordinator(device)
    cast(Any, coordinator).apps = {"cached": MagicMock()}
    coordinator._last_apps_refresh = 100.0

    with (
        patch(
            "custom_components.lametric_hass_local.coordinator.monotonic",
            return_value=100.0 + APPS_REFRESH_INTERVAL.total_seconds() - 1,
        ),
        patch.object(
            _FakeDevice,
            "installed_apps",
            new_callable=PropertyMock,
        ) as installed_apps,
    ):
        asyncio.run(coordinator._async_refresh_apps_if_needed())

    installed_apps.assert_not_called()
    assert coordinator.apps.keys() == {"cached"}


def test_apps_are_refreshed_after_ttl_expires(device_state: DeviceState) -> None:
    """Installed apps should refresh again once the cache TTL has elapsed."""
    refreshed_apps = {"weather": MagicMock()}
    coordinator = _make_coordinator(
        _FakeDevice(state=device_state, apps=refreshed_apps)
    )
    coordinator._last_apps_refresh = 100.0

    with patch(
        "custom_components.lametric_hass_local.coordinator.monotonic",
        side_effect=[100.0 + APPS_REFRESH_INTERVAL.total_seconds() + 1, 500.0],
    ):
        asyncio.run(coordinator._async_refresh_apps_if_needed())

    assert coordinator.apps == refreshed_apps
    assert coordinator._last_apps_refresh == 500.0


def test_apps_refresh_error_keeps_cached_apps(device_state: DeviceState) -> None:
    """App refresh failures should not fail the coordinator or clear cached apps."""
    coordinator = _make_coordinator(
        _FakeDevice(state=device_state, apps=LaMetricApiError("apps failed"))
    )
    cached_apps: dict[str, Any] = {"cached": MagicMock()}
    cast(Any, coordinator).apps = cached_apps.copy()

    result = asyncio.run(coordinator._async_update_data())

    assert result == device_state
    assert coordinator.apps.keys() == cached_apps.keys()


def test_apps_auth_error_keeps_cached_apps(device_state: DeviceState) -> None:
    """Auth errors on app refresh should not fail a successful state poll."""
    coordinator = _make_coordinator(
        _FakeDevice(state=device_state, apps=LaMetricAuthenticationError("bad key"))
    )
    cached_apps: dict[str, Any] = {"cached": MagicMock()}
    cast(Any, coordinator).apps = cached_apps.copy()

    result = asyncio.run(coordinator._async_update_data())

    assert result == device_state
    assert coordinator.apps.keys() == cached_apps.keys()


def test_stream_state_not_fetched_for_time_device(device_state: DeviceState) -> None:
    """Non-SKY devices should not query stream_state."""
    assert device_state.model != DeviceModels.SKY

    coordinator = _make_coordinator(
        _FakeDevice(state=device_state, stream_state=MagicMock())
    )

    with patch.object(
        _FakeDevice,
        "stream_state",
        new_callable=PropertyMock,
    ) as stream_state:
        asyncio.run(coordinator._async_update_data())

    stream_state.assert_not_called()
    assert coordinator.stream_state is None


def test_stream_state_is_fetched_for_sky_device(device_state: DeviceState) -> None:
    """SKY devices should refresh stream_state as best-effort data."""
    sky_state = dc_replace(device_state, model=DeviceModels.SKY)
    fake_stream = MagicMock()
    coordinator = _make_coordinator(
        _FakeDevice(state=sky_state, apps={}, stream_state=fake_stream)
    )

    asyncio.run(coordinator._async_update_data())

    assert coordinator.stream_state is fake_stream


def test_stream_state_api_error_does_not_fail_update(
    device_state: DeviceState,
) -> None:
    """A stream_state API failure should not fail the main update."""
    sky_state = dc_replace(device_state, model=DeviceModels.SKY)
    coordinator = _make_coordinator(
        _FakeDevice(
            state=sky_state,
            apps={},
            stream_state=LaMetricApiError("stream failed"),
        )
    )
    coordinator.stream_state = MagicMock()

    result = asyncio.run(coordinator._async_update_data())

    assert result == sky_state
    assert coordinator.stream_state is None


def test_stream_state_auth_error_does_not_fail_update(
    device_state: DeviceState,
) -> None:
    """A stream_state auth failure should not fail the main update."""
    sky_state = dc_replace(device_state, model=DeviceModels.SKY)
    coordinator = _make_coordinator(
        _FakeDevice(
            state=sky_state,
            apps={},
            stream_state=LaMetricAuthenticationError("bad key"),
        )
    )
    coordinator.stream_state = MagicMock()

    result = asyncio.run(coordinator._async_update_data())

    assert result == sky_state
    assert coordinator.stream_state is None
