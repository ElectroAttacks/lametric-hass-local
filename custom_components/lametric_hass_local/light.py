"""Light platform for LaMetric devices."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.light.const import ColorMode
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.util.color import brightness_to_value, value_to_brightness
from lametric import (
    DeviceModels,
    StreamConfig,
)

from .const import (
    CONF_STREAM_CONFIG,
    CONF_STREAM_RGB_DATA,
    CONF_STREAM_SESSION_ID,
    SERVICE_SEND_STREAM_DATA,
    SERVICE_START_STREAM,
    SERVICE_STOP_STREAM,
)
from .coordinator import (
    LaMetricConfigEntry,
    LaMetricCoordinator,
)
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler

BRIGHTNESS_SCALE = (1, 100)


LIGHTS = [
    LightEntityDescription(
        key="sky_light",
        translation_key="sky_light",
    )
]


def _coerce_stream_config(value: object) -> StreamConfig:
    """Coerce a plain dict into a StreamConfig dataclass."""
    if isinstance(value, StreamConfig):
        return value

    if not isinstance(value, Mapping):
        raise vol.Invalid(f"Cannot convert {type(value)} to StreamConfig")

    data = dict(cast(Mapping[str, Any], value))

    if "canvas" in data:
        canvas = data["canvas"]

        if not isinstance(canvas, Mapping):
            raise vol.Invalid("config.canvas must be an object")

        data = dict(cast(Mapping[str, Any], canvas))

    post = data.get("post_process")

    if isinstance(post, Mapping):
        normalized_post = dict(cast(Mapping[str, Any], post))

        if normalized_post.get("type") is None:
            normalized_post["type"] = "none"

        params = normalized_post.get("params")

        if isinstance(params, Mapping):
            normalized_params = dict(cast(Mapping[str, Any], params))

            if normalized_params.get("effect_type") is None:
                normalized_params["effect_type"] = "none"

            normalized_post["params"] = normalized_params

        data["post_process"] = normalized_post

    try:
        from_dict = cast(
            Callable[[Mapping[str, Any]], StreamConfig], StreamConfig.from_dict
        )

        return from_dict(data)

    except Exception as err:
        raise vol.Invalid("config is not a valid StreamConfig") from err


def _coerce_rgb_triplet(pixel: object) -> tuple[int, int, int]:
    """Validate a single RGB triplet payload."""
    if not isinstance(pixel, (list, tuple)):
        raise vol.Invalid("rgb_data must be a list of [R, G, B] triplets")

    channels: list[Any] = list(pixel)

    if len(channels) != 3:
        raise vol.Invalid("rgb_data must be a list of [R, G, B] triplets")

    validated: list[int] = []

    for channel in channels:
        if (
            isinstance(channel, bool)
            or not isinstance(channel, int)
            or not 0 <= channel <= 255
        ):
            raise vol.Invalid("rgb_data must be a list of [R, G, B] triplets")

        validated.append(channel)

    return validated[0], validated[1], validated[2]


def _coerce_rgb_data(value: object) -> bytes:
    """Flatten a list of [R, G, B] triplets into raw RGB888 bytes."""
    if isinstance(value, bytes):
        return value

    if not isinstance(value, list):
        raise vol.Invalid(f"Cannot convert {type(value)} to bytes")

    flat: list[int] = []

    for pixel in cast(list[object], value):
        flat.extend(_coerce_rgb_triplet(pixel))

    return bytes(flat)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric light entities for a config entry."""
    coordinator = config_entry.runtime_data
    if coordinator.data.model != DeviceModels.SKY:
        return

    async_add_entities(
        LaMetricLightEntity(coordinator, description) for description in LIGHTS
    )

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_START_STREAM,
        {vol.Required(CONF_STREAM_CONFIG): _coerce_stream_config},
        "_async_start_stream",
        supports_response=SupportsResponse.OPTIONAL,
    )
    platform.async_register_entity_service(
        SERVICE_STOP_STREAM,
        {},
        "_async_stop_stream",
    )

    platform.async_register_entity_service(
        SERVICE_SEND_STREAM_DATA,
        {
            vol.Required(CONF_STREAM_SESSION_ID): str,
            vol.Required(CONF_STREAM_RGB_DATA): _coerce_rgb_data,
        },
        "_async_send_stream_data",
    )


class LaMetricLightEntity(LaMetricEntity, LightEntity):
    """Light entity backed by LaMetric display state."""

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LightEntityDescription,
    ) -> None:
        """Initialize the LaMetric light entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS

    def _brightness_scale(self) -> tuple[int, int]:
        """Return the brightness range currently enforced by the device."""
        if limits := self.coordinator.data.display.brightness_limit:
            return int(limits.min), int(limits.max)

        return BRIGHTNESS_SCALE

    @property
    def available(self) -> bool:
        """Return whether the light is currently usable."""
        display = self.coordinator.data.display
        return self.coordinator.last_update_success and display.on is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the display is on."""
        return self.coordinator.data.display.on

    @property
    def brightness(self) -> int | None:
        """Return brightness on Home Assistant's 0-255 scale."""
        brightness = self.coordinator.data.display.brightness
        return value_to_brightness(self._brightness_scale(), float(brightness))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the current stream state metadata."""
        stream = self.coordinator.stream_state
        if stream is None:
            return {}

        return {
            "stream_status": stream.status,
            "canvas_pixel": {
                "height": stream.canvas.pixel.size.height,
                "width": stream.canvas.pixel.size.width,
            },
            "canvas_triangle": {
                "height": stream.canvas.triangle.size.height,
                "width": stream.canvas.triangle.size.width,
            },
        }

    @lametric_api_exception_handler
    async def async_turn_on(self, /, **kwargs: Any) -> None:
        """Turn the display light on and optionally set brightness."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if brightness is not None:
            brightness = math.ceil(
                brightness_to_value(self._brightness_scale(), brightness)
            )

        await self.coordinator.device.set_display(on=True, brightness=brightness)

        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler
    async def async_turn_off(self, /, **_kwargs: Any) -> None:
        """Turn the display light off."""

        await self.coordinator.device.set_display(on=False)

        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler(
        connection_error_message=(
            "Failed to connect to LaMetric device at {host} while starting the "
            "pixel stream."
        ),
        api_error_message=(
            "API error while starting the pixel stream on LaMetric device at {host}."
        ),
    )
    async def _async_start_stream(self, config: StreamConfig) -> dict[str, Any]:
        """Start a pixel-streaming session (SKY only)."""
        session_id = await self.coordinator.device.start_stream(stream_config=config)

        if session_id is None:
            return {
                "success": False,
                "message": (
                    f"Failed to start stream on LaMetric device at "
                    f"{self.coordinator.device.host}."
                ),
            }

        await self.coordinator.async_request_refresh()

        return {"success": True, "session_id": session_id}

    @lametric_api_exception_handler(
        connection_error_message=(
            "Failed to connect to LaMetric device at {host} while stopping the "
            "pixel stream."
        ),
        api_error_message=(
            "API error while stopping the pixel stream on LaMetric device at {host}."
        ),
    )
    async def _async_stop_stream(self) -> None:
        """Stop an active pixel-streaming session (SKY only)."""
        await self.coordinator.device.stop_stream()

        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler(
        connection_error_message=(
            "Failed to connect to LaMetric device at {host} while sending pixel "
            "stream data."
        ),
        api_error_message=(
            "API error while sending pixel stream data to LaMetric device at {host}."
        ),
    )
    async def _async_send_stream_data(self, session_id: str, rgb_data: bytes) -> None:
        """Send RGB pixel data to an active streaming session (SKY only)."""
        await self.coordinator.device.send_stream_data(
            session_id=session_id,
            rgb888_data=rgb_data,
        )
