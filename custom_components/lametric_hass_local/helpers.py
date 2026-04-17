"""Helper utilities for LaMetric entities."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, Concatenate, overload

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from lametric import LaMetricApiError, LaMetricConnectionError

from .const import DOMAIN
from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity


def _format_error_message(message: str | None, *, host: str, default: str) -> str:
    """Render a custom message template or fall back to the default text."""
    return (message or default).format(host=host)


async def async_handle_lametric_call[ReturnT](
    coro: Coroutine[Any, Any, ReturnT],
    *,
    host: str,
    connection_error_message: str | None = None,
    api_error_message: str | None = None,
) -> ReturnT:
    """Execute a LaMetric coroutine and map device errors to HA errors."""
    try:
        result = await coro
    except LaMetricConnectionError as error:
        raise HomeAssistantError(
            _format_error_message(
                connection_error_message,
                host=host,
                default=f"Failed to connect to LaMetric device at {host}",
            )
        ) from error
    except LaMetricApiError as error:
        raise HomeAssistantError(
            _format_error_message(
                api_error_message,
                host=host,
                default=f"API error when communicating with LaMetric device at {host}",
            )
        ) from error

    return result


@overload
def lametric_api_exception_handler[LaMetricEntityT: LaMetricEntity, **P, ReturnT](
    func: Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]],
) -> Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]]: ...


@overload
def lametric_api_exception_handler[LaMetricEntityT: LaMetricEntity, **P, ReturnT](
    func: None = None,
    *,
    connection_error_message: str | None = None,
    api_error_message: str | None = None,
) -> Callable[
    [Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]]],
    Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]],
]: ...


def lametric_api_exception_handler[LaMetricEntityT: LaMetricEntity, **P, ReturnT](
    func: (
        Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]] | None
    ) = None,
    *,
    connection_error_message: str | None = None,
    api_error_message: str | None = None,
) -> (
    Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]]
    | Callable[
        [Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]]],
        Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]],
    ]
):
    """Wrap entity API calls and map LaMetric errors to Home Assistant errors."""

    def decorator(
        wrapped: Callable[
            Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]
        ],
    ) -> Callable[Concatenate[LaMetricEntityT, P], Coroutine[Any, Any, ReturnT]]:
        @wraps(wrapped)
        async def handle(
            self: LaMetricEntityT, /, *args: P.args, **kwargs: P.kwargs
        ) -> ReturnT:
            """Execute the wrapped call and keep coordinator listeners in sync."""
            try:
                result = await async_handle_lametric_call(
                    wrapped(self, *args, **kwargs),
                    host=self.coordinator.device.host,
                    connection_error_message=connection_error_message,
                    api_error_message=api_error_message,
                )
            except HomeAssistantError as error:
                if isinstance(error.__cause__, LaMetricConnectionError):
                    self.coordinator.last_update_success = False
                    self.coordinator.async_update_listeners()

                raise

            self.coordinator.async_update_listeners()
            return result

        return handle

    if func is None:
        return decorator

    return decorator(func)


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
