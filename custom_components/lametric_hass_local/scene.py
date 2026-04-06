"""Scene platform for LaMetric app/widget activation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from lametric.device_apps import App, Widget

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler

ATTR_ACTION_ID = "action_id"  # Action to trigger on the widget
ATTR_ACTION_PARAMETERS = "action_parameters"  # Optional action parameters
ATTR_ACTION_VISIBLE = "visible"  # Bring widget to foreground on activation

SERVICE_ACTIVATE_ACTION = "activate_action"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one scene entity per installed LaMetric app widget."""

    coordinator = config_entry.runtime_data
    known_widget_ids: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add scene entities for any app widgets not yet tracked."""
        new_entities: list[LaMetricSceneEntity] = []

        for app in coordinator.apps.values():
            for widget_id in app.widgets:
                unique_id = f"{coordinator.data.serial_number}-{app.id}-{widget_id}"
                if unique_id not in known_widget_ids:
                    known_widget_ids.add(unique_id)
                    new_entities.append(
                        LaMetricSceneEntity(
                            coordinator=coordinator,
                            app=app,
                            widget_id=widget_id,
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_entities()

    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_entities)
    )

    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_ACTIVATE_ACTION,
        {
            vol.Required(ATTR_ACTION_ID): str,
            vol.Optional(ATTR_ACTION_PARAMETERS): dict,
            vol.Optional(ATTR_ACTION_VISIBLE, default=True): bool,
        },
        "_async_activate_action",
    )


class LaMetricSceneEntity(LaMetricEntity, SceneEntity):
    """Scene entity that targets one fixed app/widget pair."""

    _app_id: str
    _widget_id: str

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        app: App,
        widget_id: str,
    ) -> None:
        """Initialize metadata for a specific app/widget scene."""

        super().__init__(coordinator)

        self._app_id = app.id
        self._widget_id = widget_id
        self._attr_unique_id = f"{coordinator.data.serial_number}-{app.id}"
        self._attr_name = app.title or app.id

    @property
    def _app(self) -> App:
        """Return the current App object from the coordinator."""
        return self.coordinator.apps[self._app_id]

    @property
    def _widget(self) -> Widget:
        """Return the current Widget object from the coordinator."""
        return self.coordinator.apps[self._app_id].widgets[self._widget_id]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return available actions and their parameters for this widget's app."""

        return {
            "is_active": self._widget.visible,
        }

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_activate(self, **_kwargs: Any) -> None:
        """Bring the widget to the foreground on the device."""
        await self.coordinator.device.activate_widget(
            app_id=self._app.id,
            widget_id=self._widget_id,
        )
        await self.coordinator.async_request_refresh()

    @lametric_api_exception_handler
    async def _async_activate_action(
        self,
        action_id: str,
        action_parameters: dict[str, Any] | None = None,
        visible: bool = True,
    ) -> None:
        """Trigger a specific action on the widget (platform entity service)."""
        actions = self._app.actions or {}

        if action_id not in actions:
            available = ", ".join(actions) or "none"
            raise ValueError(
                f"Action '{action_id}' is not available for app '{self._app_id}'. "
                f"Available actions: {available}"
            )

        missing = [
            name
            for name, param in actions[action_id].items()
            if param.required and (action_parameters or {}).get(name) is None
        ]
        if missing:
            raise ValueError(
                f"Action '{action_id}' requires parameter(s): {', '.join(missing)}"
            )

        await self.coordinator.device.activate_action(
            app_id=self._app.id,
            widget_id=self._widget_id,
            action_id=action_id,
            action_parameters=action_parameters,
            visible=visible,
        )
        await self.coordinator.async_request_refresh()
