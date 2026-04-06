"""Tests for the LaMetric coordinator."""

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from lametric import DeviceModels, LaMetricApiError, LaMetricAuthenticationError
from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.coordinator import LaMetricCoordinator


# type: ignore[type-arg]
def _make_coord_with_device(state_coro_factory: Any) -> MagicMock:  # noqa: ANN001
    """Return a minimal LaMetricCoordinator mock; device.state calls factory."""
    coord = MagicMock()
    coord.device.host = "192.168.1.100"
    coord.stream_state = None
    coord.apps = {}
    type(coord.device).state = property(lambda self: state_coro_factory())
    type(coord.device).stream_state = property(lambda self: state_coro_factory())
    type(coord.device).installed_apps = property(lambda self: state_coro_factory())
    return coord


def test_update_data_returns_device_state(device_state: DeviceState) -> None:
    """Coordinator returns the DeviceState from the device API on success."""

    async def run() -> DeviceState:
        async def ok():
            return device_state

        coord = _make_coord_with_device(ok)
        return await LaMetricCoordinator._async_update_data(coord)

    result = asyncio.run(run())
    assert result == device_state


def test_update_data_raises_auth_failed_on_authentication_error() -> None:
    """Authentication errors are re-raised as ConfigEntryAuthFailed."""

    async def run() -> None:
        async def fail_auth():
            raise LaMetricAuthenticationError("bad key")

        coord = _make_coord_with_device(fail_auth)
        await LaMetricCoordinator._async_update_data(coord)

    with pytest.raises(ConfigEntryAuthFailed):
        asyncio.run(run())


def test_update_data_raises_update_failed_on_api_error() -> None:
    """Generic API errors are re-raised as UpdateFailed."""

    async def run() -> None:
        async def fail_api():
            raise LaMetricApiError("device unreachable")

        coord = _make_coord_with_device(fail_api)
        await LaMetricCoordinator._async_update_data(coord)

    with pytest.raises(UpdateFailed):
        asyncio.run(run())


def test_update_failed_message_contains_host() -> None:
    """UpdateFailed message includes the device host IP for debugging."""

    async def run() -> None:
        async def fail_api():
            raise LaMetricApiError("boom")

        coord = _make_coord_with_device(fail_api)
        await LaMetricCoordinator._async_update_data(coord)

    with pytest.raises(UpdateFailed, match="192.168.1.100"):
        asyncio.run(run())


def test_coordinator_init_creates_device_with_correct_host() -> None:
    """LaMetricCoordinator.__init__ sets self.device with the configured host."""
    from unittest.mock import MagicMock, patch

    from homeassistant.const import CONF_API_KEY, CONF_HOST

    from custom_components.lametric_hass_local.coordinator import LaMetricCoordinator

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

    mock_device.assert_called_once()
    call_kwargs = mock_device.call_args.kwargs
    assert call_kwargs["host"] == "10.0.0.1"
    assert call_kwargs["api_key"] == "secret-key"


def test_stream_state_not_fetched_for_time_device(device_state: DeviceState) -> None:
    """stream_state is set to None without an API call for non-SKY devices."""
    assert device_state.model != DeviceModels.SKY

    stream_calls = 0

    async def run() -> None:
        nonlocal stream_calls

        async def ok():
            return device_state

        async def stream_ok():
            nonlocal stream_calls
            stream_calls += 1
            return MagicMock()

        coord = _make_coord_with_device(ok)
        type(coord.device).stream_state = property(lambda self: stream_ok())
        await LaMetricCoordinator._async_update_data(coord)
        assert coord.stream_state is None

    asyncio.run(run())
    assert stream_calls == 0


def test_stream_state_fetched_for_sky_device() -> None:
    """stream_state is fetched from the API for SKY devices."""
    from tests.conftest import _build_device_state

    sky_state = _build_device_state(model=DeviceModels.SKY)
    fake_stream = MagicMock()

    async def run() -> None:
        async def ok():
            return sky_state

        async def stream_ok():
            return fake_stream

        coord = _make_coord_with_device(ok)
        type(coord.device).stream_state = property(lambda self: stream_ok())
        await LaMetricCoordinator._async_update_data(coord)
        assert coord.stream_state is fake_stream

    asyncio.run(run())
