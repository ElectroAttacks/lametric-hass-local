"""Switch platform for LaMetric device controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import DeviceState, LaMetricDevice

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricSwitchEntityDescription(SwitchEntityDescription):
    """Entity description for a LaMetric switch.

    Extends :class:`SwitchEntityDescription` with callable fields
    for reading availability, state, and issuing set commands.
    """

    available: Callable[[DeviceState], bool]
    get_state: Callable[[DeviceState], bool]
    set_state: Callable[[LaMetricDevice, bool], Awaitable[Any]]


SWITCHES = [
    LaMetricSwitchEntityDescription(
        icon="mdi:monitor-eye",
        key="display_on",
        translation_key="display_on",
        entity_category=EntityCategory.CONFIG,
        available=lambda state: state.display.on is not None,
        get_state=lambda state: bool(state.display.on),
        set_state=lambda device, on: device.set_display(on=on),
    ),
    LaMetricSwitchEntityDescription(
        icon="mdi:bluetooth",
        key="bluetooth_active",
        translation_key="bluetooth_active",
        entity_category=EntityCategory.CONFIG,
        available=lambda state: state.bluetooth.available,
        get_state=lambda state: state.bluetooth.active or False,
        set_state=lambda device, active: device.set_bluetooth(active=active),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric switch entities for a config entry.

    Switch entities are not created for the SKY model, which lacks
    the hardware controls exposed by these switches.
    """

    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricSwitchEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SWITCHES
        if description.available(coordinator.data)
    )


class LaMetricSwitchEntity(LaMetricEntity, SwitchEntity):
    """Switch entity representing a controllable LaMetric device feature."""

    entity_description: LaMetricSwitchEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricSwitchEntityDescription,
    ) -> None:
        """Initialize the LaMetric switch entity."""

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
    def is_on(self) -> bool:
        """Return the current on/off state of the switch."""
        return self.entity_description.get_state(self.coordinator.data)

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the switch on."""
        await self.entity_description.set_state(self.coordinator.device, True)

        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the switch off."""
        await self.entity_description.set_state(self.coordinator.device, False)

        await self.coordinator.async_request_refresh()
