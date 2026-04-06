# lametric-hass-local

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ElectroAttacks/lametric-hass-local)](https://github.com/ElectroAttacks/lametric-hass-local/releases)
[![License](https://img.shields.io/github/license/ElectroAttacks/lametric-hass-local)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-electroattacks.github.io-blue)](https://electroattacks.github.io/lametric-hass-local/)
[![Contributing](https://img.shields.io/badge/contributing-guide-brightgreen)](.github/CONTRIBUTING.md)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with Zeroconf / SSDP / DHCP discovery and a config flow.

## Features

- Button, Light (SKY), Number, Scene, Select, Sensor, Switch, Text, and Update entities
- Services: `show_message`, `show_chart`, and pixel streaming (SKY)
- Automatic discovery via Zeroconf, SSDP, and DHCP
- Config flow with manual entry (IP + API key) or LaMetric Cloud OAuth

## Requirements

- Home Assistant 2024.1+
- A LaMetric device on the local network
- A LaMetric developer account for cloud-assisted OAuth setup (optional)

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=lametric-hass-local&category=Integration&owner=ElectroAttacks)

Install via HACS (recommended) or copy `custom_components/lametric_hass_local/` manually
into your HA `custom_components/` folder and restart Home Assistant.

Full instructions: [electroattacks.github.io/lametric-hass-local/installation](https://electroattacks.github.io/lametric-hass-local/installation)

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **LaMetric Local**.
Supports manual entry (IP + API key) and cloud-assisted OAuth setup.

Full instructions: [electroattacks.github.io/lametric-hass-local/configuration](https://electroattacks.github.io/lametric-hass-local/configuration)

## Documentation

Full documentation is available at **[electroattacks.github.io/lametric-hass-local](https://electroattacks.github.io/lametric-hass-local/)**.

- [Services](https://electroattacks.github.io/lametric-hass-local/#show-message) — `show_message`, `show_chart`
- [Scenes & activate_action](https://electroattacks.github.io/lametric-hass-local/#scenes) — widget activation and actions
- [Pixel Streaming (SKY)](https://electroattacks.github.io/lametric-hass-local/#streaming) — LMSP frame streaming
- [All Entities](https://electroattacks.github.io/lametric-hass-local/#entities) — overview of every entity platform

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) or [electroattacks.github.io/lametric-hass-local/#contributing](https://electroattacks.github.io/lametric-hass-local/#contributing).

## Support

If this integration is useful to you, consider [sponsoring the project](https://github.com/sponsors/ElectroAttacks). ❤️
