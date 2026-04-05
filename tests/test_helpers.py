"""Tests for the LaMetric helper utilities."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from lametric import LaMetricApiError, LaMetricConnectionError

from custom_components.lametric_hass_local.helpers import (
    async_get_coordinator_by_device_id,
    lametric_api_exception_handler,
)


def _make_entity(host: str = "192.168.1.100") -> MagicMock:
    """Return a minimal entity mock compatible with the exception handler."""
    entity = MagicMock()
    entity.coordinator.device.host = host
    entity.coordinator.last_update_success = True
    return entity


def test_handler_propagates_return_value_on_success() -> None:
    """Decorated function completes without error when the API call succeeds."""

    async def run() -> None:
        @lametric_api_exception_handler
        async def action(self) -> None:  # type: ignore[override, no-untyped-def]
            pass  # success – no exception

        entity = _make_entity()
        await action(entity)

        # Coordinator listeners should be refreshed after a successful call
        entity.coordinator.async_update_listeners.assert_called_once()

    asyncio.run(run())


def test_handler_maps_connection_error_to_home_assistant_error() -> None:
    """LaMetricConnectionError is converted to HomeAssistantError."""

    async def run() -> None:
        @lametric_api_exception_handler
        async def action(self) -> None:  # type: ignore[override, no-untyped-def]
            raise LaMetricConnectionError("timeout")

        entity = _make_entity()
        with pytest.raises(HomeAssistantError, match="192.168.1.100"):
            await action(entity)

    asyncio.run(run())


def test_handler_marks_coordinator_failed_on_connection_error() -> None:
    """last_update_success is set to False when a ConnectionError occurs."""

    async def run() -> None:
        @lametric_api_exception_handler
        async def action(self) -> None:  # type: ignore[override, no-untyped-def]
            raise LaMetricConnectionError("gone")

        entity = _make_entity()
        with pytest.raises(HomeAssistantError):
            await action(entity)

        assert entity.coordinator.last_update_success is False

    asyncio.run(run())


def test_handler_maps_api_error_to_home_assistant_error() -> None:
    """LaMetricApiError is converted to HomeAssistantError."""

    async def run() -> None:
        @lametric_api_exception_handler
        async def action(self) -> None:  # type: ignore[override, no-untyped-def]
            raise LaMetricApiError("bad response")

        entity = _make_entity()
        with pytest.raises(HomeAssistantError, match="192.168.1.100"):
            await action(entity)

    asyncio.run(run())


# ── async_get_coordinator_by_device_id ────────────────────────────────────────


def test_get_coordinator_raises_when_device_not_found() -> None:
    """ValueError is raised when the device ID is not in the device registry."""
    hass = MagicMock()
    device_registry = MagicMock()
    device_registry.async_get.return_value = None

    with (
        patch(
            "custom_components.lametric_hass_local.helpers.dr.async_get",
            return_value=device_registry,
        ),
        pytest.raises(ValueError, match="No device found"),
    ):
        async_get_coordinator_by_device_id(hass, "unknown-id")


def test_get_coordinator_raises_when_no_matching_entry() -> None:
    """ValueError is raised when no loaded config entry matches the device."""
    hass = MagicMock()
    device_registry = MagicMock()

    device_entry = MagicMock()
    device_entry.config_entries = {"entry-abc"}
    device_registry.async_get.return_value = device_entry

    config_entry = MagicMock()
    config_entry.entry_id = "entry-xyz"
    hass.config_entries.async_loaded_entries.return_value = iter([config_entry])

    with (
        patch(
            "custom_components.lametric_hass_local.helpers.dr.async_get",
            return_value=device_registry,
        ),
        pytest.raises(ValueError, match="No coordinator found"),
    ):
        async_get_coordinator_by_device_id(hass, "device-123")


def test_get_coordinator_returns_runtime_data_on_match() -> None:
    """Returns config_entry.runtime_data when the entry_id matches the device."""
    hass = MagicMock()
    device_registry = MagicMock()

    device_entry = MagicMock()
    device_entry.config_entries = {"entry-abc"}
    device_registry.async_get.return_value = device_entry

    expected_coordinator = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "entry-abc"
    config_entry.runtime_data = expected_coordinator
    hass.config_entries.async_loaded_entries.return_value = iter([config_entry])

    with patch(
        "custom_components.lametric_hass_local.helpers.dr.async_get",
        return_value=device_registry,
    ):
        result = async_get_coordinator_by_device_id(hass, "device-123")

    assert result is expected_coordinator
