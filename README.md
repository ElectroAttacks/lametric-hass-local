# LaMetric Local (Home Assistant Custom Integration)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with discovery + config flow support.

## Status

Work in progress.

Implemented in this repository today:

- Config flow with discovery support (DHCP, SSDP, Zeroconf)
- Manual setup via host + API key
- Cloud-assisted setup via OAuth2 (device selection)
- Button entity platform
- Diagnostics endpoint with redacted sensitive fields

Present but not yet wired into platform loading:

- Light platform module (`custom_components/lametric_hass_local/light.py`)

## Requirements

- Home Assistant with support for custom integrations
- A LaMetric device reachable from Home Assistant
- Device API key (for local API access)

Python dependency (declared in the integration manifest):

- `lametric-py>=1.0.0`

## Installation

1. Copy this repository to your Home Assistant `custom_components` directory so
	the integration lives at:
	`custom_components/lametric_hass_local/`
2. Restart Home Assistant.
3. Go to Settings -> Devices & Services -> Add Integration.
4. Search for `LaMetric Local`.

## Configuration

You can configure the integration in two ways:

1. Manual entry
	- Provide `host` and `API key`.
2. Cloud-assisted entry
	- Authenticate with LaMetric Cloud
	- Pick a discovered cloud device
	- Integration stores local host + API key for local polling

The config flow also supports auto-discovery:

- DHCP
- SSDP (`urn:schemas-upnp-org:device:LaMetric:1`)
- Zeroconf (`_lametric-api._tcp.local.`)

## Entities

### Buttons

Current button actions exposed by the integration:

- `next_app`
- `previous_app`
- `dismiss_current_notification`
- `dismiss_all_notifications`

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
