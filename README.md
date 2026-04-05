# LaMetric Local (Home Assistant Custom Integration)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with Zeroconf / SSDP / DHCP discovery and a config flow.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ElectroAttacks/lametric-hass-local)](https://github.com/ElectroAttacks/lametric-hass-local/releases)
[![License](https://img.shields.io/github/license/ElectroAttacks/lametric-hass-local)](.github/LICENSE)

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=lametric-hass-local&category=Integration&owner=ElectroAttacks)

Install via HACS (recommended) or copy `custom_components/lametric_hass_local/` manually into your HA `custom_components/` folder and restart.

→ Full instructions: [Wiki — Installation](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Installation)

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **LaMetric Local**. Supports manual entry (IP + API key) and cloud-assisted OAuth setup.

→ [Wiki — Configuration](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Configuration)

## Features

| Feature | Details |
|---------|---------|
| **Entities** | Button, Light (SKY), Number, Scene, Select, Sensor, Switch, Text, Update |
| **Services** | `show_message`, `show_chart`, pixel streaming (SKY) |
| **Discovery** | Zeroconf, SSDP, DHCP |
| **Config flow** | Manual or LaMetric Cloud OAuth |

→ [Wiki — Services](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Services)
→ [Wiki — Scenes](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Scenes)
→ [Wiki — Pixel Streaming](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Pixel-Streaming)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) · [Wiki — Contributing](https://github.com/ElectroAttacks/lametric-hass-local/wiki/Contributing)

## Support

If this integration is useful to you, consider [sponsoring the project](https://github.com/sponsors/ElectroAttacks). ❤️
