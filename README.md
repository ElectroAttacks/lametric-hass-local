# lametric-hass-local

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/ElectroAttacks/lametric-hass-local)](https://github.com/ElectroAttacks/lametric-hass-local/releases)
[![License](https://img.shields.io/github/license/ElectroAttacks/lametric-hass-local)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-electroattacks.github.io-blue)](https://electroattacks.github.io/lametric-hass-local/)

Local Home Assistant integration for LaMetric devices using the device API
(`lametric-py`) with Zeroconf / SSDP / DHCP discovery and a config flow.

## Requirements

- Home Assistant 2026.1.0 or later
- A LaMetric device on the local network
- A LaMetric developer account for cloud-assisted OAuth setup (optional)

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=lametric-hass-local&category=Integration&owner=ElectroAttacks)

Install via HACS (recommended) or copy `custom_components/lametric_hass_local/` manually
into your HA `custom_components/` folder and restart Home Assistant.

## Documentation

Full documentation — including configuration, entities, services, pixel streaming, and contributing — is available at
**[electroattacks.github.io/lametric-hass-local](https://electroattacks.github.io/lametric-hass-local/)**.
