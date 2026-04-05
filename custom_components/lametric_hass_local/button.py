"""Button platform for LaMetric device actions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import LaMetricDevice

from .coordinator import (
    LaMetricConfigEntry,
    LaMetricCoordinator,
)
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricButtonEntityDescription(ButtonEntityDescription):
    """Description for a LaMetric button action."""

    action: Callable[[LaMetricDevice], Awaitable[Any]]


BUTTONS = [
    LaMetricButtonEntityDescription(
        icon="mdi:skip-next",
        key="next_app",
        translation_key="next_app",
        action=lambda device: device.activate_next_app(),
    ),
    LaMetricButtonEntityDescription(
        icon="mdi:skip-previous",
        key="previous_app",
        translation_key="previous_app",
        action=lambda device: device.activate_previous_app(),
    ),
    LaMetricButtonEntityDescription(
        icon="mdi:bell-off",
        key="dismiss_current_notification",
        translation_key="dismiss_current_notification",
        action=lambda device: device.dismiss_current_notification(),
    ),
    LaMetricButtonEntityDescription(
        icon="mdi:bell-remove",
        key="dismiss_all_notifications",
        translation_key="dismiss_all_notifications",
        action=lambda device: device.dismiss_all_notifications(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric button entities for a config entry."""

    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricButtonEntity(coordinator, description) for description in BUTTONS
    )


class LaMetricButtonEntity(LaMetricEntity, ButtonEntity):
    """Button entity that triggers an action on the LaMetric device."""

    entity_description: LaMetricButtonEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricButtonEntityDescription,
    ):
        """Initialize the button entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @lametric_api_exception_handler
    async def async_press(self) -> None:
        """Run the configured button action on the device."""
        await self.entity_description.action(self.coordinator.device)

        await super().async_press()

        await self.coordinator.async_request_refresh()
