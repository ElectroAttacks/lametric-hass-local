# LaMetric Local (Home Assistant Custom Integration)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with discovery + config flow support.

## Requirements

- Home Assistant with support for custom integrations
- A LaMetric device reachable from Home Assistant
- Device API key (for local API access)

Python dependency (declared in the integration manifest):

- `lametric-py>=1.0.6`

## Installation

1. Copy this repository to your Home Assistant `custom_components` directory so
	the integration lives at:
	`custom_components/lametric_hass_local/`
2. Restart Home Assistant.
3. Go to Settings -> Devices & Services -> Add Integration.
4. Search for `LaMetric Local`.

## Configuration

You can configure the integration in two ways:

1. **Manual entry** — Provide `host` and `API key`.
2. **Cloud-assisted entry** — Authenticate with LaMetric Cloud, pick a
   discovered device; the integration stores the local host + API key for
   local polling.

The config flow also supports auto-discovery:

- DHCP
- SSDP (`urn:schemas-upnp-org:device:LaMetric:1`)
- Zeroconf (`_lametric-api._tcp.local.`)

## Entities

### Buttons

| Key | Description |
|-----|-------------|
| `next_app` | Switch to the next app |
| `previous_app` | Switch to the previous app |
| `dismiss_current_notification` | Dismiss the current notification |
| `dismiss_all_notifications` | Dismiss all notifications |

### Light *(LaMetric SKY only)*

| Key | Description |
|-----|-------------|
| `sky_light` | Control the SKY LED panel brightness and on/off state |

### Number

| Key | Description |
|-----|-------------|
| `brightness` | Display brightness (1–100 %) |
| `volume` | Speaker volume (0–100 %) |

### Select

| Key | Options | Description |
|-----|---------|-------------|
| `brightness_mode` | `auto`, `manual` | How display brightness is controlled |

### Sensor

| Key | Description |
|-----|-------------|
| `rssi` | Wi-Fi signal strength in % (diagnostic, disabled by default) |

### Switch

| Key | Description |
|-----|-------------|
| `bluetooth_active` | Enable/disable Bluetooth |
| `display_on` | Turn the display on or off |

### Update

Tracks available firmware updates for devices running OS 2.3.0 or later.

### Scene

One scene entity is created per installed app widget, allowing you to activate
any app on the device from Home Assistant.

### Notify

A legacy notify service is registered per device, allowing you to send
notifications to the device from automations using `notify.send_message`.

Supported `data` fields:

| Field | Type | Description |
|-------|------|-------------|
| `icon` | string | LaMetric icon ID (e.g. `i1234`) or short name |
| `icon_type` | `none` \| `info` \| `alert` | Icon indicator type |
| `priority` | `info` \| `warning` \| `critical` | Notification priority |
| `sound` | string | Sound ID (AlarmSound or NotificationSound) |
| `cycles` | int | Number of display loops (default: 1) |

## Services

### `lametric_hass_local.show_message`

Send a text notification to a LaMetric device.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` | Yes | Target device |
| `message` | Yes | Text to display |
| `icon` | No | LaMetric icon ID or name |
| `icon_type` | No | `none` / `info` / `alert` (default: `none`) |
| `priority` | No | `info` / `warning` / `critical` (default: `info`) |
| `sound` | No | Sound to play |
| `cycles` | No | Loop count (default: 1) |

### `lametric_hass_local.show_chart`

Send a spike chart notification to a LaMetric device.

| Field | Required | Description |
|-------|----------|-------------|
| `device_id` | Yes | Target device |
| `data` | Yes | List of integer values (e.g. `[1,4,2,5,3]`) |
| `icon_type` | No | Icon indicator type |
| `priority` | No | Notification priority |
| `sound` | No | Sound to play |
| `cycles` | No | Loop count |

### `lametric_hass_local.start_stream` *(LaMetric SKY only)*

Start a pixel-streaming session. Returns a `session_id` for subsequent
`send_stream_data` calls.

### `lametric_hass_local.send_stream_data` *(LaMetric SKY only)*

Push a frame of RGB888 pixel data to an active streaming session.

### `lametric_hass_local.stop_stream` *(LaMetric SKY only)*

Stop an active pixel-streaming session.

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
