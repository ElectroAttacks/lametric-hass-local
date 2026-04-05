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
from custom_components.lametric_hass_local.services import (
    _coerce_rgb_data,
    _coerce_stream_config,
    _normalize_stream_config,
    async_send_notification,
)

# ── _normalize_stream_config ─────────────────────────────────────────────────


def test_normalize_stream_config_replaces_none_post_process_type() -> None:
    """None post_process.type is replaced with the string 'none'."""
    data = {"post_process": {"type": None, "other": "value"}}
    result = _normalize_stream_config(data)
    assert result["post_process"]["type"] == "none"


def test_normalize_stream_config_leaves_set_type_unchanged() -> None:
    """An already-set post_process.type is left as-is."""
    data = {"post_process": {"type": "gamma"}}
    result = _normalize_stream_config(data)
    assert result["post_process"]["type"] == "gamma"


def test_normalize_stream_config_no_post_process_key_unchanged() -> None:
    """Dicts without post_process are returned unchanged."""
    data = {"width": 8, "height": 8}
    result = _normalize_stream_config(data)
    assert result == data


def test_normalize_stream_config_does_not_mutate_input() -> None:
    """The original dict is not mutated."""
    inner = {"type": None}
    data = {"post_process": inner}
    _normalize_stream_config(data)
    assert inner["type"] is None  # original untouched


def test_normalize_stream_config_non_dict_post_process_unchanged() -> None:
    """A non-dict post_process value is left untouched."""
    data = {"post_process": "raw"}
    result = _normalize_stream_config(data)
    assert result["post_process"] == "raw"


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


def test_stop_stream_handler_calls_stop(coordinator: MagicMock) -> None:
    """stop_stream service handler calls device.stop_stream."""
    from unittest.mock import patch

    from custom_components.lametric_hass_local.const import SERVICE_STOP_STREAM

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.stop_stream = AsyncMock()

    call = MagicMock()
    call.data = {"device_id": "device-1"}

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        asyncio.run(handlers[SERVICE_STOP_STREAM](call))

    coordinator.device.stop_stream.assert_awaited_once()


def test_stop_stream_handler_raises_on_api_error(coordinator: MagicMock) -> None:
    """stop_stream surfaces LaMetricApiError as HomeAssistantError."""
    from unittest.mock import patch

    from lametric import LaMetricApiError

    from custom_components.lametric_hass_local.const import SERVICE_STOP_STREAM

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.stop_stream = AsyncMock(side_effect=LaMetricApiError("fail"))

    call = MagicMock()
    call.data = {"device_id": "device-1"}

    with (
        patch(
            "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
            return_value=coordinator,
        ),
        pytest.raises(HomeAssistantError),
    ):
        asyncio.run(handlers[SERVICE_STOP_STREAM](call))


def test_send_stream_data_handler_calls_device(coordinator: MagicMock) -> None:
    """send_stream_data service handler calls device.send_stream_data."""
    from unittest.mock import patch

    from custom_components.lametric_hass_local.const import (
        CONF_STREAM_RGB_DATA,
        CONF_STREAM_SESSION_ID,
        SERVICE_SEND_STREAM_DATA,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.send_stream_data = AsyncMock()

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_STREAM_SESSION_ID: "sess-123",
        CONF_STREAM_RGB_DATA: bytes([255, 0, 0]),
    }

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        asyncio.run(handlers[SERVICE_SEND_STREAM_DATA](call))

    coordinator.device.send_stream_data.assert_awaited_once_with(
        session_id="sess-123",
        rgb888_data=bytes([255, 0, 0]),
    )


def test_set_screensaver_handler_calls_set_display(coordinator: MagicMock) -> None:
    """set_screensaver service handler calls device.set_display."""
    from unittest.mock import patch

    from lametric import ScreensaverModes

    from custom_components.lametric_hass_local.const import (
        CONF_SCREENSAVER_ENABLED,
        CONF_SCREENSAVER_MODE,
        SERVICE_SET_SCREENSAVER,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.set_display = AsyncMock()

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_SCREENSAVER_ENABLED: True,
        CONF_SCREENSAVER_MODE: ScreensaverModes.WHEN_DARK,
        # CONF_SCREENSAVER_MODE_PARAMS intentionally absent → handler defaults to None
    }

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        asyncio.run(handlers[SERVICE_SET_SCREENSAVER](call))

    coordinator.device.set_display.assert_awaited_once()


def test_start_stream_handler_returns_session_id(coordinator: MagicMock) -> None:
    """start_stream returns success dict with session_id on success."""
    from unittest.mock import patch

    from lametric import StreamConfig

    from custom_components.lametric_hass_local.const import (
        CONF_STREAM_CONFIG,
        SERVICE_START_STREAM,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.start_stream = AsyncMock(return_value="stream-abc")

    stream_cfg = MagicMock(spec=StreamConfig)
    call = MagicMock()
    call.data = {"device_id": "device-1", CONF_STREAM_CONFIG: stream_cfg}

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        result = asyncio.run(handlers[SERVICE_START_STREAM](call))

    assert result == {"success": True, "session_id": "stream-abc"}


def test_start_stream_handler_returns_failure_when_session_id_none(
    coordinator: MagicMock,
) -> None:
    """start_stream returns failure dict when device returns no session_id."""
    from unittest.mock import patch

    from lametric import StreamConfig

    from custom_components.lametric_hass_local.const import (
        CONF_STREAM_CONFIG,
        SERVICE_START_STREAM,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.start_stream = AsyncMock(return_value=None)

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_STREAM_CONFIG: MagicMock(spec=StreamConfig),
    }

    with patch(
        "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
        return_value=coordinator,
    ):
        result = asyncio.run(handlers[SERVICE_START_STREAM](call))

    assert result["success"] is False


def test_start_stream_handler_raises_on_api_error(coordinator: MagicMock) -> None:
    """start_stream raises HomeAssistantError on LaMetricApiError."""
    from unittest.mock import patch

    from lametric import LaMetricApiError, StreamConfig

    from custom_components.lametric_hass_local.const import (
        CONF_STREAM_CONFIG,
        SERVICE_START_STREAM,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.start_stream = AsyncMock(side_effect=LaMetricApiError("fail"))

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_STREAM_CONFIG: MagicMock(spec=StreamConfig),
    }

    with (
        patch(
            "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
            return_value=coordinator,
        ),
        pytest.raises(HomeAssistantError),
    ):
        asyncio.run(handlers[SERVICE_START_STREAM](call))


def test_send_stream_data_handler_raises_on_api_error(coordinator: MagicMock) -> None:
    """send_stream_data raises HomeAssistantError on LaMetricApiError."""
    from unittest.mock import patch

    from lametric import LaMetricApiError

    from custom_components.lametric_hass_local.const import (
        CONF_STREAM_RGB_DATA,
        CONF_STREAM_SESSION_ID,
        SERVICE_SEND_STREAM_DATA,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.send_stream_data = AsyncMock(side_effect=LaMetricApiError("bad"))

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_STREAM_SESSION_ID: "s1",
        CONF_STREAM_RGB_DATA: bytes([0, 0, 0]),
    }

    with (
        patch(
            "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
            return_value=coordinator,
        ),
        pytest.raises(HomeAssistantError),
    ):
        asyncio.run(handlers[SERVICE_SEND_STREAM_DATA](call))


def test_set_screensaver_handler_raises_on_api_error(coordinator: MagicMock) -> None:
    """set_screensaver raises HomeAssistantError on LaMetricApiError."""
    from unittest.mock import patch

    from lametric import LaMetricApiError, ScreensaverModes

    from custom_components.lametric_hass_local.const import (
        CONF_SCREENSAVER_ENABLED,
        CONF_SCREENSAVER_MODE,
        SERVICE_SET_SCREENSAVER,
    )

    hass = MagicMock()
    handlers = _register_services(hass)
    coordinator.device.set_display = AsyncMock(side_effect=LaMetricApiError("oops"))

    call = MagicMock()
    call.data = {
        "device_id": "device-1",
        CONF_SCREENSAVER_ENABLED: True,
        CONF_SCREENSAVER_MODE: ScreensaverModes.WHEN_DARK,
    }

    with (
        patch(
            "custom_components.lametric_hass_local.services.async_get_coordinator_by_device_id",
            return_value=coordinator,
        ),
        pytest.raises(HomeAssistantError),
    ):
        asyncio.run(handlers[SERVICE_SET_SCREENSAVER](call))


def test_coerce_stream_config_from_dict_path() -> None:
    """_coerce_stream_config calls StreamConfig.from_dict when given a dict."""
    from unittest.mock import MagicMock, patch

    with patch(
        "custom_components.lametric_hass_local.services.StreamConfig.from_dict",
        return_value=MagicMock(),
    ) as mock_from_dict:
        _coerce_stream_config({"width": 8, "height": 8})

    mock_from_dict.assert_called_once()
