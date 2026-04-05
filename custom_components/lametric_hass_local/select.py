"""Select platform for LaMetric device configuration options."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import BrightnessMode, DeviceModels, DeviceState, LaMetricDevice

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricSelectEntityDescription(SelectEntityDescription):
    """Description for a LaMetric select, including get/set accessors."""

    available: Callable[[DeviceState], bool]
    get_current: Callable[[DeviceState], str]
    set_current: Callable[[LaMetricDevice, str], Awaitable[Any]]


SELECTS = [
    LaMetricSelectEntityDescription(
        icon="mdi:brightness-auto",
        key="brightness_mode",
        translation_key="brightness_mode",
        entity_category=EntityCategory.CONFIG,
        options=[mode.value for mode in BrightnessMode],
        available=lambda state: state.model != DeviceModels.SKY,
        get_current=lambda state: state.display.brightness_mode.value,
        set_current=lambda device, option: device.set_display(
            brightness_mode=BrightnessMode(option)
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric select entities for a config entry."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricSelectEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SELECTS
        if description.available(coordinator.data)
    )


class LaMetricSelectEntity(LaMetricEntity, SelectEntity):
    """Select entity for choosing a configuration option on the LaMetric device."""

    entity_description: LaMetricSelectEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the currently active option."""
        return self.entity_description.get_current(self.coordinator.data)

    @lametric_api_exception_handler
    async def async_select_option(self, option: str) -> None:
        """Apply the selected option on the device."""
        await self.entity_description.set_current(self.coordinator.device, option)

        await self.coordinator.async_request_refresh()
