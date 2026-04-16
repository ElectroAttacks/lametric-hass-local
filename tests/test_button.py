"""Tests for the LaMetric button platform."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from custom_components.lametric_hass_local.button import (
    BUTTONS,
    LaMetricButtonEntity,
)


def _description(key: str) -> Any:
    return next(b for b in BUTTONS if b.key == key)


def test_next_app_press_calls_activate_next_app(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Pressing the next_app button calls activate_next_app on the device."""
    coordinator.device.activate_next_app = AsyncMock()
    entity = LaMetricButtonEntity(coordinator, _description("next_app"))
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    coordinator.device.activate_next_app.assert_awaited_once()


def test_previous_app_press_calls_activate_previous_app(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Pressing the previous_app button calls activate_previous_app on the device."""
    coordinator.device.activate_previous_app = AsyncMock()
    entity = LaMetricButtonEntity(coordinator, _description("previous_app"))
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    coordinator.device.activate_previous_app.assert_awaited_once()


def test_dismiss_current_notification_press(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Pressing dismiss_current_notification calls the correct device method."""
    coordinator.device.dismiss_current_notification = AsyncMock()
    entity = LaMetricButtonEntity(
        coordinator, _description("dismiss_current_notification")
    )
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    coordinator.device.dismiss_current_notification.assert_awaited_once()


def test_dismiss_all_notifications_press(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Pressing dismiss_all_notifications calls the correct device method."""
    coordinator.device.dismiss_all_notifications = AsyncMock()
    entity = LaMetricButtonEntity(
        coordinator, _description("dismiss_all_notifications")
    )
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    coordinator.device.dismiss_all_notifications.assert_awaited_once()


def test_press_does_not_fall_back_to_base_press(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Button presses should not call the base ButtonEntity press implementation."""
    coordinator.device.activate_next_app = AsyncMock()
    entity = LaMetricButtonEntity(coordinator, _description("next_app"))
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    mock_hass.async_add_executor_job.assert_not_awaited()


def test_press_requests_refresh(coordinator: MagicMock, mock_hass: MagicMock) -> None:
    """Successful button presses should refresh coordinator data afterwards."""
    coordinator.device.activate_next_app = AsyncMock()
    entity = LaMetricButtonEntity(coordinator, _description("next_app"))
    entity.hass = mock_hass

    asyncio.run(entity.async_press())

    coordinator.async_request_refresh.assert_awaited_once()


def test_all_button_keys_are_unique() -> None:
    """Every button description has a distinct key."""
    keys = [b.key for b in BUTTONS]
    assert len(keys) == len(set(keys))


def test_setup_entry_adds_all_buttons(coordinator: MagicMock) -> None:
    """async_setup_entry adds one entity per BUTTONS description."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.button import BUTTONS, async_setup_entry

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == len(BUTTONS)
