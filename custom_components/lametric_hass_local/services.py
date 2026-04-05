"""Service definitions for interacting with LaMetric devices."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID, CONF_ICON
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
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
    ScreensaverConfig,
    ScreensaverConfigParams,
    ScreensaverModes,
    SimpleFrame,
    SpikeChartFrame,
    StreamConfig,
)

from .const import (
    CONF_CYCLES,
    CONF_DATA,
    CONF_ICON_TYPE,
    CONF_MESSAGE,
    CONF_PRIORITY,
    CONF_SCREENSAVER_ENABLED,
    CONF_SCREENSAVER_MODE,
    CONF_SCREENSAVER_MODE_PARAMS,
    CONF_SOUND,
    CONF_STREAM_CONFIG,
    CONF_STREAM_RGB_DATA,
    CONF_STREAM_SESSION_ID,
    DOMAIN,
    SERVICE_SEND_STREAM_DATA,
    SERVICE_SET_SCREENSAVER,
    SERVICE_SHOW_CHART,
    SERVICE_SHOW_MESSAGE,
    SERVICE_START_STREAM,
    SERVICE_STOP_STREAM,
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


def _normalize_stream_config(data: dict) -> dict:  # type: ignore[type-arg]
    """Normalize a raw stream config dict before deserialization.

    YAML/JSON parses the bare word ``none`` as Python ``None``.
    Replace ``None`` values in known string-enum fields with their
    string equivalents so mashumaro can coerce them correctly.
    """
    data = dict(data)
    post = data.get("post_process")
    if isinstance(post, dict):
        post = dict(post)
        if post.get("type") is None:
            post["type"] = "none"
        data["post_process"] = post
    return data


def _coerce_stream_config(value: object) -> StreamConfig:
    """Coerce a plain dict into a StreamConfig dataclass."""
    if isinstance(value, StreamConfig):
        return value
    if isinstance(value, dict):
        return StreamConfig.from_dict(_normalize_stream_config(value))
    raise vol.Invalid(f"Cannot convert {type(value)} to StreamConfig")


def _coerce_rgb_data(value: object) -> bytes:
    """Flatten a list of [R, G, B] triplets into raw RGB888 bytes."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, list):
        try:
            flat = [channel for pixel in value for channel in pixel]
            return bytes(flat)
        except (TypeError, ValueError) as err:
            raise vol.Invalid("rgb_data must be a list of [R, G, B] triplets") from err
    raise vol.Invalid(f"Cannot convert {type(value)} to bytes")


SERVICE_START_STREAM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_STREAM_CONFIG): _coerce_stream_config,
    }
)

SERVICE_STOP_STREAM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)

SERVICE_SEND_STREAM_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_STREAM_SESSION_ID): cv.string,
        vol.Required(CONF_STREAM_RGB_DATA): _coerce_rgb_data,
    }
)

SERVICE_SET_SCREENSAVER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_SCREENSAVER_ENABLED): cv.boolean,
        vol.Optional(
            CONF_SCREENSAVER_MODE, default=ScreensaverModes.WHEN_DARK
        ): vol.Coerce(ScreensaverModes),
        vol.Optional(CONF_SCREENSAVER_MODE_PARAMS): dict,
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

    async def _async_service_start_stream(call: ServiceCall) -> ServiceResponse:
        """Handle the start_stream service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )

        host = getattr(getattr(coordinator, "device", None), "host", "unknown")
        try:
            session_id = await coordinator.device.start_stream(
                stream_config=call.data[CONF_STREAM_CONFIG]
            )

            if session_id is None:
                return {
                    "success": False,
                    "message": f"Failed to start stream on LaMetric device at {host}.",
                }

            return {
                "success": True,
                "session_id": session_id,
            }

        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to start stream on LaMetric device at {host}."
            ) from error

    async def _async_service_stop_stream(call: ServiceCall) -> None:
        """Handle the stop_stream service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )
        host = getattr(getattr(coordinator, "device", None), "host", "unknown")

        try:
            await coordinator.device.stop_stream()

        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to stop stream on LaMetric device at {host}."
            ) from error

    async def _async_service_send_stream_data(call: ServiceCall) -> None:
        """Handle the send_stream_data service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )

        host = getattr(getattr(coordinator, "device", None), "host", "unknown")

        try:
            await coordinator.device.send_stream_data(
                session_id=call.data[CONF_STREAM_SESSION_ID],
                rgb888_data=call.data[CONF_STREAM_RGB_DATA],
            )

        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to send stream data to LaMetric device at {host}."
            ) from error

    async def _async_service_set_screensaver(call: ServiceCall) -> None:
        """Handle the set_screensaver service call."""
        coordinator = async_get_coordinator_by_device_id(
            hass, call.data[CONF_DEVICE_ID]
        )

        raw_params = call.data.get(CONF_SCREENSAVER_MODE_PARAMS)
        mode_params = (
            ScreensaverConfigParams.from_dict(raw_params)
            if isinstance(raw_params, dict)
            else ScreensaverConfigParams(enabled=False)
        )

        config = ScreensaverConfig(
            enabled=call.data[CONF_SCREENSAVER_ENABLED],
            mode=call.data[CONF_SCREENSAVER_MODE],
            mode_params=mode_params,
        )

        host = getattr(getattr(coordinator, "device", None), "host", "unknown")

        try:
            await coordinator.device.set_display(screensaver_config=config)
        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to configure screensaver on LaMetric device at {host}."
            ) from error

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

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_STREAM,
        _async_service_start_stream,
        schema=SERVICE_START_STREAM_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_STREAM,
        _async_service_stop_stream,
        schema=SERVICE_STOP_STREAM_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_STREAM_DATA,
        _async_service_send_stream_data,
        schema=SERVICE_SEND_STREAM_DATA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCREENSAVER,
        _async_service_set_screensaver,
        schema=SERVICE_SET_SCREENSAVER_SCHEMA,
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
