"""Tests for the LaMetric update platform."""

from dataclasses import replace as dc_replace
from unittest.mock import MagicMock

from awesomeversion import AwesomeVersion
from lametric.device_states import DeviceSoftwareUpdate, DeviceState

from custom_components.lametric_hass_local.update import LaMetricUpdate


def test_installed_version_returns_os_version(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """installed_version returns the string form of os_version."""
    entity = LaMetricUpdate(coordinator)
    assert entity.installed_version == str(device_state.os_version)


def test_latest_version_equals_installed_when_no_update(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """When no update info is present, latest_version equals installed."""
    state_no_update = dc_replace(device_state, update=None)
    coordinator.data = state_no_update
    entity = LaMetricUpdate(coordinator)

    assert entity.latest_version == str(state_no_update.os_version)


def test_latest_version_from_update_field(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """When an update is available, latest_version returns update.version."""
    state_with_update = dc_replace(
        device_state,
        update=DeviceSoftwareUpdate(version=AwesomeVersion("2.4.0")),
    )
    coordinator.data = state_with_update
    entity = LaMetricUpdate(coordinator)

    assert entity.latest_version == "2.4.0"


def test_unique_id_contains_serial(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """Unique ID of the update entity ends with '-update'."""
    entity = LaMetricUpdate(coordinator)
    assert entity.unique_id == f"{device_state.serial_number}-update"


def test_setup_entry_skips_old_os_version() -> None:
    """Devices older than 2.3.0 do not get an update entity."""
    import asyncio
    from unittest.mock import MagicMock

    from awesomeversion import AwesomeVersion

    from custom_components.lametric_hass_local.update import async_setup_entry
    from tests.conftest import _build_device_state

    config_entry = MagicMock()
    coordinator = MagicMock()
    coordinator.data = _build_device_state(os_version=AwesomeVersion("2.2.0"))
    config_entry.runtime_data = coordinator

    added: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, added.append))  # type: ignore[arg-type]
    assert added == []


def test_setup_entry_adds_entity_for_current_os() -> None:
    """Devices running 2.3.0+ get an update entity."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.update import async_setup_entry
    from tests.conftest import _build_device_state

    config_entry = MagicMock()
    coordinator = MagicMock()
    coordinator.data = _build_device_state()
    config_entry.runtime_data = coordinator

    added: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, added.append))  # type: ignore[arg-type]
    assert len(added) == 1
