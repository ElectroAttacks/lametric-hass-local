"""Tests for the LaMetric text platform."""

import asyncio
from dataclasses import replace as dc_replace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError
from lametric import LaMetricApiError
from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.text import (
    TEXTS,
    LaMetricTextEntity,
    async_setup_entry,
)


def _bt_desc():
    return next(t for t in TEXTS if t.key == "bluetooth_name")


# ── availability ──────────────────────────────────────────────────────────────


def test_available_true_when_bluetooth_available(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """available is True when bluetooth reports available and coordinator is up."""
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())
    assert entity.available is True


def test_available_false_when_bluetooth_not_available(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """available is False when bluetooth reports not available."""
    bt = dc_replace(device_state.bluetooth, available=False)
    coordinator.data = dc_replace(device_state, bluetooth=bt)
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())
    assert entity.available is False


# ── native_value ──────────────────────────────────────────────────────────────


def test_native_value_returns_bluetooth_name(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """native_value returns the bluetooth name from coordinator data."""
    from dataclasses import replace as dcr

    bt = dcr(device_state.bluetooth, name="MyDevice")
    coordinator.data = dcr(device_state, bluetooth=bt)
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())
    assert entity.native_value == "MyDevice"


def test_native_value_returns_empty_string_when_name_none(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """native_value returns '' when bluetooth.name is None."""
    from dataclasses import replace as dcr

    bt = dcr(device_state.bluetooth, name=None)
    coordinator.data = dcr(device_state, bluetooth=bt)
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())
    assert entity.native_value == ""


# ── async_set_value ───────────────────────────────────────────────────────────


def test_set_value_calls_set_bluetooth(coordinator: MagicMock) -> None:
    """async_set_value calls device.set_bluetooth with the new name."""
    coordinator.device.set_bluetooth = AsyncMock()
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())

    asyncio.run(entity.async_set_value("NewName"))

    coordinator.device.set_bluetooth.assert_awaited_once_with(name="NewName")
    coordinator.async_request_refresh.assert_awaited_once()


def test_set_value_raises_on_api_error(coordinator: MagicMock) -> None:
    """async_set_value raises HomeAssistantError when the device returns an error."""
    coordinator.device.set_bluetooth = AsyncMock(side_effect=LaMetricApiError("fail"))
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())

    with pytest.raises(HomeAssistantError):
        asyncio.run(entity.async_set_value("bad"))


# ── unique_id ─────────────────────────────────────────────────────────────────


def test_unique_id_contains_serial_and_key(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Unique ID combines serial_number and the entity key."""
    entity = LaMetricTextEntity(coordinator=coordinator, description=_bt_desc())
    assert entity.unique_id == f"{device_state.serial_number}-bluetooth_name"


# ── async_setup_entry ─────────────────────────────────────────────────────────


def test_setup_entry_adds_entity_when_bluetooth_available(
    coordinator: MagicMock,
) -> None:
    """async_setup_entry creates text entities when bluetooth is available."""
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) >= 1


def test_setup_entry_skips_entity_when_bluetooth_unavailable(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """async_setup_entry does not create entities when bluetooth is unavailable."""
    from dataclasses import replace as dcr

    bt = dcr(device_state.bluetooth, available=False)
    coordinator.data = dcr(device_state, bluetooth=bt)

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert collected == []
