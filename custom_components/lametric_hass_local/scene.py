"""Scene platform for LaMetric app/widget activation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from lametric.device_apps import Parameter

from .coordinator import LaMetricConfigEntry, LaMetricCoordinator
from .entity import LaMetricEntity
from .helpers import lametric_api_exception_handler

ATTR_ACTION_ID = "action_id"  # Action to trigger on the widget
ATTR_ACTION_PARAMETERS = "action_parameters"  # Optional action parameters
ATTR_ACTION_VISIBLE = "visible"  # Bring widget to foreground on activation


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
        """Add scene entities for any newly discovered app widgets."""
        new_entities: list[LaMetricSceneEntity] = []
        for app in coordinator.apps.values():
            for widget_id in app.widgets:
                unique_id = f"{coordinator.data.serial_number}-{app.id}-{widget_id}"
                if unique_id not in known_widget_ids:
                    known_widget_ids.add(unique_id)
                    new_entities.append(
                        LaMetricSceneEntity(
                            coordinator=coordinator,
                            app_id=app.id,
                            widget_id=widget_id,
                            app_title=app.title,
                            actions=app.actions,
                        )
                    )
        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_entities()

    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_entities)
    )


class LaMetricSceneEntity(LaMetricEntity, SceneEntity):
    """Scene entity that targets one fixed app/widget pair."""

    app_id: str
    widget_id: str
    _actions: dict[str, dict[str, Parameter]] | None

    def __init__(
        self,
        coordinator: LaMetricCoordinator,
        app_id: str,
        widget_id: str,
        app_title: str | None,
        actions: dict[str, dict[str, Parameter]] | None,
    ) -> None:
        """Initialize metadata for a specific app/widget scene."""

        super().__init__(coordinator)

        self.app_id = app_id
        self.widget_id = widget_id
        self._actions = actions
        self._attr_unique_id = f"{coordinator.data.serial_number}-{app_id}-{widget_id}"
        self._attr_name = app_title or app_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return available actions and their parameters for this widget's app."""

        if not self._actions:
            return {}

        return {
            "actions": {
                action_id: {
                    param_name: {
                        "type": param.data_type,
                        "name": param.name,
                        "required": param.required,
                        **({"format": param.format} if param.format else {}),
                    }
                    for param_name, param in params.items()
                }
                for action_id, params in self._actions.items()
            }
        }

    @lametric_api_exception_handler  # type: ignore[arg-type]
    async def async_activate(self, **_kwargs: Any) -> None:
        """Activate widget or widget action using optional service kwargs.

        Supported kwargs:
        - action_id: Action to execute on the configured widget.
        - action_parameters: Optional action parameters payload.
        - visible: Whether the action should bring the widget to foreground.
        """

        if (action_id := _kwargs.get(ATTR_ACTION_ID)) is not None:
            await self.coordinator.device.activate_action(
                app_id=self.app_id,
                widget_id=self.widget_id,
                action_id=action_id,
                action_parameters=_kwargs.get(ATTR_ACTION_PARAMETERS),
                visible=_kwargs.get(ATTR_ACTION_VISIBLE, True),
            )
        else:
            await self.coordinator.device.activate_widget(
                app_id=self.app_id,
                widget_id=self.widget_id,
            )

        await super().async_activate(**_kwargs)

        await self.coordinator.async_request_refresh()
