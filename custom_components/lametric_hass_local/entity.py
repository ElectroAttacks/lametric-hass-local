"""Entity base classes for the LaMetric integration."""

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import LaMetricCoordinator


class LaMetricEntity(CoordinatorEntity[LaMetricCoordinator]):
    """Base entity backed by the LaMetric coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LaMetricCoordinator) -> None:
        """Build shared device metadata for all LaMetric entities."""

        super().__init__(coordinator)

        LOGGER.debug(
            "Building device info for %s (model=%s, os_version=%s, type=%s)",
            coordinator.data.serial_number,
            coordinator.data.model,
            coordinator.data.os_version,
            type(coordinator.data.os_version).__name__,
        )

        connections = {(CONNECTION_NETWORK_MAC, format_mac(coordinator.data.wifi.mac))}

        if coordinator.data.bluetooth.mac is not None:
            # Add Bluetooth connection when the device reports a Bluetooth MAC
            connections.add(
                (CONNECTION_BLUETOOTH, format_mac(coordinator.data.bluetooth.mac))
            )

        self._attr_device_info = DeviceInfo(
            connections=connections,
            identifiers={(DOMAIN, coordinator.data.serial_number)},
            manufacturer="LaMetric Inc.",
            model_id=coordinator.data.model,
            name=coordinator.data.name,
            sw_version=str(coordinator.data.os_version),
            serial_number=coordinator.data.serial_number,
            configuration_url=f"https://{coordinator.data.wifi.ipv4}",
        )
