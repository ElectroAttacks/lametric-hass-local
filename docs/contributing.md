# Contributing

Please see [CONTRIBUTING.md](https://github.com/ElectroAttacks/lametric-hass-local/blob/main/CONTRIBUTING.md) in the repository root for the full developer guide.

## Quick reference

```bash
git clone https://github.com/ElectroAttacks/lametric-hass-local.git
cd lametric-hass-local
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
```

## Platforms

Loaded platforms are defined in `custom_components/lametric_hass_local/const.py`. When adding a new platform:

1. Add it to `PLATFORMS`
2. Forward setup in `__init__.py` (`async_setup_entry` / `async_unload_entry`)
3. Update `translations/en.json` for any new strings

## Update interval

The coordinator polls the device every **30 seconds** (`UPDATE_INTERVAL` in `const.py`).
