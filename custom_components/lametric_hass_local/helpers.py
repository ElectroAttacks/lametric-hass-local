"""Helper utilities for LaMetric entities."""

from collections.abc import Callable, Coroutine
from typing import Any, Concatenate

from homeassistant.exceptions import HomeAssistantError
from lametric import LaMetricApiError, LaMetricConnectionError

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
