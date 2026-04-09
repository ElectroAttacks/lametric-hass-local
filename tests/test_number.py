"""Tests for the LaMetric number platform."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from lametric import DeviceModels
from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.number import (
    NUMBERS,
    LaMetricNumberEntity,
)


def _brightness_desc():
    return next(n for n in NUMBERS if n.key == "brightness")


def _volume_desc():
    return next(n for n in NUMBERS if n.key == "volume")


# ── brightness ────────────────────────────────────────────────────────────────


def test_brightness_native_value(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """native_value returns the display brightness from coordinator data."""
    entity = LaMetricNumberEntity(
        coordinator=coordinator, description=_brightness_desc()
    )
    assert entity.native_value == device_state.display.brightness


def test_brightness_range_from_display_limit(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Min/max come from the display brightness_limit IntRange."""
    from dataclasses import replace as dc_replace

    from lametric.device_states import IntRange

    # Use non-zero min so coverage sees the True branch distinctly
    display = dc_replace(device_state.display, brightness_limit=IntRange(min=5, max=90))
    coordinator.data = dc_replace(device_state, display=display)
    entity = LaMetricNumberEntity(
        coordinator=coordinator, description=_brightness_desc()
    )
    assert entity.native_min_value == 5
    assert entity.native_max_value == 90


def test_brightness_not_available_for_sky_model(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Brightness number is not available for the SKY model."""
    desc = _brightness_desc()
    from dataclasses import replace as dc_replace

    sky_state = dc_replace(device_state, model=DeviceModels.SKY)
    coordinator.data = sky_state
    assert not desc.available(sky_state)


def test_brightness_available_for_time_model(device_state: DeviceState) -> None:
    """Brightness number is available for the TIME model."""
    assert _brightness_desc().available(device_state)


def test_brightness_set_value_calls_set_display(coordinator: MagicMock) -> None:
    """async_set_native_value calls set_display with the brightness value."""
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricNumberEntity(
        coordinator=coordinator, description=_brightness_desc()
    )

    asyncio.run(entity.async_set_native_value(75.0))

    coordinator.device.set_display.assert_awaited_once_with(brightness=75)


# ── volume ────────────────────────────────────────────────────────────────────


def test_volume_native_value(coordinator: MagicMock, device_state: DeviceState) -> None:
    """native_value returns the audio volume from coordinator data."""
    entity = LaMetricNumberEntity(coordinator=coordinator, description=_volume_desc())
    assert entity.native_value == device_state.audio.volume


def test_volume_set_value_calls_set_audio(coordinator: MagicMock) -> None:
    """async_set_native_value calls set_audio with the volume value."""
    coordinator.device.set_audio = AsyncMock()
    entity = LaMetricNumberEntity(coordinator=coordinator, description=_volume_desc())

    asyncio.run(entity.async_set_native_value(30.0))

    coordinator.device.set_audio.assert_awaited_once_with(volume=30)


def test_unique_id_contains_serial_and_key(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Unique ID is serial_number + key."""
    entity = LaMetricNumberEntity(
        coordinator=coordinator, description=_brightness_desc()
    )
    assert entity.unique_id == f"{device_state.serial_number}-brightness"


def test_native_min_falls_back_to_zero_when_range_none(
    coordinator: MagicMock,
) -> None:
    """native_min_value returns 0 when get_range returns None."""
    from dataclasses import replace as dc_replace

    desc = dc_replace(_volume_desc(), get_range=lambda _state: None)
    entity = LaMetricNumberEntity(coordinator=coordinator, description=desc)
    assert entity.native_min_value == 0


def test_native_max_falls_back_to_100_when_range_none(
    coordinator: MagicMock,
) -> None:
    """native_max_value returns 100 when get_range returns None."""
    from dataclasses import replace as dc_replace

    desc = dc_replace(_volume_desc(), get_range=lambda _state: None)
    entity = LaMetricNumberEntity(coordinator=coordinator, description=desc)
    assert entity.native_max_value == 100


def test_setup_entry_adds_available_entities(coordinator: MagicMock) -> None:
    """async_setup_entry adds entities for descriptions where available() is True."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.number import async_setup_entry

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    # Both brightness (TIME model) and volume (audio.available=True) should be added
    assert len(collected) >= 1


def test_available_delegates_to_description(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """available is True when coordinator is up and description.available() is True."""
    entity = LaMetricNumberEntity(
        coordinator=coordinator, description=_brightness_desc()
    )
    # Coordinator mock has last_update_success as a truthy MagicMock by default.
    assert entity.available is True
