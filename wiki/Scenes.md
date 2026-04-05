# Scenes (App Control)

Each installed widget/app on the LaMetric device is exposed as a **scene entity** in Home Assistant.

## Switch to an app

Brings the app to the foreground on the device:

```yaml
action: scene.turn_on
target:
  entity_id: scene.lametric_clock
```

## Trigger a widget action

Some LaMetric apps support actions (e.g. start/stop a stopwatch, set a countdown timer).
Pass `action_id` and optionally `action_parameters` as extra data:

```yaml
action: scene.turn_on
target:
  entity_id: scene.lametric_stopwatch
data:
  action_id: "stopwatch.start"
```

```yaml
action: scene.turn_on
target:
  entity_id: scene.lametric_countdown
data:
  action_id: "countdown.configure"
  action_parameters:
    duration: 300
  visible: true   # bring the widget to the foreground (default: true)
```

The `action_id` values and available `action_parameters` depend on the individual app.
Refer to the [LaMetric Developer documentation](https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-apps.html) for details.
