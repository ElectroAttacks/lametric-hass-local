"""Tests for the LaMetric scene platform."""

import asyncio
from collections.abc import Iterable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity

from custom_components.lametric_hass_local.scene import (
    LaMetricSceneEntity,
    async_setup_entry,
)


def _make_app(
    *,
    app_id: str = "com.lametric.clock",
    app_title: str | None = "Clock",
    widget_id: str = "widget1",
    visible: bool = True,
    actions: dict[str, Any] | None = None,
) -> MagicMock:
    app = MagicMock()
    app.id = app_id
    app.title = app_title
    app.actions = actions
    widget = MagicMock()
    widget.visible = visible
    app.widgets = {widget_id: widget}
    return app


def _make_scene(
    coordinator: MagicMock,
    *,
    app_id: str = "com.lametric.clock",
    widget_id: str = "widget1",
    app_title: str | None = "Clock",
    visible: bool = True,
    actions: dict[str, Any] | None = None,
) -> LaMetricSceneEntity:
    app = _make_app(
        app_id=app_id,
        app_title=app_title,
        widget_id=widget_id,
        visible=visible,
        actions=actions,
    )
    coordinator.apps[app.id] = app
    return LaMetricSceneEntity(
        coordinator=coordinator,
        app=app,
        widget_id=widget_id,
    )


def _setup_scene_platform(
    coordinator: MagicMock,
    hass: MagicMock | None = None,
) -> tuple[list[LaMetricSceneEntity], MagicMock, MagicMock]:
    hass = hass or MagicMock()
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator
    config_entry.async_on_unload = MagicMock()
    registry = MagicMock()
    platform = MagicMock()
    collected: list[LaMetricSceneEntity] = []

    def _async_add_entities(
        new_entities: Iterable[Entity],
        update_before_add: bool = False,
        *,
        config_subentry_id: str | None = None,
    ) -> None:
        del update_before_add, config_subentry_id
        collected.extend(cast(LaMetricSceneEntity, entity) for entity in new_entities)

    with (
        patch(
            "custom_components.lametric_hass_local.scene.async_get_current_platform",
            return_value=platform,
        ),
        patch(
            "custom_components.lametric_hass_local.scene.er.async_get",
            return_value=registry,
        ),
    ):
        asyncio.run(async_setup_entry(hass, config_entry, _async_add_entities))

    return collected, registry, platform


def test_unique_id_contains_serial_app_and_widget(coordinator: MagicMock) -> None:
    """Unique ID should be specific to the app widget, not only the app."""
    entity = _make_scene(coordinator, widget_id="widget1")

    assert entity.unique_id == (
        f"{coordinator.data.serial_number}-com.lametric.clock-widget1"
    )


def test_name_is_app_title(coordinator: MagicMock) -> None:
    """Entity name should use the app title when available."""
    entity = _make_scene(coordinator, app_title="Weather")

    assert entity.name == "Weather"


def test_name_falls_back_to_app_id(coordinator: MagicMock) -> None:
    """Entity name should fall back to the app id when no title exists."""
    entity = _make_scene(
        coordinator,
        app_id="com.lametric.weather",
        app_title=None,
    )

    assert entity.name == "com.lametric.weather"


def test_extra_state_attributes_expose_is_visible(coordinator: MagicMock) -> None:
    """Scene attributes should expose whether the widget is currently visible."""
    entity = _make_scene(coordinator, visible=True)

    assert entity.extra_state_attributes == {"is_visible": True}


def test_extra_state_attributes_mark_missing_widget_not_visible(
    coordinator: MagicMock,
) -> None:
    """A missing widget should report is_visible=False instead of crashing."""
    entity = _make_scene(coordinator)
    coordinator.apps["com.lametric.clock"].widgets = {}

    assert entity.extra_state_attributes == {"is_visible": False}


def test_available_false_when_widget_is_missing(coordinator: MagicMock) -> None:
    """Scene entities should become unavailable when their widget disappears."""
    coordinator.last_update_success = True
    entity = _make_scene(coordinator)
    coordinator.apps["com.lametric.clock"].widgets = {}

    assert entity.available is False


def test_activate_calls_activate_widget(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """scene.turn_on should activate the target widget."""
    coordinator.device.activate_widget = AsyncMock()
    entity = _make_scene(coordinator)
    entity.hass = mock_hass

    asyncio.run(entity.async_activate())

    coordinator.device.activate_widget.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
    )


def test_activate_raises_if_widget_is_missing(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Activation should fail cleanly for stale scene entities."""
    entity = _make_scene(coordinator)
    entity.hass = mock_hass
    coordinator.apps.clear()

    with pytest.raises(HomeAssistantError, match="no longer available"):
        asyncio.run(entity.async_activate())


def test_activate_action_service_calls_device(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """activate_action should forward all parameters to the device client."""
    coordinator.device.activate_action = AsyncMock()
    param = MagicMock()
    param.required = False
    entity = _make_scene(coordinator, actions={"toggle": {"on": param}})
    entity.hass = mock_hass
    activate_action = cast(Any, entity)._async_activate_action

    asyncio.run(
        activate_action(
            action_id="toggle",
            action_parameters={"on": True},
            visible=False,
        )
    )

    coordinator.device.activate_action.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
        action_id="toggle",
        action_parameters={"on": True},
        visible=False,
    )


def test_activate_action_service_defaults_visible_true(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """visible should default to True when omitted."""
    coordinator.device.activate_action = AsyncMock()
    entity = _make_scene(coordinator, actions={"start": {}})
    entity.hass = mock_hass
    activate_action = cast(Any, entity)._async_activate_action

    asyncio.run(activate_action(action_id="start"))

    coordinator.device.activate_action.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
        action_id="start",
        action_parameters=None,
        visible=True,
    )


def test_activate_action_raises_for_unknown_action(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Unknown actions should still raise a ValueError."""
    entity = _make_scene(coordinator, actions={"start": {}})
    entity.hass = mock_hass
    activate_action = cast(Any, entity)._async_activate_action

    with pytest.raises(ValueError, match="unknown"):
        asyncio.run(activate_action(action_id="unknown"))


def test_activate_action_raises_for_missing_required_param(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Required action parameters should be validated before the API call."""
    param = MagicMock()
    param.required = True
    entity = _make_scene(coordinator, actions={"configure": {"duration": param}})
    entity.hass = mock_hass
    activate_action = cast(Any, entity)._async_activate_action

    with pytest.raises(ValueError, match="duration"):
        asyncio.run(
            activate_action(
                action_id="configure",
                action_parameters={},
            )
        )


def test_activate_action_raises_if_widget_is_missing(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Action dispatch should fail cleanly for stale scene entities."""
    entity = _make_scene(coordinator, actions={"start": {}})
    entity.hass = mock_hass
    coordinator.apps.clear()
    activate_action = cast(Any, entity)._async_activate_action

    with pytest.raises(HomeAssistantError, match="no longer available"):
        asyncio.run(activate_action(action_id="start"))


def test_setup_entry_creates_one_entity_per_widget(coordinator: MagicMock) -> None:
    """async_setup_entry should create one scene entity per app widget."""
    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.weather"
    app.widgets = {"w1": widget, "w2": widget}
    app.title = "Weather"
    app.actions = None
    coordinator.apps = {"weather": app}

    collected, _registry, platform = _setup_scene_platform(coordinator)

    assert len(collected) == 2
    assert collected[0].unique_id != collected[1].unique_id
    platform.async_register_entity_service.assert_called_once()


def test_setup_entry_adds_new_entities_on_coordinator_update(
    coordinator: MagicMock,
) -> None:
    """Coordinator listener should add only widgets that are new."""
    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.clock"
    app.widgets = {"w1": widget}
    app.title = "Clock"
    app.actions = None
    coordinator.apps = {"clock": app}

    collected, _registry, _platform = _setup_scene_platform(coordinator)

    assert len(collected) == 1

    new_app = MagicMock()
    new_app.id = "com.lametric.weather"
    new_app.widgets = {"w2": widget}
    new_app.title = "Weather"
    new_app.actions = None
    coordinator.apps["weather"] = new_app

    listener = coordinator.async_add_listener.call_args.args[0]
    listener()
    assert len(collected) == 2

    listener()
    assert len(collected) == 2


def test_setup_entry_removes_deleted_entities_from_registry(
    coordinator: MagicMock,
) -> None:
    """Widgets removed from the device should be removed from the entity registry."""
    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.clock"
    app.widgets = {"w1": widget}
    app.title = "Clock"
    app.actions = None
    coordinator.apps = {"clock": app}

    with patch.object(
        LaMetricSceneEntity,
        "registry_entry",
        new_callable=PropertyMock,
        return_value=MagicMock(),
    ):
        collected, registry, _platform = _setup_scene_platform(coordinator)

        assert len(collected) == 1
        collected[0].entity_id = "scene.lametric_clock"

        coordinator.apps = {}
        listener = coordinator.async_add_listener.call_args.args[0]
        listener()

    registry.async_remove.assert_called_once_with("scene.lametric_clock")


def test_setup_entry_removes_deleted_entities_from_runtime(
    coordinator: MagicMock,
) -> None:
    """Widgets without registry entries should be removed from runtime entities."""
    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.clock"
    app.widgets = {"w1": widget}
    app.title = "Clock"
    app.actions = None
    coordinator.apps = {"clock": app}

    hass = MagicMock()

    def _close_task(coro: Any) -> None:
        coro.close()

    hass.async_create_task.side_effect = _close_task
    collected, _registry, _platform = _setup_scene_platform(coordinator, hass=hass)

    assert len(collected) == 1
    collected[0].hass = hass

    with patch.object(collected[0], "async_remove", new=AsyncMock()):
        coordinator.apps = {}
        listener = coordinator.async_add_listener.call_args.args[0]
        listener()

    hass.async_create_task.assert_called_once()
