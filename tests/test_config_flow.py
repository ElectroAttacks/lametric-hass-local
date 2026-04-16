"""Tests for the LaMetric config flow."""

import asyncio
from ipaddress import IPv4Address
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_MAC
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from lametric import LaMetricConnectionError

from custom_components.lametric_hass_local.config_flow import LaMetricConfigFlowHandler
from custom_components.lametric_hass_local.const import DEVICES_URL


class _FakeState:
    """Minimal device state used by config-flow tests."""

    def __init__(
        self,
        *,
        serial_number: str = "SA1234567890",
        name: str = "Kitchen LaMetric",
        mac: str = "11:22:33:44:55:66",
    ) -> None:
        self.serial_number = serial_number
        self.name = name
        self.wifi = MagicMock(mac=mac)


class _FakeDevice:
    """Minimal fake LaMetric device client for config-flow tests."""

    def __init__(self, host: str, api_key: str, state: _FakeState) -> None:
        self.host = host
        self.api_key = api_key
        self._state = state
        self.send_notification = AsyncMock()

    @property
    def state(self):
        async def _state_coro() -> _FakeState:
            return self._state

        return _state_coro()


def _make_flow(*, source: str = "user") -> LaMetricConfigFlowHandler:
    """Create a flow instance with the minimum Home Assistant mocks."""
    flow = LaMetricConfigFlowHandler()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = MagicMock(return_value="reload-task")
    flow.hass.async_create_task = MagicMock()
    object.__setattr__(flow, "context", {"source": source})
    return flow


def _make_ssdp_info(
    *,
    location: str | None = "http://192.168.1.20:8080/device",
    serial: str | None = "SA1234567890",
    friendly_name: str = "Kitchen LaMetric",
) -> SsdpServiceInfo:
    """Build an SSDP discovery payload."""
    upnp: dict[str, Any] = {ATTR_UPNP_FRIENDLY_NAME: friendly_name}
    if serial is not None:
        upnp[ATTR_UPNP_SERIAL] = serial

    return SsdpServiceInfo(
        ssdp_usn="uuid:lametric::upnp:rootdevice",
        ssdp_st="urn:schemas-upnp-org:device:LaMetric:1",
        upnp=upnp,
        ssdp_location=location,
    )


def _make_zeroconf_info(
    *,
    host: str = "lametric.local.",
    name: str = "Kitchen._lametric-api._tcp.local.",
    ip_address: str = "192.168.1.20",
) -> ZeroconfServiceInfo:
    """Build a Zeroconf discovery payload."""
    ip = IPv4Address(ip_address)
    return ZeroconfServiceInfo(
        ip_address=ip,
        ip_addresses=[ip],
        port=8080,
        hostname=host,
        type="_lametric-api._tcp.local.",
        name=name,
        properties={},
    )


def _schema_fields(result: Any) -> set[str]:
    """Extract field names from a shown form schema."""
    result_dict = cast(dict[str, Any], result)
    return {key.schema for key in result_dict["data_schema"].schema}


def test_is_matching_requires_same_discovered_host() -> None:
    """Only flows for the same discovered host should match."""
    first = _make_flow()
    second = _make_flow()

    first.discovered = True
    first.discovered_host = "192.168.1.20"
    second.discovered = True
    second.discovered_host = "192.168.1.20"

    assert first.is_matching(second) is True

    first.discovered_host = "192.168.1.21"
    assert first.is_matching(second) is False

    first.discovered = False
    assert first.is_matching(second) is False


def test_user_step_routes_directly_to_manual() -> None:
    """User initiated setup should immediately show the manual step."""
    flow = _make_flow()
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_user({CONF_HOST: "192.168.1.20"}))

    assert cast(dict[str, Any], result) == {"type": "form", "step_id": "manual"}
    mock_manual_step.assert_awaited_once_with({CONF_HOST: "192.168.1.20"})


def test_reauth_routes_directly_to_manual() -> None:
    """Reauthentication should jump straight to the manual step."""
    flow = _make_flow(source=SOURCE_REAUTH)
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_reauth({CONF_HOST: "192.168.1.20"}))

    assert cast(dict[str, Any], result) == {"type": "form", "step_id": "manual"}
    mock_manual_step.assert_awaited_once_with()


def test_dhcp_updates_existing_entry_and_aborts() -> None:
    """DHCP discovery should update the host for an already configured device."""
    flow = _make_flow()
    existing_entry = MagicMock()
    existing_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_HOST: "192.168.1.10",
    }
    existing_entry.entry_id = "entry-1"
    cast(Any, flow)._async_current_entries = MagicMock(return_value=[existing_entry])

    result = asyncio.run(
        flow.async_step_dhcp(
            DhcpServiceInfo(
                ip="192.168.1.55",
                hostname="lametric-time",
                macaddress="aa:bb:cc:dd:ee:ff",
            )
        )
    )

    result_dict = cast(dict[str, Any], result)
    assert result_dict["type"] is FlowResultType.ABORT
    assert result_dict["reason"] == "already_configured"
    cast(Any, flow.hass.config_entries.async_update_entry).assert_called_once_with(
        existing_entry,
        data={CONF_MAC: "AA:BB:CC:DD:EE:FF", CONF_HOST: "192.168.1.55"},
    )
    cast(Any, flow.hass.config_entries.async_reload).assert_called_once_with("entry-1")
    cast(Any, flow.hass.async_create_task).assert_called_once()


def test_dhcp_discovery_routes_to_manual_and_stores_host() -> None:
    """New DHCP discoveries should store host metadata and continue in manual."""
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

    assert cast(dict[str, Any], result) == {"type": "form", "step_id": "manual"}
    assert flow.discovered is True
    assert flow.discovered_host == "192.168.1.55"
    assert flow.discovered_name == "lametric-time"
    mock_manual_step.assert_awaited_once_with()


def test_ssdp_aborts_for_invalid_discovery_payload() -> None:
    """SSDP discovery should reject missing host or serial data."""
    flow = _make_flow()

    missing_host = cast(
        dict[str, Any],
        asyncio.run(flow.async_step_ssdp(_make_ssdp_info(location=None))),
    )
    missing_serial = cast(
        dict[str, Any],
        asyncio.run(flow.async_step_ssdp(_make_ssdp_info(serial=None))),
    )

    assert missing_host["type"] is FlowResultType.ABORT
    assert missing_host["reason"] == "invalid_discovery_info"
    assert missing_serial["type"] is FlowResultType.ABORT
    assert missing_serial["reason"] == "invalid_discovery_info"


def test_ssdp_aborts_for_link_local_host() -> None:
    """SSDP discovery should reject link-local addresses."""
    flow = _make_flow()

    result = cast(
        dict[str, Any],
        asyncio.run(
            flow.async_step_ssdp(
                _make_ssdp_info(location="http://169.254.10.5:8080/device")
            )
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "link_local_not_supported"


def test_ssdp_sets_discovery_context_and_routes_to_manual() -> None:
    """Valid SSDP discovery should populate flow state and continue."""
    flow = _make_flow()
    cast(Any, flow).async_set_unique_id = AsyncMock()
    cast(Any, flow)._abort_if_unique_id_configured = MagicMock()
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_ssdp(_make_ssdp_info()))

    assert cast(dict[str, Any], result) == {"type": "form", "step_id": "manual"}
    cast(Any, flow).async_set_unique_id.assert_awaited_once_with("SA1234567890")
    cast(Any, flow)._abort_if_unique_id_configured.assert_called_once_with(
        updates={CONF_HOST: "192.168.1.20"}
    )
    context = cast(dict[str, Any], flow.context)
    assert context["title_placeholders"] == {"name": "Kitchen LaMetric"}
    assert context["configuration_url"] == "https://developer.lametric.com"
    assert flow.discovered is True
    assert flow.discovered_host == "192.168.1.20"
    assert flow.discovered_name == "Kitchen LaMetric"
    mock_manual_step.assert_awaited_once_with()


def test_zeroconf_aborts_for_link_local_address() -> None:
    """Zeroconf discovery should reject link-local addresses."""
    flow = _make_flow()

    result = cast(
        dict[str, Any],
        asyncio.run(
            flow.async_step_zeroconf(_make_zeroconf_info(ip_address="169.254.10.5"))
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "link_local_address"


def test_zeroconf_sets_discovery_context_and_routes_to_manual() -> None:
    """Valid Zeroconf discovery should populate flow state and continue."""
    flow = _make_flow()
    cast(Any, flow)._async_abort_entries_match = MagicMock()
    mock_manual_step = AsyncMock(return_value={"type": "form", "step_id": "manual"})
    cast(Any, flow).async_step_manual = mock_manual_step

    result = asyncio.run(flow.async_step_zeroconf(_make_zeroconf_info()))

    assert cast(dict[str, Any], result) == {"type": "form", "step_id": "manual"}
    cast(Any, flow)._async_abort_entries_match.assert_called_once_with(
        {CONF_HOST: "192.168.1.20"}
    )
    context = cast(dict[str, Any], flow.context)
    assert context["title_placeholders"] == {"name": "Kitchen"}
    assert context["configuration_url"] == "https://developer.lametric.com"
    assert flow.discovered is True
    assert flow.discovered_host == "192.168.1.20"
    assert flow.discovered_name == "Kitchen"
    mock_manual_step.assert_awaited_once_with()


def test_manual_form_requires_host_for_normal_setup() -> None:
    """Normal setup should ask for host and API key."""
    flow = _make_flow()

    result = asyncio.run(flow.async_step_manual())
    result_dict = cast(dict[str, Any], result)

    assert result_dict["type"] is FlowResultType.FORM
    assert result_dict["step_id"] == "manual"
    assert result_dict["description_placeholders"] == {"devices_url": DEVICES_URL}
    assert _schema_fields(result) == {CONF_HOST, CONF_API_KEY}


def test_manual_form_hides_host_for_discovered_device() -> None:
    """Discovered devices should only ask for the API key."""
    flow = _make_flow()
    flow.discovered = True
    flow.discovered_host = "192.168.1.55"

    result = asyncio.run(flow.async_step_manual())

    assert _schema_fields(result) == {CONF_API_KEY}


def test_manual_form_hides_host_for_reauth() -> None:
    """Reauth should only ask for a fresh API key."""
    flow = _make_flow(source=SOURCE_REAUTH)

    result = asyncio.run(flow.async_step_manual())

    assert _schema_fields(result) == {CONF_API_KEY}


def test_manual_submit_uses_user_supplied_host() -> None:
    """Normal manual setup should validate against the submitted host."""
    flow = _make_flow()
    mock_create_entry = AsyncMock(return_value={"type": "create_entry"})
    cast(Any, flow)._async_step_create_entry = mock_create_entry

    result = asyncio.run(
        flow.async_step_manual({CONF_HOST: "192.168.1.55", CONF_API_KEY: "secret"})
    )

    assert cast(dict[str, Any], result) == {"type": "create_entry"}
    mock_create_entry.assert_awaited_once_with("192.168.1.55", "secret")


def test_manual_submit_uses_discovered_host() -> None:
    """Discovered setup should ignore host input and use the discovered host."""
    flow = _make_flow()
    flow.discovered = True
    flow.discovered_host = "192.168.1.77"
    mock_create_entry = AsyncMock(return_value={"type": "create_entry"})
    cast(Any, flow)._async_step_create_entry = mock_create_entry

    result = asyncio.run(flow.async_step_manual({CONF_API_KEY: "secret"}))

    assert cast(dict[str, Any], result) == {"type": "create_entry"}
    mock_create_entry.assert_awaited_once_with("192.168.1.77", "secret")


def test_manual_submit_uses_reauth_entry_host() -> None:
    """Reauth should validate using the existing entry host."""
    flow = _make_flow(source=SOURCE_REAUTH)
    reauth_entry = MagicMock()
    reauth_entry.data = {CONF_HOST: "192.168.1.88"}
    cast(Any, flow)._get_reauth_entry = MagicMock(return_value=reauth_entry)
    mock_create_entry = AsyncMock(return_value={"type": "create_entry"})
    cast(Any, flow)._async_step_create_entry = mock_create_entry

    result = asyncio.run(flow.async_step_manual({CONF_API_KEY: "secret"}))

    assert cast(dict[str, Any], result) == {"type": "create_entry"}
    mock_create_entry.assert_awaited_once_with("192.168.1.88", "secret")


def test_manual_submit_sets_cannot_connect_on_connection_error() -> None:
    """Connection errors should be mapped to the cannot_connect form error."""
    flow = _make_flow()
    cast(Any, flow)._async_step_create_entry = AsyncMock(
        side_effect=LaMetricConnectionError("boom")
    )

    result = cast(
        dict[str, Any],
        asyncio.run(
            flow.async_step_manual({CONF_HOST: "192.168.1.55", CONF_API_KEY: "secret"})
        ),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


def test_manual_submit_sets_unknown_on_unexpected_error() -> None:
    """Unexpected errors should be mapped to the unknown form error."""
    flow = _make_flow()
    cast(Any, flow)._async_step_create_entry = AsyncMock(
        side_effect=RuntimeError("boom")
    )

    result = cast(
        dict[str, Any],
        asyncio.run(
            flow.async_step_manual({CONF_HOST: "192.168.1.55", CONF_API_KEY: "secret"})
        ),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


def test_manual_submit_reraises_abort_flow() -> None:
    """AbortFlow should not be swallowed by the manual submit step."""
    flow = _make_flow()
    cast(Any, flow)._async_step_create_entry = AsyncMock(side_effect=AbortFlow("stop"))

    with pytest.raises(AbortFlow, match="stop"):
        asyncio.run(
            flow.async_step_manual({CONF_HOST: "192.168.1.55", CONF_API_KEY: "secret"})
        )


def test_create_entry_creates_new_config_entry() -> None:
    """Fresh setup should set the unique ID and create an entry."""
    flow = _make_flow()
    device_state = _FakeState()
    fake_device = _FakeDevice("192.168.1.55", "secret", device_state)
    cast(Any, flow).async_set_unique_id = AsyncMock()
    cast(Any, flow)._abort_if_unique_id_configured = MagicMock()
    cast(Any, flow).async_create_entry = MagicMock(
        return_value={"type": "create_entry"}
    )

    with (
        patch(
            "custom_components.lametric_hass_local.config_flow.LaMetricDevice",
            return_value=fake_device,
        ) as mock_device_cls,
        patch(
            "custom_components.lametric_hass_local.config_flow.async_get_clientsession",
            return_value="session",
        ),
    ):
        result = asyncio.run(
            cast(Any, flow)._async_step_create_entry("192.168.1.55", "secret")
        )

    assert cast(dict[str, Any], result) == {"type": "create_entry"}
    mock_device_cls.assert_called_once_with(
        host="192.168.1.55", api_key="secret", session="session"
    )
    cast(Any, flow).async_set_unique_id.assert_awaited_once_with(
        device_state.serial_number, raise_on_progress=False
    )
    cast(Any, flow)._abort_if_unique_id_configured.assert_called_once_with(
        updates={CONF_HOST: "192.168.1.55", CONF_API_KEY: "secret"}
    )
    fake_device.send_notification.assert_awaited_once()
    cast(Any, flow).async_create_entry.assert_called_once_with(
        title=device_state.name,
        data={
            CONF_API_KEY: "secret",
            CONF_HOST: "192.168.1.55",
            CONF_MAC: device_state.wifi.mac,
        },
    )


def test_create_entry_updates_existing_entry_during_reauth() -> None:
    """Reauth should update the existing entry instead of creating a new one."""
    flow = _make_flow(source=SOURCE_REAUTH)
    device_state = _FakeState()
    fake_device = _FakeDevice("192.168.1.55", "new-secret", device_state)
    reauth_entry = MagicMock()
    cast(Any, flow)._get_reauth_entry = MagicMock(return_value=reauth_entry)
    cast(Any, flow).async_update_reload_and_abort = MagicMock(
        return_value={"type": "abort", "reason": "reauth_successful"}
    )
    cast(Any, flow).async_set_unique_id = AsyncMock()
    cast(Any, flow)._abort_if_unique_id_configured = MagicMock()

    with (
        patch(
            "custom_components.lametric_hass_local.config_flow.LaMetricDevice",
            return_value=fake_device,
        ),
        patch(
            "custom_components.lametric_hass_local.config_flow.async_get_clientsession",
            return_value="session",
        ),
    ):
        result = asyncio.run(
            cast(Any, flow)._async_step_create_entry("192.168.1.55", "new-secret")
        )

    assert cast(dict[str, Any], result) == {
        "type": "abort",
        "reason": "reauth_successful",
    }
    cast(Any, flow).async_set_unique_id.assert_not_awaited()
    cast(Any, flow)._abort_if_unique_id_configured.assert_not_called()
    fake_device.send_notification.assert_awaited_once()
    cast(Any, flow).async_update_reload_and_abort.assert_called_once_with(
        reauth_entry,
        data_updates={CONF_HOST: "192.168.1.55", CONF_API_KEY: "new-secret"},
    )
