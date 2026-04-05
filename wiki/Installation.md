# Installation

## HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=lametric-hass-local&category=Integration&owner=ElectroAttacks)

Click the badge above or follow these steps manually:

1. Open HACS in your Home Assistant instance.
2. Click the three-dot menu in the top right and select **Custom repositories**.
3. Enter `https://github.com/ElectroAttacks/lametric-hass-local` as the repository URL and select **Integration** as the category.
4. Click **Add**, then find and install **LaMetric Local** from the HACS store.
5. Restart Home Assistant.

## Manual

1. Download the latest release from the [Releases page](https://github.com/ElectroAttacks/lametric-hass-local/releases).
2. Copy the `custom_components/lametric_hass_local/` folder into your Home Assistant `custom_components/` directory.
3. Restart Home Assistant.

## Requirements

- Home Assistant 2024.1 or later
- A LaMetric device reachable from Home Assistant
- For cloud-assisted setup: a LaMetric developer account at [developer.lametric.com](https://developer.lametric.com)
