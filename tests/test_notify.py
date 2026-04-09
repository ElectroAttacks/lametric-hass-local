"""Tests for the LaMetric notify platform."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from lametric import LaMetricApiError

from custom_components.lametric_hass_local.notify import (
    LaMetricNotificationService,
    async_get_service,
)

# ── async_get_service ─────────────────────────────────────────────────────────


def test_get_service_returns_none_without_discovery_info() -> None:
    """Returns None when discovery_info is None."""
    result = asyncio.run(async_get_service(MagicMock(), {}, discovery_info=None))
    assert result is None


def test_get_service_returns_none_when_entry_not_found() -> None:
    """Returns None when the config entry cannot be found in hass."""
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = None

    result = asyncio.run(
        async_get_service(hass, {}, discovery_info={"entry_id": "missing"})
    )
    assert result is None


def test_get_service_returns_service_for_valid_entry() -> None:
    """Returns LaMetricNotificationService when entry is valid."""
    device = MagicMock()
    entry = MagicMock()
    entry.runtime_data.device = device

    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = entry

    result = asyncio.run(
        async_get_service(hass, {}, discovery_info={"entry_id": "abc"})
    )
    assert isinstance(result, LaMetricNotificationService)
    assert result.device is device


# ── LaMetricNotificationService.async_send_message ───────────────────────────


def _make_service() -> tuple[LaMetricNotificationService, AsyncMock]:
    """Return a service instance and its send_notification mock."""
    mock_send = AsyncMock()
    device = MagicMock()
    device.host = "10.0.0.1"
    device.send_notification = mock_send
    return LaMetricNotificationService(device), mock_send


def test_send_message_calls_device_send_notification() -> None:
    """A plain message triggers device.send_notification."""
    svc, mock_send = _make_service()
    asyncio.run(svc.async_send_message("Hello"))
    mock_send.assert_awaited_once()


def test_send_message_with_notification_sound() -> None:
    """A valid NotificationSound is accepted and passed along."""
    from homeassistant.components.notify.const import ATTR_DATA

    from custom_components.lametric_hass_local.const import CONF_SOUND

    svc, mock_send = _make_service()
    asyncio.run(svc.async_send_message("hi", **{ATTR_DATA: {CONF_SOUND: "bicycle"}}))
    mock_send.assert_awaited_once()


def test_send_message_with_alarm_sound() -> None:
    """A valid AlarmSound value is accepted."""
    from homeassistant.components.notify.const import ATTR_DATA

    from custom_components.lametric_hass_local.const import CONF_SOUND

    svc, mock_send = _make_service()
    asyncio.run(svc.async_send_message("alert", **{ATTR_DATA: {CONF_SOUND: "alarm1"}}))
    mock_send.assert_awaited_once()


def test_send_message_invalid_sound_raises_service_validation_error() -> None:
    """An unknown sound ID raises ServiceValidationError before calling the device."""
    from homeassistant.components.notify.const import ATTR_DATA

    from custom_components.lametric_hass_local.const import CONF_SOUND

    svc, mock_send = _make_service()
    with pytest.raises(ServiceValidationError, match="bad-sound"):
        asyncio.run(
            svc.async_send_message("hi", **{ATTR_DATA: {CONF_SOUND: "bad-sound"}})
        )
    mock_send.assert_not_awaited()


def test_send_message_api_error_raises_home_assistant_error() -> None:
    """LaMetricApiError from the device is re-raised as HomeAssistantError."""
    mock_send = AsyncMock(side_effect=LaMetricApiError("boom"))
    device = MagicMock()
    device.host = "10.0.0.1"
    device.send_notification = mock_send
    svc = LaMetricNotificationService(device)
    with pytest.raises(HomeAssistantError, match="10.0.0.1"):
        asyncio.run(svc.async_send_message("fail"))


def test_send_message_no_data_uses_defaults() -> None:
    """Message with no extra data still succeeds (all defaults applied)."""
    svc, mock_send = _make_service()
    asyncio.run(svc.async_send_message("default"))
    mock_send.assert_awaited_once()
