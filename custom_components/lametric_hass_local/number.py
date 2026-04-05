"""Number platform for LaMetric device configuration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import DeviceModels, DeviceState, IntRange, LaMetricDevice

from .coordinator import (
    LaMetricConfigEntry,
    LaMetricCoordinator,
)
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricNumberEntityDescription(NumberEntityDescription):
    """Description for a LaMetric number, including value and range accessors."""

    available: Callable[[DeviceState], bool]
    get_value: Callable[[DeviceState], int | None]
    set_value: Callable[[LaMetricDevice, int], Awaitable[Any]]
    get_range: Callable[[DeviceState], IntRange | None]


NUMBERS = [
    LaMetricNumberEntityDescription(
        icon="mdi:brightness-6",
        key="brightness",
        translation_key="brightness",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
        available=lambda state: state.model != DeviceModels.SKY,
        get_range=lambda state: state.display.brightness_limit,
        get_value=lambda state: state.display.brightness,
        set_value=lambda device, brightness: device.set_display(brightness=brightness),
    ),
    LaMetricNumberEntityDescription(
        icon="mdi:volume-high",
        key="volume",
        translation_key="volume",
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.CONFIG,
        available=lambda state: state.audio.available,
        get_range=lambda state: state.audio.volume_range if state.audio else None,
        get_value=lambda state: state.audio.volume if state.audio else 0,
        set_value=lambda device, volume: device.set_audio(volume=volume),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric number entities for a config entry."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricNumberEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in NUMBERS
        if description.available(coordinator.data)
    )


class LaMetricNumberEntity(LaMetricEntity, NumberEntity):
    """Number entity for adjusting a numeric value on the LaMetric device."""

    entity_description: LaMetricNumberEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def available(self) -> bool:
        """Return True when the coordinator is available and feature is supported."""
        return super().available and self.entity_description.available(
            self.coordinator.data
        )

    @property
    def native_value(self) -> int | None:
        """Return the current numeric value."""
        return self.entity_description.get_value(self.coordinator.data)

    @property
    def native_min_value(self) -> int:
        """Return the minimum allowed value from the device."""
        if limits := self.entity_description.get_range(self.coordinator.data):
            return int(limits.min)
        return 0

    @property
    def native_max_value(self) -> int:
        """Return the maximum allowed value from the device."""
        if limits := self.entity_description.get_range(self.coordinator.data):
            return int(limits.max)
        return 100

    @lametric_api_exception_handler
    async def async_set_native_value(self, value: float) -> None:
        """Send the new value to the device."""
        await self.entity_description.set_value(self.coordinator.device, int(value))

        await self.coordinator.async_request_refresh()
