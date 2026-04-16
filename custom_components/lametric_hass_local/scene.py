"""Scene platform for LaMetric app/widget activation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
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


def _scene_unique_id(serial_number: str, app_id: str, widget_id: str) -> str:
    """Build a widget-specific unique ID for a scene entity."""
    return f"{serial_number}-{app_id}-{widget_id}"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: LaMetricConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one scene entity per installed LaMetric app widget."""

    coordinator = config_entry.runtime_data
    entity_registry = er.async_get(hass)
    tracked_entities: dict[str, LaMetricSceneEntity] = {}

    @callback
    def _async_sync_entities() -> None:
        """Add new scene entities and remove stale ones after app refreshes."""
        new_entities: list[LaMetricSceneEntity] = []
        current_widget_ids: set[str] = set()

        for app in coordinator.apps.values():
            for widget_id in app.widgets:
                unique_id = _scene_unique_id(
                    coordinator.data.serial_number, app.id, widget_id
                )
                current_widget_ids.add(unique_id)

                if unique_id not in tracked_entities:
                    entity = LaMetricSceneEntity(
                        coordinator=coordinator,
                        app=app,
                        widget_id=widget_id,
                    )
                    tracked_entities[unique_id] = entity
                    new_entities.append(entity)

        for unique_id in set(tracked_entities) - current_widget_ids:
            entity = tracked_entities.pop(unique_id)

            if entity.registry_entry is not None:
                entity_registry.async_remove(entity.entity_id)
            else:
                hass.async_create_task(entity.async_remove(force_remove=True))

        if new_entities:
            async_add_entities(new_entities)

    _async_sync_entities()

    config_entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))

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
        self._attr_unique_id = _scene_unique_id(
            coordinator.data.serial_number, app.id, widget_id
        )
        self._attr_name = app.title or app.id

    @property
    def _app(self) -> App | None:
        """Return the current App object from the coordinator."""
        return self.coordinator.apps.get(self._app_id)

    @property
    def _widget(self) -> Widget | None:
        """Return the current Widget object from the coordinator."""
        if (app := self._app) is None:
            return None

        return app.widgets.get(self._widget_id)

    @property
    def available(self) -> bool:
        """Return whether the target widget still exists and the device is online."""
        return self.coordinator.last_update_success and self._widget is not None

    def _require_widget(self) -> tuple[App, Widget]:
        """Return the current app/widget pair or raise a user-facing HA error."""
        app = self._app
        widget = self._widget

        if app is None or widget is None:
            raise HomeAssistantError(
                f"LaMetric widget '{self._widget_id}' for app '{self._app_id}' "
                "is no longer available."
            )

        return app, widget

    @property  # pyright: ignore[reportIncompatibleMethodOverride]
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return available actions and their parameters for this widget's app."""
        widget = self._widget
        return {"is_visible": False if widget is None else widget.visible}

    @lametric_api_exception_handler  # type: ignore[arg-type]
    # pyright: ignore[reportIncompatibleMethodOverride]
    async def async_activate(self, **_kwargs: Any) -> None:
        """Bring the widget to the foreground on the device."""
        app, _widget = self._require_widget()

        await self.coordinator.device.activate_widget(
            app_id=app.id,
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
        app, _widget = self._require_widget()
        actions = app.actions or {}

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
            app_id=app.id,
            widget_id=self._widget_id,
            action_id=action_id,
            action_parameters=action_parameters,
            visible=visible,
        )
        await self.coordinator.async_request_refresh()
