"""Helper utilities for LaMetric entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Concatenate

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from lametric import LaMetricApiError, LaMetricConnectionError

from .const import DOMAIN
from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity


def lametric_api_exception_handler[LaMetricEntityT: LaMetricEntity, **P](
    func: Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, Any]],
) -> Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, None]]:
    """Wrap entity API calls and map LaMetric errors to Home Assistant errors."""

    async def handle(
        self: LaMetricEntityT, /, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Execute the wrapped call and keep coordinator listeners in sync."""
        try:
            await func(self, *args, **kwargs)

            self.coordinator.async_update_listeners()

        except LaMetricConnectionError as error:
            self.coordinator.last_update_success = False
            self.coordinator.async_update_listeners()

            raise HomeAssistantError(
                "Failed to connect to LaMetric device at"
                f" {self.coordinator.device.host}"
            ) from error

        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"API error when communicating with LaMetric device at"
                f" {self.coordinator.device.host}"
            ) from error

    return handle


@callback
def async_get_coordinator_by_device_id(
    hass: HomeAssistant, device_id: str
) -> LaMetricCoordinator:

    device_registry = dr.async_get(hass)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ValueError(f"No device found with ID: {device_id}")

    config_entry: LaMetricConfigEntry
    for config_entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if config_entry.entry_id in device_entry.config_entries:
            return config_entry.runtime_data

    raise ValueError(f"No coordinator found for device ID: {device_id}")
