"""Service definitions for interacting with LaMetric devices."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID, CONF_ICON
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util.enum import try_parse_enum
from lametric import (
    AlarmSound,
    BuiltinSound,
    GoalFrame,
    IconType,
    LaMetricApiError,
    Notification,
    NotificationData,
    NotificationPriority,
    NotificationSound,
    SimpleFrame,
    SpikeChartFrame,
)

from .const import (
    CONF_CYCLES,
    CONF_DATA,
    CONF_ICON_TYPE,
    CONF_MESSAGE,
    CONF_PRIORITY,
    CONF_SOUND,
    DOMAIN,
    SERVICE_SHOW_CHART,
    SERVICE_SHOW_MESSAGE,
)
from .coordinator import LaMetricCoordinator
from .helpers import async_get_coordinator_by_device_id

SERVICE_BASE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_CYCLES, default=1): cv.positive_int,
        vol.Optional(CONF_ICON_TYPE, default=IconType.NONE): vol.Coerce(IconType),
        vol.Optional(CONF_PRIORITY, default=NotificationPriority.INFO): vol.Coerce(
            NotificationPriority
        ),
        vol.Optional(CONF_SOUND): vol.Any(
            vol.Coerce(AlarmSound), vol.Coerce(NotificationSound)
        ),
    }
)

SERVICE_SHOW_MESSAGE_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_MESSAGE): cv.string,
        vol.Optional(CONF_ICON): cv.string,
    }
)

SERVICE_SHOW_CHART_SCHEMA = SERVICE_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_DATA): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    }
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register all LaMetric services with Home Assistant."""

    async def _async_service_chart(call: ServiceCall) -> None:
        """Handle the show_chart service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )

        await async_send_notification(
            coordinator, call, [SpikeChartFrame(chart_data=call.data[CONF_DATA])]
        )

    async def _async_service_message(call: ServiceCall) -> None:
        """Handle the show_message service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )

        await async_send_notification(
            coordinator,
            call,
            [
                SimpleFrame(
                    icon=call.data.get(CONF_ICON),
                    text=call.data[CONF_MESSAGE],
                )
            ],
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SHOW_CHART,
        _async_service_chart,
        schema=SERVICE_SHOW_CHART_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SHOW_MESSAGE,
        _async_service_message,
        schema=SERVICE_SHOW_MESSAGE_SCHEMA,
        description_placeholders={"icons_url": "https://developer.lametric.com/icons"},
    )


async def async_send_notification(
    coordinator: LaMetricCoordinator,
    call: ServiceCall,
    frames: list[SpikeChartFrame | GoalFrame | SimpleFrame],
) -> None:
    """Build and send a notification to a LaMetric device."""

    sound = None

    if CONF_SOUND in call.data:
        sound_id: AlarmSound | NotificationSound | None

        if (sound_id := try_parse_enum(AlarmSound, call.data[CONF_SOUND])) is None and (
            sound_id := try_parse_enum(NotificationSound, call.data[CONF_SOUND])
        ) is None:
            raise ServiceValidationError(
                f"Invalid sound '{call.data[CONF_SOUND]}'. "
                "Must be a valid AlarmSound or NotificationSound."
            )

        sound = BuiltinSound(category=None, id=sound_id)

    notification = Notification(
        icon_type=IconType(call.data[CONF_ICON_TYPE]),
        priority=NotificationPriority(
            call.data.get(CONF_PRIORITY, NotificationPriority.INFO)
        ),
        model=NotificationData(
            frames=frames,
            cycles=call.data[CONF_CYCLES],
            sound=sound,
        ),
    )

    host = getattr(getattr(coordinator, "device", None), "host", "unknown")
    try:
        await coordinator.device.send_notification(notification=notification)

    except LaMetricApiError as error:
        raise HomeAssistantError(
            f"Failed to send notification to LaMetric device at {host}."
        ) from error
