"""Tests for the LaMetric integration __init__.py setup functions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.lametric_hass_local import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.lametric_hass_local.const import DOMAIN


def _make_hass() -> MagicMock:
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


def _make_config_entry(coordinator: MagicMock) -> MagicMock:
    entry = MagicMock()
    entry.runtime_data = coordinator
    return entry


# ── async_setup ────────────────────────────────────────────────────────────────


def test_async_setup_returns_true() -> None:
    """async_setup always returns True (config-entry only integration)."""
    hass = _make_hass()

    with patch(
        "custom_components.lametric_hass_local.async_setup_services"
    ) as mock_services:
        result = asyncio.run(async_setup(hass, {}))

    assert result is True
    mock_services.assert_called_once_with(hass)


# ── async_setup_entry ──────────────────────────────────────────────────────────


def test_async_setup_entry_returns_true(coordinator: MagicMock) -> None:
    """async_setup_entry returns True on success."""
    hass = _make_hass()
    entry = _make_config_entry(coordinator)
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with patch(
        "custom_components.lametric_hass_local.LaMetricCoordinator",
        return_value=coordinator,
    ):
        result = asyncio.run(async_setup_entry(hass, entry))

    assert result is True


def test_async_setup_entry_stores_coordinator(coordinator: MagicMock) -> None:
    """async_setup_entry assigns the coordinator to config_entry.runtime_data."""
    hass = _make_hass()
    entry = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with patch(
        "custom_components.lametric_hass_local.LaMetricCoordinator",
        return_value=coordinator,
    ):
        asyncio.run(async_setup_entry(hass, entry))

    assert entry.runtime_data is coordinator


def test_async_setup_entry_forwards_platforms(coordinator: MagicMock) -> None:
    """async_setup_entry forwards setup to all platforms."""
    from custom_components.lametric_hass_local.const import PLATFORMS

    hass = _make_hass()
    entry = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with patch(
        "custom_components.lametric_hass_local.LaMetricCoordinator",
        return_value=coordinator,
    ):
        asyncio.run(async_setup_entry(hass, entry))

    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )


# ── async_unload_entry ────────────────────────────────────────────────────────


def test_async_unload_entry_returns_true_on_success(
    coordinator: MagicMock,
) -> None:
    """async_unload_entry returns True when platform unloading succeeds."""
    hass = _make_hass()
    entry = _make_config_entry(coordinator)

    with patch(
        "custom_components.lametric_hass_local.notify_async_reload",
        new_callable=AsyncMock,
    ):
        result = asyncio.run(async_unload_entry(hass, entry))

    assert result is True


def test_async_unload_entry_reloads_notify_on_success(
    coordinator: MagicMock,
) -> None:
    """async_unload_entry calls notify_async_reload after successful unload."""
    hass = _make_hass()
    entry = _make_config_entry(coordinator)

    with patch(
        "custom_components.lametric_hass_local.notify_async_reload",
        new_callable=AsyncMock,
    ) as mock_reload:
        asyncio.run(async_unload_entry(hass, entry))

    mock_reload.assert_awaited_once_with(hass, DOMAIN)


def test_async_unload_entry_skips_reload_on_failure(
    coordinator: MagicMock,
) -> None:
    """async_unload_entry does NOT call notify_async_reload if unloading fails."""
    hass = _make_hass()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    entry = _make_config_entry(coordinator)

    with patch(
        "custom_components.lametric_hass_local.notify_async_reload",
        new_callable=AsyncMock,
    ) as mock_reload:
        result = asyncio.run(async_unload_entry(hass, entry))

    assert result is False
    mock_reload.assert_not_awaited()


# ── application_credentials ───────────────────────────────────────────────────


def test_async_get_authorization_server_returns_correct_urls() -> None:
    """async_get_authorization_server returns the LaMetric OAuth endpoints."""
    from custom_components.lametric_hass_local.application_credentials import (
        async_get_authorization_server,
    )

    server = asyncio.run(async_get_authorization_server(MagicMock()))

    assert "lametric.com" in server.authorize_url
    assert "lametric.com" in server.token_url
