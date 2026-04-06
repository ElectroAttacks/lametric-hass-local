# Pixel Streaming *(LaMetric SKY only)*

The streaming services allow you to push raw RGB pixel data to the LaMetric SKY's LED matrix in real time.

For full details on canvas configuration and render modes, refer to the [LaMetric Developer documentation](https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-stream.html).

> **Breaking change (April 2026):** These services were previously called with a `device_id` field.
> They are now **platform entity services** targeting the SKY light entity.
> Replace `device_id: "..."` with a `target:` block as shown in the examples below.

---

## `lametric_hass_local.start_stream`

Start a pixel-streaming session. Returns a `session_id` used by subsequent calls.

| Field | Required | Description |
|-------|----------|-------------|
| `target` | Yes | The SKY light entity (e.g. `light.lametric_sky_light`) |
| `config` | Yes | Stream canvas configuration object (see below) |

### `config` structure

```yaml
fill_type: scale        # scale | tile
render_mode: pixel      # pixel | triangle
post_process:
  type: none            # none | effect
  params:               # only required when type is 'effect'
    effect_type: fading_pixels
    effect_params:
      smooth: true
      pixel_fill: 1
      fade_speed: 0.005
      pixel_base: 0.05
```

### Return value

```json
{ "success": true, "session_id": "<hex-session-id>" }
```

### Example

```yaml
action: lametric_hass_local.start_stream
target:
  entity_id: light.lametric_sky_light
data:
  config:
    fill_type: scale
    render_mode: pixel
    post_process:
      type: none
```

---

## `lametric_hass_local.send_stream_data`

Push a single frame of RGB888 pixel data to an active streaming session.

| Field | Required | Description |
|-------|----------|-------------|
| `target` | Yes | The SKY light entity |
| `session_id` | Yes | Session ID returned by `start_stream` |
| `rgb_data` | Yes | List of `[R, G, B]` triples — one per pixel, covering the full canvas (`width × height` pixels) |

### Example

```yaml
action: lametric_hass_local.send_stream_data
target:
  entity_id: light.lametric_sky_light
data:
  session_id: "deadbeef..."
  rgb_data:
    - [255, 0, 0]
    - [0, 255, 0]
    - [0, 0, 255]
```

---

## `lametric_hass_local.stop_stream`

Stop an active pixel-streaming session and return the device to normal operation.

| Field | Required | Description |
|-------|----------|-------------|
| `target` | Yes | The SKY light entity |

### Example

```yaml
action: lametric_hass_local.stop_stream
target:
  entity_id: light.lametric_sky_light
```
