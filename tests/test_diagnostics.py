"""Tests for the LaMetric diagnostics module."""

from unittest.mock import MagicMock

from lametric.device_states import DeviceState

from custom_components.lametric_hass_local.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)


def test_redacted_fields_are_defined() -> None:
    """TO_REDACT contains the expected sensitive field names."""
    assert "serial_number" in TO_REDACT
    assert "name" in TO_REDACT
    assert "ssid" in TO_REDACT


def test_diagnostics_redacts_sensitive_fields(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Sensitive fields must be replaced with '**REDACTED**' in diagnostics output."""
    import asyncio

    entry = MagicMock()
    entry.runtime_data = coordinator

    result = asyncio.run(async_get_config_entry_diagnostics(MagicMock(), entry))

    for field in TO_REDACT:
        if field in result:
            assert result[field] == "**REDACTED**", (
                f"Field '{field}' should be redacted in diagnostics output"
            )


def test_diagnostics_returns_dict(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Diagnostics handler always returns a dict."""
    import asyncio

    entry = MagicMock()
    entry.runtime_data = coordinator

    result = asyncio.run(async_get_config_entry_diagnostics(MagicMock(), entry))

    assert isinstance(result, dict)
