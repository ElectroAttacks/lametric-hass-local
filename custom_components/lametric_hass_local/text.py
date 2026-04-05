"""Text platform for LaMetric device configuration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import DeviceState, LaMetricDevice

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricTextEntityDescription(TextEntityDescription):
    """Entity description for a LaMetric text entity.

    Extends :class:`TextEntityDescription` with callable fields
    for reading availability, current value, and issuing set commands.
    """

    available: Callable[[DeviceState], bool]
    get_value: Callable[[DeviceState], str]
    set_value: Callable[[LaMetricDevice, str], Awaitable[Any]]


TEXTS = [
    LaMetricTextEntityDescription(
        icon="mdi:bluetooth",
        key="bluetooth_name",
        translation_key="bluetooth_name",
        native_min=1,
        native_max=248,
        mode=TextMode.TEXT,
        entity_category=EntityCategory.CONFIG,
        available=lambda state: state.bluetooth.available,
        get_value=lambda state: state.bluetooth.name or "",
        set_value=lambda device, name: device.set_bluetooth(name=name),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric text entities for a config entry.

    Text entities are only created when the device reports Bluetooth as available.
    """

    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricTextEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in TEXTS
        if description.available(coordinator.data)
    )


class LaMetricTextEntity(LaMetricEntity, TextEntity):
    """Text entity representing a configurable string field on a LaMetric device."""

    entity_description: LaMetricTextEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricTextEntityDescription,
    ) -> None:
        """Initialize the LaMetric text entity."""

        super().__init__(coordinator)

        self.entity_description = description
        self._attr_mode = description.mode
        self._attr_native_max = description.native_max
        self._attr_native_min = description.native_min
        self._attr_pattern = description.pattern
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def available(self) -> bool:
        """Return True when the coordinator is available and feature is supported."""
        return super().available and self.entity_description.available(
            self.coordinator.data
        )

    @property
    def native_value(self) -> str | None:
        """Return the current text value."""
        return self.entity_description.get_value(self.coordinator.data)

    @lametric_api_exception_handler
    async def async_set_value(self, value: str) -> None:
        """Send the new text value to the device."""
        await self.entity_description.set_value(self.coordinator.device, value)

        await self.coordinator.async_request_refresh()
