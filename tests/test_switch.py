"""Tests for the LaMetric switch platform."""

import asyncio
from ipaddress import IPv4Address
from unittest.mock import AsyncMock, MagicMock

from awesomeversion import AwesomeVersion
from lametric import DeviceModels, DeviceModes
from lametric.device_states import (  # type: ignore[attr-defined]
    BrightnessMode,
    DeviceAudioState,
    DeviceBluetoothState,
    DeviceDisplayState,
    DeviceState,
    DeviceWiFiState,
    DisplayType,
    IntRange,
)

from custom_components.lametric_hass_local.switch import (
    SWITCHES,
    LaMetricSwitchEntity,
)


def _bluetooth_description():
    return next(s for s in SWITCHES if s.key == "bluetooth_active")


def test_switch_is_on_reflects_bluetooth_active(
    coordinator: MagicMock, device_state: DeviceState
) -> None:
    """is_on mirrors the bluetooth.active field of the coordinator data."""
    desc = _bluetooth_description()
    entity = LaMetricSwitchEntity(coordinator=coordinator, description=desc)

    assert entity.is_on is device_state.bluetooth.active


def test_switch_available_when_bluetooth_hardware_present(
    coordinator: MagicMock,
) -> None:
    """Switch availability matches the bluetooth.available field."""
    desc = _bluetooth_description()
    entity = LaMetricSwitchEntity(coordinator=coordinator, description=desc)

    assert entity.available is True


def test_switch_not_created_when_bluetooth_unavailable(
    device_state: DeviceState,
) -> None:
    """Bluetooth switch is unavailable when bluetooth.available is False."""
    desc = _bluetooth_description()
    unavailable_state = DeviceState(
        cloud_id=1,
        name="LaMetric TIME",
        serial_number="SA0000000001",
        os_version=AwesomeVersion("2.3.0"),
        model=DeviceModels.TIME,
        mode=DeviceModes.AUTO,
        audio=DeviceAudioState(available=True, volume=50),
        bluetooth=DeviceBluetoothState(available=False),  # no Bluetooth hardware
        display=DeviceDisplayState(
            on=True,
            width=37,
            height=8,
            type=DisplayType.MONOCHROME,
            brightness=50,
            brightness_mode=BrightnessMode.AUTO,
            brightness_range=IntRange(min=0, max=100),
            brightness_limit=IntRange(min=0, max=100),
        ),
        wifi=DeviceWiFiState(
            available=True,
            active=True,
            encryption="WPA2",
            netmask=IPv4Address("255.255.255.0"),
            ip_address_mode="dhcp",
            ipv4=IPv4Address("192.168.1.100"),
            mac="11:22:33:44:55:66",
            signal_strength=75,
            ssid="TestNet",
        ),
    )

    assert not desc.available(unavailable_state)


def test_display_on_switch_unavailable_when_display_on_is_none(
    device_state: DeviceState,
) -> None:
    """display_on switch is unavailable when display.on is None."""
    desc = next(s for s in SWITCHES if s.key == "display_on")
    none_display_state = DeviceState(
        cloud_id=1,
        name="LaMetric TIME",
        serial_number="SA0000000001",
        os_version=AwesomeVersion("2.3.0"),
        model=DeviceModels.TIME,
        mode=DeviceModes.AUTO,
        audio=DeviceAudioState(available=True, volume=50),
        bluetooth=DeviceBluetoothState(available=True),
        display=DeviceDisplayState(
            on=None,
            width=37,
            height=8,
            type=DisplayType.MONOCHROME,
            brightness=50,
            brightness_mode=BrightnessMode.AUTO,
            brightness_range=IntRange(min=0, max=100),
            brightness_limit=IntRange(min=0, max=100),
        ),
        wifi=DeviceWiFiState(
            available=True,
            active=True,
            encryption="WPA2",
            netmask=IPv4Address("255.255.255.0"),
            ip_address_mode="dhcp",
            ipv4=IPv4Address("192.168.1.100"),
            mac="11:22:33:44:55:66",
            signal_strength=75,
            ssid="TestNet",
        ),
    )

    assert not desc.available(none_display_state)


def test_turn_on_calls_set_bluetooth_true(coordinator: MagicMock) -> None:
    """async_turn_on calls set_state with active=True on the device."""
    desc = _bluetooth_description()
    coordinator.device.set_bluetooth = AsyncMock()

    entity = LaMetricSwitchEntity(coordinator=coordinator, description=desc)

    asyncio.run(entity.async_turn_on())

    coordinator.device.set_bluetooth.assert_awaited_once_with(active=True)


def test_turn_off_calls_set_bluetooth_false(coordinator: MagicMock) -> None:
    """async_turn_off calls set_state with active=False on the device."""
    desc = _bluetooth_description()
    coordinator.device.set_bluetooth = AsyncMock()

    entity = LaMetricSwitchEntity(coordinator=coordinator, description=desc)

    asyncio.run(entity.async_turn_off())

    coordinator.device.set_bluetooth.assert_awaited_once_with(active=False)


def test_setup_entry_adds_available_switches(coordinator: MagicMock) -> None:
    """async_setup_entry adds switches for descriptions where available() is True."""
    import asyncio
    from unittest.mock import MagicMock

    from custom_components.lametric_hass_local.switch import async_setup_entry

    config_entry = MagicMock()
    config_entry.runtime_data = coordinator

    collected: list = []
    asyncio.run(async_setup_entry(MagicMock(), config_entry, collected.extend))  # type: ignore[arg-type]
    # bluetooth is available in the default fixture
    assert len(collected) >= 1
