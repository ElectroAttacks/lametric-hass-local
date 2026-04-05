# LaMetric Local (Home Assistant Custom Integration)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with discovery + config flow support.

## Requirements

- Home Assistant 2024.1 or later
- A LaMetric device reachable from Home Assistant
- For cloud-assisted setup: a LaMetric developer account at [developer.lametric.com](https://developer.lametric.com)

Python dependency (declared in the integration manifest):

- `lametric-py>=1.0.7`

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ElectroAttacks&repository=https%3A%2F%2Fgithub.com%2FElectroAttacks%2Flametric-hass-local&category=Integration)

Click the badge above or follow these steps manually:

1. Open HACS in your Home Assistant instance.
2. Click the three-dot menu in the top right and select **Custom repositories**.
3. Enter `https://github.com/ElectroAttacks/lametric-hass-local` as the repository URL and select **Integration** as the category.
4. Click **Add**, then find and install **LaMetric Local** from the HACS store.
5. Restart Home Assistant.

### Manual

1. Download the latest release from the [Releases page](https://github.com/ElectroAttacks/lametric-hass-local/releases).
2. Copy the `custom_components/lametric_hass_local/` folder into your Home Assistant
   `custom_components/` directory.
3. Restart Home Assistant.

## Configuration

After installation, go to **Settings → Devices & Services → Add Integration** and search for **LaMetric Local**.

You can configure the integration in two ways:

### Option 1 — Manual entry

Provide the local IP address of the device and its **API key**.
You can find the API key in the LaMetric Developer portal under **My Devices** → select a device → **API key**.

### Option 2 — Cloud-assisted entry (recommended)

The cloud path retrieves the device's IP address and API key automatically via the LaMetric Cloud API.
It uses the OAuth 2.0 Authorization Code flow and requires you to register your own OAuth application:

1. Sign in at [developer.lametric.com](https://developer.lametric.com) and create a new application
   (type: **Personal** is sufficient).
2. Set the **OAuth2 Redirect URI** to match your Home Assistant instance, e.g.
   `https://<your-ha-url>/auth/external/callback`.
3. Copy the **Client ID** and **Client Secret** from the app settings.
4. In Home Assistant, go to **Settings → Devices & Services → Application Credentials**,
   click **Add Application Credential**, select **LaMetric Local**, and enter your Client ID and
   Client Secret.
5. Proceed with the integration setup and choose **Import from LaMetric Cloud**.

> **Note:** This step is required because HACS custom integrations cannot ship bundled OAuth
> credentials. The credentials you create belong to your own developer account and are never
> shared with anyone else.


## Activating Apps (Scenes)

Each installed widget/app on the device is exposed as a **scene entity** in Home Assistant.
Calling `scene.turn_on` on a scene entity supports two modes:

### Switch to an app

Brings the app to the foreground on the device:

```yaml
action: scene.turn_on
target:
  entity_id: scene.lametric_clock
```

### Trigger a widget action

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
  visible: true   # bring the widget to foreground (default: true)
```

The `action_id` values and available `action_parameters` depend on the individual app.
You can find them in the [LaMetric Developer documentation](https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-apps.html).

## Services

### `lametric_hass_local.show_message`

Send a text notification to a LaMetric device.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | — | Target device |
| `message` | Yes | — | Text to display |
| `icon` | No | — | LaMetric icon ID (e.g. `i1234`) |
| `icon_type` | No | `none` | `none` / `info` / `alert` |
| `priority` | No | `info` | `info` / `warning` / `critical` |
| `sound` | No | — | Sound to play (see sound list in the UI) |
| `cycles` | No | `1` | Number of display loops (`0` = infinite) |

### `lametric_hass_local.show_chart`

Send a spike chart notification to a LaMetric device.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `device_id` | Yes | — | Target device |
| `data` | Yes | — | List of integer values (e.g. `[1,4,2,5,3]`) |
| `icon_type` | No | `none` | `none` / `info` / `alert` |
| `priority` | No | `info` | `info` / `warning` / `critical` |
| `sound` | No | — | Sound to play |
| `cycles` | No | `1` | Number of display loops (`0` = infinite) |

### Pixel Streaming *(LaMetric SKY only)*

The three streaming services allow you to push raw RGB pixel data to the LaMetric SKY's LED matrix.
For full details on the canvas configuration and available render modes, refer to the
[LaMetric Developer documentation](https://lametric-documentation.readthedocs.io/en/latest/reference-docs/device-display.html).

#### `lametric_hass_local.start_stream`

Start a pixel-streaming session. Returns a `session_id` used by subsequent calls.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` | Yes | Target device |
| `config` | Yes | Stream canvas configuration object (see LaMetric docs) |

#### `lametric_hass_local.send_stream_data`

Push a frame of RGB888 pixel data to an active streaming session.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` | Yes | Target device |
| `session_id` | Yes | Session ID returned by `start_stream` |
| `rgb_data` | Yes | List of `[R, G, B]` triples — one per pixel |

#### `lametric_hass_local.stop_stream`

Stop an active pixel-streaming session.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` | Yes | Target device |

## Diagnostics

Diagnostics redact sensitive fields before export, including:

- device identifiers
- name and serial-related values
- Wi-Fi SSID

## Notes For Contributors

- Update interval is currently set to 30 seconds.
- Loaded platforms are defined in `custom_components/lametric_hass_local/const.py`.
- If you add a new entity platform, include it in `PLATFORMS` and forward setup
  from integration startup (`__init__.py`).
