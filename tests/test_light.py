"""Tests for the LaMetric light platform (SKY model only)."""

import asyncio
import math
from collections.abc import Coroutine
from dataclasses import replace as dc_replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
    from typing import cast

    display = dc_replace(device_state.display, brightness=cast(int, None))
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
    """async_turn_on sends on and brightness in one device call."""
    from homeassistant.components.light import ATTR_BRIGHTNESS

    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_on(**{ATTR_BRIGHTNESS: 128}))

    expected_brightness = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, 128))
    coordinator.device.set_display.assert_awaited_once_with(
        on=True,
        brightness=expected_brightness,
    )


def test_turn_off_calls_set_display_off(coordinator: MagicMock) -> None:
    """async_turn_off calls set_display(on=False)."""
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_off())

    coordinator.device.set_display.assert_awaited_once_with(on=False)


def test_turn_on_optimistically_updates_coordinator_state(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """async_turn_on updates the local coordinator state before refresh."""
    from homeassistant.components.light import ATTR_BRIGHTNESS

    coordinator.device.set_display = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_on(**{ATTR_BRIGHTNESS: 128}))

    expected_brightness = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, 128))
    expected_display = dc_replace(
        device_state.display,
        on=True,
        brightness=expected_brightness,
    )
    expected_state = dc_replace(device_state, display=expected_display)
    coordinator.async_set_updated_data.assert_called_once_with(expected_state)


def test_turn_off_optimistically_updates_coordinator_state(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """async_turn_off updates the local coordinator state before refresh."""
    coordinator.device.set_display = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity.async_turn_off())

    expected_display = dc_replace(device_state.display, on=False)
    expected_state = dc_replace(device_state, display=expected_display)
    coordinator.async_set_updated_data.assert_called_once_with(expected_state)


def test_turn_off_schedules_refresh_when_entity_has_hass(
    coordinator: MagicMock,
) -> None:
    """async_turn_off should not block on refresh once the entity is added."""
    scheduled: list[tuple[Coroutine[object, object, object], str]] = []

    def track_task(coro: Coroutine[object, object, object], *, name: str) -> None:
        scheduled.append((coro, name))
        coro.close()

    coordinator.device.set_display = AsyncMock()
    coordinator.async_set_updated_data = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    fake_hass = MagicMock()
    fake_hass.async_create_task = MagicMock(side_effect=track_task)
    entity.entity_id = "light.lametric_sky_light"

    with patch.object(entity, "_get_hass_for_refresh", return_value=fake_hass):
        asyncio.run(entity.async_turn_off())

    coordinator.async_request_refresh.assert_not_awaited()
    fake_hass.async_create_task.assert_called_once()
    assert scheduled[0][1] == "lametric_refresh_light.lametric_sky_light"


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
    from unittest.mock import MagicMock, patch

    from lametric import DeviceModels

    from custom_components.lametric_hass_local.light import async_setup_entry
    from tests.conftest import _build_device_state

    sky_coordinator = MagicMock()
    sky_coordinator.data = _build_device_state(model=DeviceModels.SKY)
    sky_coordinator.async_request_refresh = AsyncMock()

    config_entry = MagicMock()
    config_entry.runtime_data = sky_coordinator

    collected: list = []
    with patch(
        "custom_components.lametric_hass_local.light.async_get_current_platform"
    ):
        asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == len(LIGHTS)


# ── stream entity service methods ─────────────────────────────────────────────


def test_start_stream_returns_session_id(coordinator: MagicMock) -> None:
    """_async_start_stream returns success dict with session_id."""
    from lametric import StreamConfig

    coordinator.device.start_stream = AsyncMock(return_value="sess-abc")
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    stream_cfg = MagicMock(spec=StreamConfig)

    result = asyncio.run(entity._async_start_stream(stream_cfg))

    assert result == {"success": True, "session_id": "sess-abc"}
    coordinator.device.start_stream.assert_awaited_once_with(stream_config=stream_cfg)


def test_start_stream_returns_failure_when_session_id_none(
    coordinator: MagicMock,
) -> None:
    """_async_start_stream returns failure dict when device returns None."""
    from lametric import StreamConfig

    coordinator.device.start_stream = AsyncMock(return_value=None)
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    result = asyncio.run(entity._async_start_stream(MagicMock(spec=StreamConfig)))

    assert result["success"] is False


def test_start_stream_raises_on_api_error(coordinator: MagicMock) -> None:
    """_async_start_stream raises HomeAssistantError on LaMetricApiError."""
    from homeassistant.exceptions import HomeAssistantError
    from lametric import LaMetricApiError, StreamConfig

    coordinator.device.start_stream = AsyncMock(side_effect=LaMetricApiError("fail"))
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    with pytest.raises(HomeAssistantError):
        asyncio.run(entity._async_start_stream(MagicMock(spec=StreamConfig)))


def test_stop_stream_calls_device(coordinator: MagicMock) -> None:
    """_async_stop_stream calls device.stop_stream."""
    coordinator.device.stop_stream = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity._async_stop_stream())

    coordinator.device.stop_stream.assert_awaited_once()


def test_stop_stream_raises_on_api_error(coordinator: MagicMock) -> None:
    """_async_stop_stream raises HomeAssistantError on LaMetricApiError."""
    from homeassistant.exceptions import HomeAssistantError
    from lametric import LaMetricApiError

    coordinator.device.stop_stream = AsyncMock(side_effect=LaMetricApiError("fail"))
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    with pytest.raises(HomeAssistantError):
        asyncio.run(entity._async_stop_stream())


def test_send_stream_data_calls_device(coordinator: MagicMock) -> None:
    """_async_send_stream_data calls device.send_stream_data with correct args."""
    coordinator.device.send_stream_data = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    asyncio.run(entity._async_send_stream_data("sess-1", bytes([255, 0, 0])))

    coordinator.device.send_stream_data.assert_awaited_once_with(
        session_id="sess-1",
        rgb888_data=bytes([255, 0, 0]),
    )


def test_send_stream_data_raises_on_api_error(coordinator: MagicMock) -> None:
    """_async_send_stream_data raises HomeAssistantError on LaMetricApiError."""
    from homeassistant.exceptions import HomeAssistantError
    from lametric import LaMetricApiError

    coordinator.device.send_stream_data = AsyncMock(
        side_effect=LaMetricApiError("fail")
    )
    entity = LaMetricLightEntity(coordinator, _sky_desc())

    with pytest.raises(HomeAssistantError):
        asyncio.run(entity._async_send_stream_data("sess-1", bytes([0, 0, 0])))


# ── extra_state_attributes ────────────────────────────────────────────────────


def test_extra_state_attributes_returns_empty_when_stream_state_none(
    coordinator: MagicMock,
) -> None:
    """extra_state_attributes is empty when coordinator.stream_state is None."""
    coordinator.stream_state = None
    entity = LaMetricLightEntity(coordinator, _sky_desc())
    assert entity.extra_state_attributes == {}


def test_extra_state_attributes_returns_stream_data_when_stream_state_present(
    coordinator: MagicMock,
) -> None:
    """extra_state_attributes includes stream status and canvas dimensions."""
    stream = MagicMock()
    stream.status = "receiving"
    stream.canvas.pixel.size.height = 8
    stream.canvas.pixel.size.width = 24
    stream.canvas.triangle.size.height = 16
    stream.canvas.triangle.size.width = 48
    coordinator.stream_state = stream

    entity = LaMetricLightEntity(coordinator, _sky_desc())
    attrs = entity.extra_state_attributes

    assert attrs["stream_status"] == "receiving"
    assert attrs["canvas_pixel"] == {"height": 8, "width": 24}
    assert attrs["canvas_triangle"] == {"height": 16, "width": 48}
