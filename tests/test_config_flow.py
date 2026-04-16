"""Tests for the manual-only LaMetric config flow."""

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from lametric import DeviceModels, NotificationSound

from custom_components.lametric_hass_local.config_flow import LaMetricConfigFlowHandler
from tests.conftest import _build_device_state


def _make_flow() -> LaMetricConfigFlowHandler:
    """Create a flow instance with a minimal mocked hass object."""
    flow = LaMetricConfigFlowHandler()
    flow.hass = MagicMock()
    return flow


def test_user_step_routes_directly_to_manual() -> None:
    """User initiated setup should skip any cloud menu and show the manual step."""
    flow = _make_flow()
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_user())

    assert result == {"type": "form", "step_id": "manual"}
    mock_manual_step.assert_awaited_once_with(None)


def test_reauth_routes_directly_to_manual() -> None:
    """Reauthentication should prompt for the API key directly."""
    flow = _make_flow()
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_reauth({}))

    assert result == {"type": "form", "step_id": "manual"}
    mock_manual_step.assert_awaited_once_with()


def test_dhcp_discovery_routes_to_manual_and_stores_host() -> None:
    """DHCP discovery should pre-fill the host and continue with manual auth."""
    flow = _make_flow()
    cast(Any, flow)._async_current_entries = MagicMock(return_value=[])
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(
        flow.async_step_dhcp(
            DhcpServiceInfo(
                ip="192.168.1.55",
                hostname="lametric-time",
                macaddress="AA:BB:CC:DD:EE:FF",
            )
        )
    )

    assert result == {"type": "form", "step_id": "manual"}
    assert flow.discovered is True
    assert flow.discovered_host == "192.168.1.55"
    assert flow.discovered_name == "lametric-time"
    mock_manual_step.assert_awaited_once_with()


def test_manual_form_requires_host_for_normal_setup() -> None:
    """Normal setup should ask for both host and API key."""
    flow = _make_flow()
    flow.context = {"source": "user"}
    flow.discovered = False

    result = asyncio.run(flow.async_step_manual())

    assert result["type"] == "form"
    schema = result["data_schema"]
    assert schema is not None
    fields = {key.schema for key in schema.schema}
    assert CONF_HOST in fields
    assert CONF_API_KEY in fields


def test_manual_form_hides_host_for_discovered_device() -> None:
    """Discovered devices should only require the API key."""
    flow = _make_flow()
    flow.context = {"source": "user"}
    flow.discovered = True
    flow.discovered_host = "192.168.1.55"

    result = asyncio.run(flow.async_step_manual())

    assert result["type"] == "form"
    schema = result["data_schema"]
    assert schema is not None
    fields = {key.schema for key in schema.schema}
    assert CONF_HOST not in fields
    assert CONF_API_KEY in fields


def test_create_entry_sends_welcome_sound_for_sky() -> None:
    """SKY devices should use the same welcome-notification sound as other models."""
    from unittest.mock import patch

    flow = _make_flow()
    flow.context = {"source": "user"}

    sky_state = _build_device_state(model=DeviceModels.SKY)
    fake_device = MagicMock()
    fake_device.host = "192.168.1.55"
    fake_device.api_key = "secret"
    fake_device.send_notification = AsyncMock()

    async def state_coro() -> Any:
        return sky_state

    type(fake_device).state = property(lambda self: state_coro())

    cast(Any, flow).async_set_unique_id = AsyncMock()
    cast(Any, flow)._abort_if_unique_id_configured = MagicMock()
    cast(Any, flow).async_create_entry = MagicMock(
        return_value={"type": "create_entry"}
    )

    with (
        patch(
            "custom_components.lametric_hass_local.config_flow.LaMetricDevice",
            return_value=fake_device,
        ),
        patch(
            "custom_components.lametric_hass_local.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ):
        result = asyncio.run(flow._async_step_create_entry("192.168.1.55", "secret"))

    assert result == {"type": "create_entry"}
    fake_device.send_notification.assert_awaited_once()

    notification = fake_device.send_notification.await_args.kwargs["notification"]
    assert notification.model.sound is not None
    assert notification.model.sound.id == NotificationSound.WIN
