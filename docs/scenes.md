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

## Discovering available actions

Every scene entity exposes several **state attributes** that describe the app and its widget:

| Attribute | Description |
|-----------|-------------|
| `vendor` | App vendor/author |
| `version` | Installed app version |
| `triggers` | Trigger list reported by the app |
| `visible` | Whether this widget is currently visible on the device |
| `actions` | Available actions and their parameters (omitted if the app defines none) |

You can inspect these directly in the Home Assistant UI under **Developer Tools → States**, or via a template:

```yaml
{{ state_attr('scene.lametric_stopwatch', 'actions') }}
```

Example output for a stopwatch app:

```yaml
actions:
  stopwatch.start:
    value:
      type: java.lang.Object
      name: value
      required: false
  stopwatch.stop:
    value:
      type: java.lang.Object
      name: value
      required: false
  stopwatch.reset:
    value:
      type: java.lang.Object
      name: value
      required: false
```

If an app defines no actions, the `actions` key is absent from the attributes.
