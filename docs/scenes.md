# Scenes (App Control)

Each installed widget/app on the LaMetric device is exposed as a **scene entity** in Home Assistant.
Scene entities are **automatically added** when new apps are installed on the device — no restart required.

## Switch to an app

Brings the app to the foreground on the device:

```yaml
action: scene.turn_on
target:
  entity_id: scene.lametric_clock
```

## Trigger a widget action

Some LaMetric apps support actions (e.g. start/stop a stopwatch, set a countdown timer).
Use the dedicated `lametric_hass_local.activate_action` service:

```yaml
action: lametric_hass_local.activate_action
target:
  entity_id: scene.lametric_stopwatch
data:
  action_id: "stopwatch.start"
```

```yaml
action: lametric_hass_local.activate_action
target:
  entity_id: scene.lametric_countdown
data:
  action_id: "countdown.configure"
  action_parameters:
    duration: 300
  visible: true   # bring the widget to the foreground (default: true)
```

The service validates the call before sending it to the device:
- If `action_id` is not supported by the app, a `ValueError` is raised listing the available actions.
- If a required parameter is missing from `action_parameters`, a `ValueError` is raised naming the missing fields.

The `action_id` values and required `action_parameters` depend on the individual app.
Refer to the [LaMetric Developer documentation](https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-apps.html) for details.

## State attributes

| Attribute | Description |
|-----------|-------------|
| `is_active` | Whether this widget is currently visible on the device |
