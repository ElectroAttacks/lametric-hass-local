# Services

## `lametric_hass_local.show_message`

Send a text notification to a LaMetric device.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | — | Target device |
| `message` | Yes | — | Text to display |
| `icon` | No | — | LaMetric icon ID (e.g. `i1234`) |
| `icon_type` | No | `none` | `none` / `info` / `alert` |
| `priority` | No | `info` | `info` / `warning` / `critical` |
| `sound` | No | — | Sound to play (see selector in the UI for full list) |
| `cycles` | No | `1` | Number of display loops (`0` = infinite) |

### Example

```yaml
action: lametric_hass_local.show_message
data:
  device_id: "abc123"
  message: "Hello!"
  icon: "i1234"
  priority: info
  sound: notification
```

---

## `lametric_hass_local.show_chart`

Send a spike chart notification to a LaMetric device.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | — | Target device |
| `data` | Yes | — | List of integer values (e.g. `[1,4,2,5,3]`) |
| `icon_type` | No | `none` | `none` / `info` / `alert` |
| `priority` | No | `info` | `info` / `warning` / `critical` |
| `sound` | No | — | Sound to play |
| `cycles` | No | `1` | Number of display loops (`0` = infinite) |

### Example

```yaml
action: lametric_hass_local.show_chart
data:
  device_id: "abc123"
  data: [1, 3, 5, 4, 2, 6, 3]
```

---

## `lametric_hass_local.set_screensaver`

Enable or disable the screensaver on a LaMetric device and configure its activation mode.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | — | Target device |
| `enabled` | Yes | — | `true` to enable, `false` to disable |
| `mode` | No | `when_dark` | `when_dark` or `time_based` |
| `mode_params` | No | — | Time window config for `time_based` mode (see below) |

### Modes

- **`when_dark`** — screensaver activates automatically when the ambient light sensor detects a dark environment.
- **`time_based`** — screensaver activates during a fixed daily time window.

For `time_based` mode, pass `mode_params` as a mapping:

| Key | Description |
|-----|-------------|
| `enabled` | Whether the time window is active |
| `start_time` | Start of the screensaver window (ISO 8601, e.g. `2000-01-01T22:00:00`) |
| `end_time` | End of the screensaver window (ISO 8601, e.g. `2000-01-01T08:00:00`) |

### Examples

```yaml
# Enable screensaver in when-dark mode
action: lametric_hass_local.set_screensaver
data:
  device_id: "abc123"
  enabled: true
  mode: when_dark
```

```yaml
# Enable screensaver between 22:00 and 08:00
action: lametric_hass_local.set_screensaver
data:
  device_id: "abc123"
  enabled: true
  mode: time_based
  mode_params:
    enabled: true
    start_time: "2000-01-01T22:00:00"
    end_time: "2000-01-01T08:00:00"
```

```yaml
# Disable screensaver entirely
action: lametric_hass_local.set_screensaver
data:
  device_id: "abc123"
  enabled: false
```

---

> For pixel-streaming services (`start_stream`, `send_stream_data`, `stop_stream`) see [Pixel Streaming](pixel-streaming.md).
> These are **platform entity services** targeting the SKY light entity, not device_id-based.
