"""Light platform for LaMetric devices."""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.light.const import ColorMode
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.util.color import brightness_to_value, value_to_brightness
from lametric import (
    DeviceModels,
    DeviceState,
    LaMetricApiError,
    LaMetricDevice,
    StreamConfig,
    StreamState,
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


def _coerce_stream_config(value: object) -> StreamConfig:
    """Coerce a plain dict into a StreamConfig dataclass."""
    if isinstance(value, StreamConfig):
        return value
    if isinstance(value, dict):
        # The service schema nests all stream settings under a 'canvas' key.
        data = dict(value)
        if "canvas" in data:
            data = dict(data["canvas"])
        # YAML/JSON may parse bare ``none`` as Python None; fix known enum fields.
        post = data.get("post_process")
        if isinstance(post, dict):
            post = dict(post)
            if post.get("type") is None:
                post["type"] = "none"
            data["post_process"] = post
        return StreamConfig.from_dict(data)
    raise vol.Invalid(f"Cannot convert {type(value)} to StreamConfig")


def _coerce_rgb_data(value: object) -> bytes:
    """Flatten a list of [R, G, B] triplets into raw RGB888 bytes."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, list):
        try:
            flat = [channel for pixel in value for channel in pixel]
            return bytes(flat)
        except (TypeError, ValueError) as err:
            raise vol.Invalid("rgb_data must be a list of [R, G, B] triplets") from err
    raise vol.Invalid(f"Cannot convert {type(value)} to bytes")


@dataclass(frozen=True, kw_only=True)
class LaMetricLightEntityDescription(LightEntityDescription):
    """Description for a LaMetric light entity."""

    brightness_get: Callable[[DeviceState], int | None]
    brightness_set: Callable[[LaMetricDevice, int], Awaitable[Any]]
    state_get: Callable[[DeviceState], bool]
    state_set: Callable[[LaMetricDevice, bool], Awaitable[Any]]


LIGHTS = [
    LaMetricLightEntityDescription(
        key="sky_light",
        translation_key="sky_light",
        brightness_get=lambda state: state.display.brightness,
        brightness_set=lambda device, brightness: device.set_display(
            brightness=brightness
        ),
        state_get=lambda state: bool(state.display.on),
        state_set=lambda device, state: device.set_display(on=state),
    )
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric light entities for a config entry."""

    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricLightEntity(coordinator, description)
        for description in LIGHTS
        if coordinator.data.model == DeviceModels.SKY
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

    entity_description: LaMetricLightEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricLightEntityDescription,
    ) -> None:
        """Initialize the LaMetric light entity."""

        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool | None:
        """Return whether the LaMetric display light is enabled."""

        return self.entity_description.state_get(self.coordinator.data)

    @property
    def brightness(self) -> int | None:
        """Return brightness in Home Assistant 0-255 scale."""

        brightness = self.entity_description.brightness_get(self.coordinator.data)

        if brightness is None:
            return None

        return value_to_brightness(BRIGHTNESS_SCALE, float(brightness))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return stream state as extra attributes."""
        stream: StreamState | None = self.coordinator.stream_state

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

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the display light on and optionally set brightness."""

        await self.entity_description.state_set(self.coordinator.device, True)

        brightness = kwargs.get(ATTR_BRIGHTNESS)

        if brightness is not None:
            brightness = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, brightness))

            await self.entity_description.brightness_set(
                self.coordinator.device, brightness
            )

        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the display light off."""

        await self.entity_description.state_set(self.coordinator.device, False)

        await self.coordinator.async_request_refresh()

    async def _async_start_stream(self, config: StreamConfig) -> dict[str, Any]:
        """Start a pixel-streaming session (SKY only)."""
        try:
            session_id = await self.coordinator.device.start_stream(
                stream_config=config
            )
        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to start stream on LaMetric device at "
                f"{self.coordinator.device.host}."
            ) from error

        if session_id is None:
            return {
                "success": False,
                "message": (
                    f"Failed to start stream on LaMetric device at "
                    f"{self.coordinator.device.host}."
                ),
            }
        return {"success": True, "session_id": session_id}

    async def _async_stop_stream(self) -> None:
        """Stop an active pixel-streaming session (SKY only)."""
        try:
            await self.coordinator.device.stop_stream()
        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to stop stream on LaMetric device at "
                f"{self.coordinator.device.host}."
            ) from error

    async def _async_send_stream_data(self, session_id: str, rgb_data: bytes) -> None:
        """Send RGB pixel data to an active streaming session (SKY only)."""
        try:
            await self.coordinator.device.send_stream_data(
                session_id=session_id,
                rgb888_data=rgb_data,
            )
        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to send stream data to LaMetric device at "
                f"{self.coordinator.device.host}."
            ) from error
