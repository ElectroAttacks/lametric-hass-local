# Contributing

Thank you for considering a contribution to **LaMetric Local**! Here's everything you need to get started.

## Development setup

**Prerequisites:** Python 3.14, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/ElectroAttacks/lametric-hass-local.git
cd lametric-hass-local
uv sync
uv run pre-commit install
```

## Running checks

```bash
uv run pre-commit run --all-files   # lint, format, type-check, tests
uv run pytest                       # tests only
uv run mypy .                       # type-check only
```

## Commit style

This project uses [Conventional Commits](https://www.conventionalcommits.org):

| Prefix | Description |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change without feature/fix |
| `chore:` | Maintenance (deps, CI, …) |
| `feat!:` / `BREAKING CHANGE:` | Breaking change |

## Submitting a pull request

1. Fork the repository and create a branch from `main`
2. Make your changes — keep PRs focused on a single concern
3. Ensure all pre-commit checks pass
4. Open a pull request using the provided template

## Translations

If you add new strings, update `custom_components/lametric_hass_local/translations/en.json`. Additional language files are welcome.

## Reporting bugs / requesting features

Please use the GitHub [issue templates](https://github.com/ElectroAttacks/lametric-hass-local/issues/new/choose).
