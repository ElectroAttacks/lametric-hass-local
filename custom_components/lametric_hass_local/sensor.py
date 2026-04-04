"""Sensor platform for LaMetric device diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric import DeviceState

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity


@dataclass(frozen=True, kw_only=True)
class LaMetricSensorEntityDescription(SensorEntityDescription):
    """Description for a LaMetric sensor, including its value accessor."""

    get_value: Callable[[DeviceState], int | None]


SENSORS = [
    LaMetricSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        get_value=lambda state: state.wifi.signal_strength,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric sensor entities for a config entry."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricSensorEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SENSORS
    )


class LaMetricSensorEntity(LaMetricEntity, SensorEntity):
    """Sensor entity that exposes a single value from the LaMetric device state."""

    entity_description: LaMetricSensorEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""

        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def native_value(self) -> int | None:
        """Return the current sensor value from the coordinator data."""
        return self.entity_description.get_value(self.coordinator.data)
