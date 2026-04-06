"""Select platform for LaMetric device configuration options."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from lametric import (
    BrightnessMode,
    DeviceModels,
    DeviceState,
    LaMetricApiError,
    LaMetricDevice,
    ScreensaverConfig,
    ScreensaverConfigParams,
    ScreensaverModes,
)

from .const import (
    CONF_SCREENSAVER_ENABLED,
    CONF_SCREENSAVER_MODE,
    CONF_SCREENSAVER_MODE_PARAMS,
    SERVICE_SET_SCREENSAVER,
)
from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler


@dataclass(frozen=True, kw_only=True)
class LaMetricSelectEntityDescription(SelectEntityDescription):
    """Description for a LaMetric select, including get/set accessors."""

    available: Callable[[DeviceState], bool]
    get_current: Callable[[DeviceState], str]
    set_current: Callable[[LaMetricDevice, str], Awaitable[Any]]


SELECTS = [
    LaMetricSelectEntityDescription(
        icon="mdi:brightness-auto",
        key="brightness_mode",
        translation_key="brightness_mode",
        entity_category=EntityCategory.CONFIG,
        options=[mode.value for mode in BrightnessMode],
        available=lambda state: state.model != DeviceModels.SKY,
        get_current=lambda state: state.display.brightness_mode.value,
        set_current=lambda device, option: device.set_display(
            brightness_mode=BrightnessMode(option)
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LaMetric select entities for a config entry."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        LaMetricSelectEntity(
            coordinator=coordinator,
            description=description,
        )
        for description in SELECTS
        if description.available(coordinator.data)
    )

    platform = async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SET_SCREENSAVER,
        {
            vol.Required(CONF_SCREENSAVER_ENABLED): bool,
            vol.Optional(
                CONF_SCREENSAVER_MODE, default=ScreensaverModes.WHEN_DARK
            ): vol.Coerce(ScreensaverModes),
            vol.Optional(CONF_SCREENSAVER_MODE_PARAMS): dict,
        },
        "_async_set_screensaver",
    )


class LaMetricSelectEntity(LaMetricEntity, SelectEntity):
    """Select entity for choosing a configuration option on the LaMetric device."""

    entity_description: LaMetricSelectEntityDescription

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        description: LaMetricSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.serial_number}-{description.key}"

    @property
    def available(self) -> bool:
        """Return True when the coordinator is available and feature is supported."""
        return super().available and self.entity_description.available(
            self.coordinator.data
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently active option."""
        return self.entity_description.get_current(self.coordinator.data)

    @lametric_api_exception_handler
    async def async_select_option(self, option: str) -> None:
        """Apply the selected option on the device."""
        await self.entity_description.set_current(self.coordinator.device, option)

        await self.coordinator.async_request_refresh()

    async def _async_set_screensaver(
        self,
        enabled: bool,
        mode: ScreensaverModes = ScreensaverModes.WHEN_DARK,
        mode_params: dict[str, Any] | None = None,
    ) -> None:
        """Configure the screensaver on the device."""
        params = (
            ScreensaverConfigParams.from_dict(mode_params)
            if isinstance(mode_params, dict)
            else ScreensaverConfigParams(enabled=False)
        )

        config = ScreensaverConfig(
            enabled=enabled,
            mode=mode,
            mode_params=params,
        )

        try:
            await self.coordinator.device.set_display(screensaver_config=config)
        except LaMetricApiError as error:
            raise HomeAssistantError(
                f"Failed to configure screensaver on LaMetric device at "
                f"{self.coordinator.device.host}."
            ) from error

        await self.coordinator.async_request_refresh()
