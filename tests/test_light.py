"""Tests for the LaMetric light platform (SKY model only)."""

import asyncio
import math
from unittest.mock import AsyncMock, MagicMock

from homeassistant.util.color import brightness_to_value, value_to_brightness
from lametric import DeviceModels
from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.light import (
    BRIGHTNESS_SCALE,
    LIGHTS,
    LaMetricLightEntity,
)


def _sky_desc():
    return next(d for d in LIGHTS if d.key == "sky_light")


# ── is_on / brightness ──────────────────────────────────────────────────────


def test_is_on_reflects_display_state(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """is_on mirrors display.on from coordinator data."""
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    assert entity.is_on == device_state.display.on


def test_brightness_converts_from_device_scale(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """HA brightness (0-255) is converted from the device 1-100 scale."""
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    expected = value_to_brightness(
        BRIGHTNESS_SCALE, float(device_state.display.brightness)
    )
    assert entity.brightness == expected


def test_brightness_none_when_display_brightness_none(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """brightness property returns None when display.brightness is None."""
    from dataclasses import replace as dc_replace

    # type: ignore[call-arg]
    display = dc_replace(device_state.display, brightness=None)  # type: ignore[arg-type]
    coordinator.data = dc_replace(device_state, display=display)
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    assert entity.brightness is None


# ── turn_on / turn_off ────────────────────────────────────────────────────────


def test_turn_on_calls_set_display_on(coordinator: MagicMock) -> None:
    """async_turn_on calls set_display(on=True)."""
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_on())

    coordinator.device.set_display.assert_any_await(on=True)


def test_turn_on_with_brightness_calls_set_display_brightness(
    coordinator: MagicMock,
) -> None:
    """async_turn_on with ATTR_BRIGHTNESS also calls set_display with brightness."""
    from homeassistant.components.light import ATTR_BRIGHTNESS

    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_on(**{ATTR_BRIGHTNESS: 128}))

    expected_brightness = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, 128))
    coordinator.device.set_display.assert_any_await(brightness=expected_brightness)


def test_turn_off_calls_set_display_off(coordinator: MagicMock) -> None:
    """async_turn_off calls set_display(on=False)."""
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_off())

    coordinator.device.set_display.assert_awaited_once_with(on=False)


# ── setup_entry guard ─────────────────────────────────────────────────────────


def test_light_not_created_for_time_model(device_state: DeviceState) -> None:
    """Light entities are only created for the SKY model."""
    assert device_state.model != DeviceModels.SKY  # type: ignore[comparison-overlap]
    # Simulate what async_setup_entry does: filter by model
    entities = [d for d in LIGHTS if device_state.model == DeviceModels.SKY]  # type: ignore[comparison-overlap]
    assert entities == []


def test_setup_entry_adds_light_for_sky_model() -> None:
    """async_setup_entry creates a light entity for the SKY model."""
    import asyncio
    from unittest.mock import MagicMock

    from lametric import DeviceModels

    from custom_components.lametric_hass_local.light import async_setup_entry
    from tests.conftest import _build_device_state

    sky_coordinator = MagicMock()
    sky_coordinator.data = _build_device_state(model=DeviceModels.SKY)
    sky_coordinator.async_request_refresh = AsyncMock()

    config_entry = MagicMock()
    config_entry.runtime_data = sky_coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == len(LIGHTS)
