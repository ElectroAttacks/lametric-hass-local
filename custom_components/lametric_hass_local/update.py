"""Update platform for LaMetric firmware update tracking."""

from __future__ import annotations

from awesomeversion import AwesomeVersion
from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the LaMetric update entity for a config entry.

    Only registered for devices running OS 2.3.0 or later, which is
    the first version that exposes update information via the local API.
    """

    coordinator = config_entry.runtime_data

    if coordinator.data.os_version >= AwesomeVersion("2.3.0"):
        async_add_entities([LaMetricUpdate(coordinator)])


class LaMetricUpdate(LaMetricEntity, UpdateEntity):
    """Update entity that tracks LaMetric firmware versions."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(self, coordinator: LaMetricCoordinator) -> None:
        """Initialize the LaMetric update entity."""

        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.data.serial_number}-update"

    @property
    def installed_version(self) -> str:
        """Return the currently installed OS version."""
        return str(self.coordinator.data.os_version)

    @property
    def latest_version(self) -> str | None:
        """Return the latest available OS version, or installed if up to date."""
        if not self.coordinator.data.update:
            return str(self.coordinator.data.os_version)

        return str(self.coordinator.data.update.version)
