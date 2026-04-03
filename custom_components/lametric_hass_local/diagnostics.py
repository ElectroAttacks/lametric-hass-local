"""Diagnostics support for the LaMetric integration."""

import json
from typing import Any, cast

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import LaMetricConfigEntry

TO_REDACT = {
    "device_id",
    "name",
    "serial_number",
    "ssid",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LaMetricConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics data for a config entry."""

    coordinator = entry.runtime_data
    data = cast(dict[str, Any], json.loads(coordinator.data.to_json()))

    return async_redact_data(data, TO_REDACT)
