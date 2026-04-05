"""Tests for the LaMetric select platform."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from lametric import DeviceModels
from lametric.device_states import (  # type: ignore[attr-defined]
    BrightnessMode,
    DeviceState,
)

from custom_components.lametric_hass_local.select import (
    SELECTS,
    LaMetricSelectEntity,
)


def _brightness_mode_desc():
    return next(s for s in SELECTS if s.key == "brightness_mode")


def test_current_option_returns_brightness_mode(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """current_option reflects the display brightness_mode value."""
    entity = LaMetricSelectEntity(
        coordinator=coordinator, description=_brightness_mode_desc()
    )
    assert entity.current_option == device_state.display.brightness_mode.value


def test_not_available_for_sky_model(device_state: DeviceState) -> None:
    """brightness_mode select is not available for the SKY model."""
    from dataclasses import replace as dc_replace

    sky_state = dc_replace(device_state, model=DeviceModels.SKY)
    assert not _brightness_mode_desc().available(sky_state)


def test_available_for_time_model(device_state: DeviceState) -> None:
    """brightness_mode select is available for the TIME model."""
    assert _brightness_mode_desc().available(device_state)


def test_select_option_calls_set_display(coordinator: MagicMock) -> None:
    """async_select_option calls set_display with the chosen BrightnessMode."""
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricSelectEntity(
        coordinator=coordinator, description=_brightness_mode_desc()
    )

    asyncio.run(entity.async_select_option(BrightnessMode.MANUAL.value))

    coordinator.device.set_display.assert_awaited_once_with(
        brightness_mode=BrightnessMode.MANUAL
    )


def test_unique_id_contains_serial_and_key(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Unique ID is serial_number + key."""
    entity = LaMetricSelectEntity(
        coordinator=coordinator, description=_brightness_mode_desc()
    )
    assert entity.unique_id == f"{device_state.serial_number}-brightness_mode"


def test_available_false_for_sky_model(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """available returns False for the SKY model."""
    from dataclasses import replace as dc_replace

    from lametric import DeviceModels

    coordinator.data = dc_replace(device_state, model=DeviceModels.SKY)
    entity = LaMetricSelectEntity(
        coordinator=coordinator, description=_brightness_mode_desc()
    )
    assert entity.available is False


def test_setup_entry_adds_entities(coordinator: MagicMock) -> None:
    """async_setup_entry adds select entities for available descriptions."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.select import async_setup_entry

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) >= 1
