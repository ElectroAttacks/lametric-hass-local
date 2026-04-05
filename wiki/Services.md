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

> For pixel-streaming services (`start_stream`, `send_stream_data`, `stop_stream`) see [Pixel Streaming](Pixel-Streaming).
