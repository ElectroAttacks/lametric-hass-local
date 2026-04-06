"""Tests for the LaMetric scene platform."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.lametric_hass_local.scene import (
    LaMetricSceneEntity,
)


def _make_app(
    *,
    app_id: str = "com.lametric.clock",
    app_title: str = "Clock",
    actions: dict | None = None,
) -> MagicMock:
    app = MagicMock()
    app.id = app_id
    app.title = app_title
    app.actions = actions
    return app


def _make_scene(
    coordinator: MagicMock,
    *,
    app_id: str = "com.lametric.clock",
    widget_id: str = "widget1",
    app_title: str = "Clock",
    actions: dict | None = None,
) -> LaMetricSceneEntity:
    app = _make_app(app_id=app_id, app_title=app_title, actions=actions)
    widget = MagicMock()
    app.widgets = {widget_id: widget}
    coordinator.apps[app_id] = app
    return LaMetricSceneEntity(
        coordinator=coordinator,
        app=app,
        widget_id=widget_id,
    )


# ── metadata ─────────────────────────────────────────────────────────────────


def test_unique_id_contains_serial_and_app(
    coordinator: MagicMock,
) -> None:
    """Unique ID is serial_number + app_id."""
    entity = _make_scene(coordinator)
    assert entity.unique_id == (f"{coordinator.data.serial_number}-com.lametric.clock")


def test_name_is_app_title(coordinator: MagicMock) -> None:
    """Entity name is the app title."""
    entity = _make_scene(coordinator, app_title="Weather")
    assert entity.name == "Weather"


def test_name_falls_back_to_app_id(coordinator: MagicMock) -> None:
    """Entity name falls back to app_id when app_title is None."""
    app = _make_app(app_id="com.lametric.weather", app_title=None)  # type: ignore[arg-type]
    app.widgets = {"widget1": MagicMock()}
    coordinator.apps["com.lametric.weather"] = app
    entity = LaMetricSceneEntity(
        coordinator=coordinator,
        app=app,
        widget_id="widget1",
    )
    assert entity.name == "com.lametric.weather"


# ── extra_state_attributes ────────────────────────────────────────────────────


def test_extra_state_attributes_base_fields_always_present(
    coordinator: MagicMock,
) -> None:
    """extra_state_attributes only contains is_active."""
    entity = _make_scene(coordinator, actions=None)
    attrs = entity.extra_state_attributes
    assert "is_active" in attrs
    assert "actions" not in attrs


# ── async_activate ────────────────────────────────────────────────────────────


def test_activate_calls_activate_widget(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """scene.turn_on calls activate_widget to bring widget to foreground."""
    coordinator.device.activate_widget = AsyncMock()
    entity = _make_scene(coordinator)
    entity.hass = mock_hass

    asyncio.run(entity.async_activate())

    coordinator.device.activate_widget.assert_awaited_once_with(
        app_id="com.lametric.clock",
        widget_id="widget1",
    )


# ── _async_activate_action (platform entity service) ──────────────────────────


def test_activate_action_service_calls_device(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """_async_activate_action passes all parameters to the device client."""
    coordinator.device.activate_action = AsyncMock()
    param = MagicMock()
    param.required = False
    entity = _make_scene(coordinator, actions={"toggle": {"on": param}})
    entity.hass = mock_hass

    asyncio.run(
        entity._async_activate_action(
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
    """visible defaults to True when omitted."""
    coordinator.device.activate_action = AsyncMock()
    entity = _make_scene(coordinator, actions={"start": {}})
    entity.hass = mock_hass

    asyncio.run(entity._async_activate_action(action_id="start"))

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
    """ValueError is raised when action_id is not in the app's actions."""
    entity = _make_scene(coordinator, actions={"start": {}})
    entity.hass = mock_hass

    try:
        asyncio.run(entity._async_activate_action(action_id="unknown"))
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "unknown" in str(exc)
        assert "start" in str(exc)


def test_activate_action_raises_for_missing_required_param(
    coordinator: MagicMock, mock_hass: MagicMock
) -> None:
    """ValueError is raised when a required parameter is missing."""
    param = MagicMock()
    param.required = True
    entity = _make_scene(coordinator, actions={"configure": {"duration": param}})
    entity.hass = mock_hass

    try:
        asyncio.run(
            entity._async_activate_action(action_id="configure", action_parameters={})
        )
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "duration" in str(exc)


def test_setup_entry_creates_one_entity_per_widget(coordinator: MagicMock) -> None:
    """async_setup_entry builds a scene entity for every app/widget combination."""
    import asyncio
    from unittest.mock import MagicMock, patch

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
    with patch(
        "custom_components.lametric_hass_local.scene.async_get_current_platform"
    ):
        asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == 2  # one entity per widget


def test_setup_entry_adds_new_entities_on_coordinator_update(
    coordinator: MagicMock,
) -> None:
    """Coordinator listener picks up widgets installed after initial setup."""
    import asyncio
    from unittest.mock import MagicMock, patch

    from custom_components.lametric_hass_local.scene import async_setup_entry

    widget = MagicMock()
    app = MagicMock()
    app.id = "com.lametric.clock"
    app.widgets = {"w1": widget}
    app.title = "Clock"
    app.actions = None

    coordinator.apps = {"clock": app}
    listener_callbacks: list = []
    config_entry = MagicMock()
    config_entry.runtime_data = coordinator
    config_entry.async_on_unload.side_effect = lambda fn: listener_callbacks.append(fn)

    collected: list = []
    with patch(
        "custom_components.lametric_hass_local.scene.async_get_current_platform"
    ):
        asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    assert len(collected) == 1

    # Simulate a new app being installed and the coordinator firing an update
    new_app = MagicMock()
    new_app.id = "com.lametric.weather"
    new_app.widgets = {"w2": widget}
    new_app.title = "Weather"
    new_app.actions = None
    coordinator.apps["weather"] = new_app

    # The listener registered via async_on_unload should add the new entity
    assert listener_callbacks, "No listener was registered"
    # coordinator.async_add_listener returns a callable; simulate its invocation
    coordinator.async_add_listener.call_args[0][0]()
    assert len(collected) == 2

    # A second update with the same apps must not produce duplicates
    coordinator.async_add_listener.call_args[0][0]()
    assert len(collected) == 2
