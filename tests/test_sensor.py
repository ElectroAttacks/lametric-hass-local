"""Tests for the LaMetric sensor platform."""

from unittest.mock import MagicMock

from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.sensor import (
    SENSORS,
    LaMetricSensorEntity,
)


def test_rssi_sensor_returns_wifi_signal_strength(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """RSSI sensor value equals wifi.signal_strength from coordinator data."""
    description = next(s for s in SENSORS if s.key == "rssi")
    entity = LaMetricSensorEntity(coordinator=coordinator, description=description)

    assert entity.native_value == device_state.wifi.signal_strength


def test_sensor_unique_id_contains_serial_and_key(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Unique ID is composed of serial_number and the sensor key."""
    description = next(s for s in SENSORS if s.key == "rssi")
    entity = LaMetricSensorEntity(coordinator=coordinator, description=description)

    assert entity.unique_id == f"{device_state.serial_number}-{description.key}"


def test_rssi_sensor_returns_none_when_signal_absent(
    coordinator: MagicMock,
) -> None:
    """Sensor returns None when the accessor returns None."""
    description = next(s for s in SENSORS if s.key == "rssi")

    # Override signal_strength to None via a custom get_value
    from dataclasses import replace

    null_description = replace(description, get_value=lambda _state: None)
    entity = LaMetricSensorEntity(coordinator=coordinator, description=null_description)

    assert entity.native_value is None


def test_setup_entry_adds_sensor_entities(coordinator: MagicMock) -> None:
    """async_setup_entry adds one entity per SENSORS description."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.sensor import SENSORS, async_setup_entry

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == len(SENSORS)
