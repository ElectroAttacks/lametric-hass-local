"""Light platform for LaMetric devices."""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.components.light.const import ColorMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness
from lametric import DeviceModels, DeviceState, LaMetricDevice

from .coordinator import (
    LaMetricConfigEntry,
    LaMetricCoordinator,
)
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler

BRIGHTNESS_SCALE = (1, 100)


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
        state_get=lambda state: state.display.on,
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

    if coordinator.data.model != DeviceModels.SKY:
        return

    async_add_entities(
        LaMetricLightEntity(coordinator, description) for description in LIGHTS
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
