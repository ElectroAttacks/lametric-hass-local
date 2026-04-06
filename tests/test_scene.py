"""Tests for the LaMetric scene platform."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.lametric_hass_local.scene import (
    ATTR_ACTION_ID,
    ATTR_ACTION_PARAMETERS,
    ATTR_ACTION_VISIBLE,
    LaMetricSceneEntity,
)


def _make_scene(
    coordinator: MagicMock,
    *,
    app_id: str = "com.lametric.clock",
    widget_id: str = "widget1",
    app_title: str = "Clock",
    actions: dict | None = None,
) -> LaMetricSceneEntity:
    return LaMetricSceneEntity(
        coordinator=coordinator,
        app_id=app_id,
        widget_id=widget_id,
        app_title=app_title,
        actions=actions,
    )


# ── metadata ─────────────────────────────────────────────────────────────────


def test_unique_id_contains_serial_app_and_widget(
    coordinator: MagicMock,
) -> None:
    """Unique ID is serial_number + app_id + widget_id."""
    entity = _make_scene(coordinator)
    assert entity.unique_id == (
        f"{coordinator.data.serial_number}-com.lametric.clock-widget1"
    )


def test_name_is_app_title(coordinator: MagicMock) -> None:
    """Entity name is the app title."""
    entity = _make_scene(coordinator, app_title="Weather")
    assert entity.name == "Weather"


def test_name_falls_back_to_app_id(coordinator: MagicMock) -> None:
    """Entity name falls back to app_id when app_title is None."""
    entity = _make_scene(
        coordinator,
        app_title=None,  # type: ignore[arg-type]
        app_id="com.lametric.weather",
    )
    assert entity.name == "com.lametric.weather"


# ── extra_state_attributes ────────────────────────────────────────────────────


def test_extra_state_attributes_empty_without_actions(
    coordinator: MagicMock,
) -> None:
    """extra_state_attributes returns {} when no actions are defined."""
    entity = _make_scene(coordinator, actions=None)
    assert entity.extra_state_attributes == {}


def test_extra_state_attributes_contains_action_metadata(
    coordinator: MagicMock,
) -> None:
    """extra_state_attributes exposes action parameters."""
    param = MagicMock()
    param.data_type = "string"
    param.name = "text"
    param.required = True
    param.format = None

    actions = {"activate": {"text": param}}
    entity = _make_scene(coordinator, actions=actions)
    attrs = entity.extra_state_attributes

    assert "actions" in attrs
    assert "activate" in attrs["actions"]
    assert attrs["actions"]["activate"]["text"]["type"] == "string"


# ── async_activate ────────────────────────────────────────────────────────────


def test_activate_without_action_calls_activate_widget(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Activation without action_id calls activate_widget."""
    coordinator.device.activate_widget = AsyncMock()
    entity = _make_scene(coordinator)
    entity.hass = mock_hass

    asyncio.run(entity.async_activate())

    coordinator.device.activate_widget.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
    )


def test_activate_with_action_calls_activate_action(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """Activation with action_id calls activate_action."""
    coordinator.device.activate_action = AsyncMock()
    entity = _make_scene(coordinator)
    entity.hass = mock_hass

    asyncio.run(
        entity.async_activate(
            **{
                ATTR_ACTION_ID: "toggle",
                ATTR_ACTION_PARAMETERS: {"on": True},
                ATTR_ACTION_VISIBLE: False,
            }
        )
    )

    coordinator.device.activate_action.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
        action_id="toggle",
        action_parameters={"on": True},
        visible=False,
    )


def test_setup_entry_creates_one_entity_per_widget(coordinator: MagicMock) -> None:
    """async_setup_entry builds a scene entity for every app/widget combination."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.scene import async_setup_entry

    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.weather"
    app.widgets = {"w1": widget, "w2": widget}
    app.title = "Weather"
    app.actions = None

    coordinator.apps = {"weather": app}
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == 2  # one entity per widget
