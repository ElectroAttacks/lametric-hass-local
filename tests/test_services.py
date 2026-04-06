"""Tests for services.py – pure helpers and async_send_notification."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from lametric import IconType, LaMetricApiError, NotificationPriority

from custom_components.lametric_hass_local.const import (
    CONF_CYCLES,
    CONF_ICON_TYPE,
    CONF_PRIORITY,
)
from custom_components.lametric_hass_local.light import (
    _coerce_rgb_data,
    _coerce_stream_config,
)
from custom_components.lametric_hass_local.services import async_send_notification

# ── _coerce_rgb_data ─────────────────────────────────────────────────────────


def test_coerce_rgb_data_flattens_triplets() -> None:
    """RGB triplets are flattened into a bytes sequence."""
    result = _coerce_rgb_data([[255, 0, 0], [0, 255, 0], [0, 0, 255]])
    assert result == bytes([255, 0, 0, 0, 255, 0, 0, 0, 255])


def test_coerce_rgb_data_passthrough_bytes() -> None:
    """Bytes input is returned unchanged."""
    raw = bytes([1, 2, 3])
    assert _coerce_rgb_data(raw) is raw


def test_coerce_rgb_data_rejects_invalid_type() -> None:
    """Non-bytes, non-list input raises vol.Invalid."""
    with pytest.raises(vol.Invalid):
        _coerce_rgb_data("not-rgb")


def test_coerce_rgb_data_rejects_bad_triplet_structure() -> None:
    """A list that cannot be flattened raises vol.Invalid."""
    with pytest.raises(vol.Invalid):
        _coerce_rgb_data([1, 2, 3])  # flat ints, not triplets


# ── _coerce_stream_config ────────────────────────────────────────────────────


def test_coerce_stream_config_passthrough_stream_config() -> None:
    """An already-built StreamConfig instance is returned unchanged."""
    from lametric import StreamConfig

    sc = MagicMock(spec=StreamConfig)
    assert _coerce_stream_config(sc) is sc


def test_coerce_stream_config_rejects_unsupported_type() -> None:
    """Non-dict, non-StreamConfig input raises vol.Invalid."""
    with pytest.raises(vol.Invalid):
        _coerce_stream_config(42)


# ── async_send_notification ───────────────────────────────────────────────────


def _make_service_call(**extra_data: object) -> MagicMock:
    """Return a ServiceCall-like mock with sensible defaults."""
    call = MagicMock()
    call.data = {
        CONF_CYCLES: 1,
        CONF_ICON_TYPE: IconType.NONE,
        CONF_PRIORITY: NotificationPriority.INFO,
        **extra_data,
    }
    return call


def test_send_notification_calls_device(coordinator: MagicMock) -> None:
    """async_send_notification calls device.send_notification on success."""
    from lametric import SimpleFrame

    coordinator.device.send_notification = AsyncMock()
    call = _make_service_call()

    asyncio.run(async_send_notification(coordinator, call, [SimpleFrame(text="hi")]))

    coordinator.device.send_notification.assert_awaited_once()


def test_send_notification_raises_on_api_error(coordinator: MagicMock) -> None:
    """LaMetricApiError from the device is re-raised as HomeAssistantError."""
    from lametric import SimpleFrame

    coordinator.device.send_notification = AsyncMock(
        side_effect=LaMetricApiError("boom")
    )
    call = _make_service_call()

    with pytest.raises(HomeAssistantError):
        asyncio.run(
            async_send_notification(coordinator, call, [SimpleFrame(text="hi")])
        )


def test_send_notification_error_contains_host(coordinator: MagicMock) -> None:
    """HomeAssistantError message includes the device host."""
    from lametric import SimpleFrame

    coordinator.device.host = "10.0.0.5"
    coordinator.device.send_notification = AsyncMock(
        side_effect=LaMetricApiError("oops")
    )
    call = _make_service_call()

    with pytest.raises(HomeAssistantError, match="10.0.0.5"):
        asyncio.run(
            async_send_notification(coordinator, call, [SimpleFrame(text="hi")])
        )


def test_send_notification_invalid_sound_raises_service_validation_error(
    coordinator: MagicMock,
) -> None:
    """An invalid sound name raises ServiceValidationError before the API is called."""
    from lametric import SimpleFrame

    from custom_components.lametric_hass_local.const import CONF_SOUND

    coordinator.device.send_notification = AsyncMock()
    call = _make_service_call(**{CONF_SOUND: "totally-invalid-sound"})

    with pytest.raises(ServiceValidationError, match="totally-invalid-sound"):
        asyncio.run(
            async_send_notification(coordinator, call, [SimpleFrame(text="hi")])
        )

    coordinator.device.send_notification.assert_not_awaited()


def test_send_notification_with_valid_sound_calls_device(
    coordinator: MagicMock,
) -> None:
    """A valid NotificationSound value is accepted and the notification is sent."""
    from lametric import SimpleFrame

    from custom_components.lametric_hass_local.const import CONF_SOUND

    coordinator.device.send_notification = AsyncMock()
    call = _make_service_call(**{CONF_SOUND: "bicycle"})

    asyncio.run(async_send_notification(coordinator, call, [SimpleFrame(text="hi")]))

    coordinator.device.send_notification.assert_awaited_once()


# ── service handler closures ─────────────────────────────────────────────────


def _register_services(hass: MagicMock) -> dict:
    """Call async_setup_services and return {service_name: handler_fn}."""
    from custom_components.lametric_hass_local.services import async_setup_services

    captured: dict = {}

    def fake_register(domain, name, handler, **kwargs):
        captured[name] = handler

    hass.services.async_register.side_effect = fake_register
    async_setup_services(hass)
    return captured


def _fake_hass_with_coordinator(coordinator: MagicMock) -> MagicMock:
    hass = MagicMock()
    hass.services.async_register.side_effect = lambda *a, **k: None
    return hass


def test_show_message_handler_sends_notification(coordinator: MagicMock) -> None:
    """show_message service handler sends a notification with the right text."""
    from unittest.mock import patch

    from custom_components.lametric_hass_local.const import (
        CONF_MESSAGE,
        SERVICE_SHOW_MESSAGE,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.send_notification = AsyncMock()

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_CYCLES: 1,
        CONF_ICON_TYPE: IconType.NONE,
        CONF_PRIORITY: NotificationPriority.INFO,
        CONF_MESSAGE: "Hello LaMetric",
    }

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        asyncio.run(handlers[SERVICE_SHOW_MESSAGE](call))

    coordinator.device.send_notification.assert_awaited_once()


def test_show_chart_handler_sends_notification(coordinator: MagicMock) -> None:
    """show_chart service handler sends a notification with chart frames."""
    from unittest.mock import patch

    from custom_components.lametric_hass_local.const import (
        CONF_DATA,
        SERVICE_SHOW_CHART,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.send_notification = AsyncMock()

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_CYCLES: 1,
        CONF_ICON_TYPE: IconType.NONE,
        CONF_PRIORITY: NotificationPriority.INFO,
        CONF_DATA: [10, 20, 30, 40, 50],
    }

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        asyncio.run(handlers[SERVICE_SHOW_CHART](call))

    coordinator.device.send_notification.assert_awaited_once()


def test_coerce_stream_config_from_dict_path() -> None:
    """_coerce_stream_config calls StreamConfig.from_dict when given a dict."""
    from unittest.mock import MagicMock, patch

    with patch(
        "custom_components.lametric_hass_local.light.StreamConfig.from_dict",
        return_value=MagicMock(),
    ) as mock_from_dict:
        _coerce_stream_config({"width": 8, "height": 8})

    mock_from_dict.assert_called_once()
