"""Shared fixtures for the LaMetric integration test suite."""

import sys
from ipaddress import IPv4Address
from unittest.mock import AsyncMock, MagicMock

import pytest

# Create minimal mocks for missing homeassistant modules before any imports
# These are needed because the pip-installable homeassistant package is incomplete
if "homeassistant.exceptions" not in sys.modules:
    sys.modules["homeassistant.exceptions"] = MagicMock()
if "homeassistant.components" not in sys.modules:
    sys.modules["homeassistant.components"] = MagicMock()
if "homeassistant.components.notify" not in sys.modules:
    sys.modules["homeassistant.components.notify"] = MagicMock()
if "homeassistant.components.notify.legacy" not in sys.modules:
    sys.modules["homeassistant.components.notify.legacy"] = MagicMock()
if "homeassistant.generated" not in sys.modules:
    sys.modules["homeassistant.generated"] = MagicMock()
if "homeassistant.generated.entity_platforms" not in sys.modules:
    sys.modules["homeassistant.generated.entity_platforms"] = MagicMock()

from awesomeversion import AwesomeVersion
from lametric import DeviceModels, DeviceModes
from lametric.const import BrightnessMode, DisplayType
from lametric.device_states import (  # type: ignore[attr-defined]
    DeviceAudioState,
    DeviceBluetoothState,
    DeviceDisplayState,
    DeviceState,
    DeviceWiFiState,
    IntRange,
)

_DEFAULT_OS_VERSION = AwesomeVersion("2.3.0")
_DEFAULT_MODEL = DeviceModels.TIME


def _build_device_state(
    *,
    os_version: AwesomeVersion = _DEFAULT_OS_VERSION,
    model: DeviceModels = _DEFAULT_MODEL,
) -> DeviceState:
    """Build a DeviceState with optional overrides – usable outside fixtures."""
    return DeviceState(
        cloud_id=1,
        name="LaMetric TIME",
        serial_number="SA1234567890",
        os_version=os_version,
        model=model,
        mode=DeviceModes.AUTO,
        audio=DeviceAudioState(available=True, volume=50),
        bluetooth=DeviceBluetoothState(
            available=True,
            active=True,
            mac="AA:BB:CC:DD:EE:FF",
        ),
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
            signal_strength=80,
            ssid="TestNet",
        ),
    )


@pytest.fixture
def device_state() -> DeviceState:
    """Return a realistic DeviceState for a LaMetric TIME device."""
    return _build_device_state()


@pytest.fixture
def mock_hass() -> MagicMock:
    """Return a minimal HomeAssistant mock suitable for entity tests."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def coordinator(device_state: DeviceState) -> MagicMock:
    """Return a mocked LaMetricCoordinator pre-populated with device_state."""
    mock = MagicMock()
    mock.data = device_state
    mock.apps = {}
    mock.device.host = "192.168.1.100"
    mock.async_request_refresh = AsyncMock()
    return mock
