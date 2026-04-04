"""Notify platform for sending messages to a LaMetric device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.notify.const import ATTR_DATA
from homeassistant.components.notify.legacy import BaseNotificationService
from homeassistant.const import CONF_ICON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util.enum import try_parse_enum
from lametric import (
    AlarmSound,
    BuiltinSound,
    IconType,
    LaMetricApiError,
    LaMetricDevice,
    Notification,
    NotificationData,
    NotificationPriority,
    NotificationSound,
    SimpleFrame,
)

from .const import CONF_CYCLES, CONF_ICON_TYPE, CONF_PRIORITY, CONF_SOUND
from .coordinator import LaMetricConfigEntry


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> LaMetricNotificationService | None:
    """Return the notification service for a discovered config entry."""
    if discovery_info is None:
        return None

    entry: LaMetricConfigEntry | None = hass.config_entries.async_get_entry(
        discovery_info["entry_id"]
    )
    if entry is None:
        return None

    return LaMetricNotificationService(entry.runtime_data.device)


class LaMetricNotificationService(BaseNotificationService):
    """Notification service implementation that sends to a LaMetric device."""

    def __init__(self, device: LaMetricDevice) -> None:
        """Initialize the service with a LaMetric device client."""
        self.device = device

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Build and send a notification to the LaMetric device."""

        data: dict[str, Any] = kwargs.get(ATTR_DATA) or {}

        sound = None
        if CONF_SOUND in data:
            sound_id: AlarmSound | NotificationSound | None
            provided_id = data[CONF_SOUND]

            if (sound_id := try_parse_enum(AlarmSound, provided_id)) is None and (
                sound_id := try_parse_enum(NotificationSound, provided_id)
            ) is None:
                raise ServiceValidationError(
                    f"Invalid sound '{provided_id}'. "
                    "Must be a valid AlarmSound or NotificationSound."
                )

            sound = BuiltinSound(category=None, id=sound_id)

        notification = Notification(
            icon_type=IconType(data.get(CONF_ICON_TYPE, "none")),
            priority=NotificationPriority(data.get(CONF_PRIORITY, "info")),
            model=NotificationData(
                frames=[
                    SimpleFrame(
                        icon=data.get(CONF_ICON, "a7956"),
                        text=message,
                    )
                ],
                cycles=int(data.get(CONF_CYCLES, 1)),
                sound=sound,
            ),
        )

        host = getattr(self.device, "host", "unknown")

        try:
            await self.device.send_notification(notification=notification)

        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to send notification to LaMetric device at {host}. "
                "Check device connectivity and credentials."
            ) from error
