"""Tests for the LaMetric SKY light platform."""

import asyncio
import math
from dataclasses import replace as dc_replace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.color import brightness_to_value, value_to_brightness
from lametric import (
    DeviceModels,
    LaMetricApiError,
    LaMetricConnectionError,
    StreamConfig,
)

from custom_components.lametric_hass_local.const import (
    CONF_STREAM_CONFIG,
    CONF_STREAM_RGB_DATA,
    CONF_STREAM_SESSION_ID,
    SERVICE_SEND_STREAM_DATA,
    SERVICE_START_STREAM,
    SERVICE_STOP_STREAM,
)
from custom_components.lametric_hass_local.light import (
    LIGHTS,
    LaMetricLightEntity,
    _coerce_rgb_data,
    _coerce_stream_config,
    async_setup_entry,
)
from tests.conftest import _build_device_state


def _sky_description():
    return LIGHTS[0]


def _build_sky_coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = _build_device_state(model=DeviceModels.SKY)
    coordinator.stream_state = None
    coordinator.last_update_success = True
    coordinator.device.host = "192.168.1.100"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_update_listeners = MagicMock()
    return coordinator


def _build_stream_config() -> StreamConfig:
    return StreamConfig.from_dict(
        {
            "fill_type": "tile",
            "render_mode": "pixel",
            "post_process": {"type": "none"},
        }
    )


def test_coerce_stream_config_returns_existing_instance() -> None:
    """Existing StreamConfig instances should pass through unchanged."""
    config = _build_stream_config()

    assert _coerce_stream_config(config) is config


def test_coerce_stream_config_accepts_nested_canvas_mapping() -> None:
    """Service payloads may nest the config below the canvas key."""
    config = _coerce_stream_config(
        {
            "canvas": {
                "fill_type": "tile",
                "render_mode": "pixel",
                "post_process": {"type": None},
            }
        }
    )

    assert isinstance(config, StreamConfig)
    assert config.post_process.type.value == "none"


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("invalid", "Cannot convert"),
        ({"canvas": "invalid"}, "config.canvas must be an object"),
        ({"fill_type": "tile"}, "config is not a valid StreamConfig"),
    ],
)
def test_coerce_stream_config_rejects_invalid_values(
    value: object, message: str
) -> None:
    """Invalid stream config payloads should raise voluptuous errors."""
    with pytest.raises(vol.Invalid, match=message):
        _coerce_stream_config(value)


def test_coerce_rgb_data_passes_bytes_through() -> None:
    """Raw RGB byte payloads should not be modified."""
    payload = bytes([1, 2, 3])

    assert _coerce_rgb_data(payload) is payload


def test_coerce_rgb_data_flattens_rgb_triplets() -> None:
    """Triplet payloads should be flattened to RGB888 bytes."""
    assert _coerce_rgb_data([[255, 0, 0], [0, 255, 0]]) == bytes([255, 0, 0, 0, 255, 0])


@pytest.mark.parametrize(
    "value",
    [
        "invalid",
        [[255, 0]],
        [[255, 0, 256]],
        [[255, False, 0]],
    ],
)
def test_coerce_rgb_data_rejects_invalid_values(value: object) -> None:
    """Invalid RGB payloads should fail schema validation."""
    with pytest.raises(vol.Invalid, match="rgb_data must be a list|Cannot convert"):
        _coerce_rgb_data(value)


def test_async_setup_entry_skips_non_sky_devices() -> None:
    """Non-SKY devices should not create a light entity or services."""
    coordinator = MagicMock()
    coordinator.data = _build_device_state(model=DeviceModels.TIME)
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator
    add_entities = MagicMock()

    asyncio.run(async_setup_entry(MagicMock(), config_entry, add_entities))

    add_entities.assert_not_called()


def test_async_setup_entry_adds_entity_and_registers_services() -> None:
    """SKY setup should add the light entity and entity services."""
    coordinator = _build_sky_coordinator()
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator
    add_entities = MagicMock()
    platform = MagicMock()

    with patch(
        "custom_components.lametric_hass_local.light.async_get_current_platform",
        return_value=platform,
    ):
        asyncio.run(async_setup_entry(MagicMock(), config_entry, add_entities))

    add_entities.assert_called_once()
    added_entities = list(add_entities.call_args.args[0])
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], LaMetricLightEntity)

    assert platform.async_register_entity_service.call_args_list == [
        call(
            SERVICE_START_STREAM,
            {vol.Required(CONF_STREAM_CONFIG): _coerce_stream_config},
            "_async_start_stream",
            supports_response=SupportsResponse.OPTIONAL,
        ),
        call(
            SERVICE_STOP_STREAM,
            {},
            "_async_stop_stream",
        ),
        call(
            SERVICE_SEND_STREAM_DATA,
            {
                vol.Required(CONF_STREAM_SESSION_ID): str,
                vol.Required(CONF_STREAM_RGB_DATA): _coerce_rgb_data,
            },
            "_async_send_stream_data",
        ),
    ]


def test_entity_state_properties_reflect_coordinator_data() -> None:
    """Availability, power state and brightness should come from coordinator data."""
    coordinator = _build_sky_coordinator()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    assert entity.available is True
    assert entity.is_on is True
    assert entity.brightness == value_to_brightness(
        (
            int(coordinator.data.display.brightness_limit.min),
            int(coordinator.data.display.brightness_limit.max),
        ),
        float(coordinator.data.display.brightness),
    )


def test_entity_unavailable_when_coordinator_failed_or_display_state_unknown() -> None:
    """Availability should drop when the device is offline or on/off is unknown."""
    coordinator = _build_sky_coordinator()
    coordinator.last_update_success = False
    entity = LaMetricLightEntity(coordinator, _sky_description())
    assert entity.available is False

    coordinator.last_update_success = True
    coordinator.data = dc_replace(
        coordinator.data,
        display=dc_replace(coordinator.data.display, on=None),
    )
    assert entity.available is False


def test_extra_state_attributes_are_empty_without_stream_state() -> None:
    """No stream state should mean no extra attributes."""
    coordinator = _build_sky_coordinator()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    assert entity.extra_state_attributes == {}


def test_extra_state_attributes_expose_stream_dimensions() -> None:
    """Stream metadata should be exposed as extra state attributes."""
    coordinator = _build_sky_coordinator()
    coordinator.stream_state = MagicMock()
    coordinator.stream_state.status = "receiving"
    coordinator.stream_state.canvas.pixel.size.height = 8
    coordinator.stream_state.canvas.pixel.size.width = 37
    coordinator.stream_state.canvas.triangle.size.height = 16
    coordinator.stream_state.canvas.triangle.size.width = 74
    entity = LaMetricLightEntity(coordinator, _sky_description())

    assert entity.extra_state_attributes == {
        "stream_status": "receiving",
        "canvas_pixel": {"height": 8, "width": 37},
        "canvas_triangle": {"height": 16, "width": 74},
    }


def test_async_turn_on_sets_display_and_refreshes() -> None:
    """Turning the light on should call set_display and refresh the coordinator."""
    coordinator = _build_sky_coordinator()
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    asyncio.run(entity.async_turn_on())

    coordinator.device.set_display.assert_awaited_once_with(on=True, brightness=None)
    coordinator.async_request_refresh.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()


def test_async_turn_on_converts_brightness_to_device_scale() -> None:
    """Brightness should be converted from HA scale to LaMetric scale."""
    coordinator = _build_sky_coordinator()
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    asyncio.run(entity.async_turn_on(brightness=128))

    expected = math.ceil(
        brightness_to_value(
            (
                int(coordinator.data.display.brightness_limit.min),
                int(coordinator.data.display.brightness_limit.max),
            ),
            128,
        )
    )
    coordinator.device.set_display.assert_awaited_once_with(
        on=True, brightness=expected
    )


def test_async_turn_off_sets_display_and_refreshes() -> None:
    """Turning the light off should call set_display and refresh the coordinator."""
    coordinator = _build_sky_coordinator()
    coordinator.device.set_display = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    asyncio.run(entity.async_turn_off())

    coordinator.device.set_display.assert_awaited_once_with(on=False)
    coordinator.async_request_refresh.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()


def test_async_turn_on_marks_coordinator_unavailable_on_connection_error() -> None:
    """Connection failures should mark the coordinator unavailable."""
    coordinator = _build_sky_coordinator()
    coordinator.device.set_display = AsyncMock(
        side_effect=LaMetricConnectionError("offline")
    )
    entity = LaMetricLightEntity(coordinator, _sky_description())

    with pytest.raises(HomeAssistantError, match="Failed to connect to LaMetric"):
        asyncio.run(entity.async_turn_on())

    assert coordinator.last_update_success is False
    coordinator.async_update_listeners.assert_called_once()
    coordinator.async_request_refresh.assert_not_awaited()


def test_start_stream_returns_session_id_and_refreshes() -> None:
    """Starting a stream should return the session id and refresh state."""
    coordinator = _build_sky_coordinator()
    coordinator.device.start_stream = AsyncMock(return_value="session-123")
    entity = LaMetricLightEntity(coordinator, _sky_description())
    config = _build_stream_config()

    result = asyncio.run(entity._async_start_stream(config))

    assert result == {"success": True, "session_id": "session-123"}
    coordinator.device.start_stream.assert_awaited_once_with(stream_config=config)
    coordinator.async_request_refresh.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()


def test_start_stream_returns_failure_payload_when_device_returns_none() -> None:
    """A missing session id should produce a failure response without refresh."""
    coordinator = _build_sky_coordinator()
    coordinator.device.start_stream = AsyncMock(return_value=None)
    entity = LaMetricLightEntity(coordinator, _sky_description())

    result = asyncio.run(entity._async_start_stream(_build_stream_config()))

    assert result == {
        "success": False,
        "message": "Failed to start stream on LaMetric device at 192.168.1.100.",
    }
    coordinator.async_request_refresh.assert_not_awaited()
    coordinator.async_update_listeners.assert_called_once()


def test_start_stream_uses_custom_connection_error_message() -> None:
    """The stream start service should expose its service-specific error text."""
    coordinator = _build_sky_coordinator()
    coordinator.device.start_stream = AsyncMock(
        side_effect=LaMetricConnectionError("offline")
    )
    entity = LaMetricLightEntity(coordinator, _sky_description())

    with pytest.raises(
        HomeAssistantError,
        match="while starting the pixel stream",
    ):
        asyncio.run(entity._async_start_stream(_build_stream_config()))

    assert coordinator.last_update_success is False
    coordinator.async_update_listeners.assert_called_once()


def test_stop_stream_calls_device_and_refreshes() -> None:
    """Stopping a stream should call the device API and refresh."""
    coordinator = _build_sky_coordinator()
    coordinator.device.stop_stream = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_description())

    asyncio.run(entity._async_stop_stream())

    coordinator.device.stop_stream.assert_awaited_once_with()
    coordinator.async_request_refresh.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()


def test_send_stream_data_calls_device_and_updates_listeners() -> None:
    """Sending stream data should pass RGB bytes straight through."""
    coordinator = _build_sky_coordinator()
    coordinator.device.send_stream_data = AsyncMock()
    entity = LaMetricLightEntity(coordinator, _sky_description())
    rgb_data = bytes([1, 2, 3])

    asyncio.run(entity._async_send_stream_data("session-123", rgb_data))

    coordinator.device.send_stream_data.assert_awaited_once_with(
        session_id="session-123",
        rgb888_data=rgb_data,
    )
    coordinator.async_update_listeners.assert_called_once()


def test_send_stream_data_uses_custom_api_error_message() -> None:
    """The stream send service should expose its service-specific API error text."""
    coordinator = _build_sky_coordinator()
    coordinator.device.send_stream_data = AsyncMock(
        side_effect=LaMetricApiError("bad request")
    )
    entity = LaMetricLightEntity(coordinator, _sky_description())

    with pytest.raises(
        HomeAssistantError,
        match="API error while sending pixel stream data",
    ):
        asyncio.run(entity._async_send_stream_data("session-123", bytes([1, 2, 3])))

    coordinator.async_update_listeners.assert_not_called()
