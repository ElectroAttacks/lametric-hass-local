"""Config flow for discovering and connecting LaMetric devices."""

from collections.abc import Mapping
from ipaddress import ip_address
from logging import Logger
from typing import Any, Self, override

import voluptuous as vol
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_DEVICE, CONF_HOST, CONF_MAC
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_SERIAL,
    SsdpServiceInfo,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.util.network import is_link_local
from lametric import (
    BuiltinSound,
    CloudDevice,
    DeviceModels,
    IconType,
    LaMetricCloud,
    LaMetricConnectionError,
    LaMetricDevice,
    Notification,
    NotificationData,
    NotificationPriority,
    NotificationSound,
    SimpleFrame,
)
from yarl import URL

from .const import DOMAIN, LOGGER

DEVICES_URL = "https://developer.lametric.com/user/devices"


class LaMetricConfigFlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle setup, discovery, and reauthentication for LaMetric devices."""

    DOMAIN = DOMAIN
    VERSION = 1

    cloud_devices: dict[str, CloudDevice]
    discovered_host: str
    discovered_name: str
    discovered_serial: str | None
    discovered: bool = False

    @property
    def logger(self) -> Logger:
        """Return the integration logger for OAuth flow internals."""
        return LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Provide OAuth2 scopes required by the cloud API."""
        return {"scope": "basic devices_read"}

    @override
    def is_matching(self, other_flow: Self) -> bool:
        """Match concurrent flows that target the same discovered device."""
        return bool(
            self.discovered
            and other_flow.discovered
            and getattr(self, "discovered_host", None)
            and self.discovered_host == getattr(other_flow, "discovered_host", None)
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle device discovery coming from DHCP."""

        mac = format_mac(discovery_info.macaddress)

        # Check if we've already configured a device with this MAC address
        for entry in self._async_current_entries():
            if format_mac(entry.data.get(CONF_MAC)) == mac:
                self.hass.config_entries.async_update_entry(
                    entry, data=entry.data | {CONF_HOST: discovery_info.ip}
                )

                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )

                return self.async_abort(reason="already_configured")

        # New device discovered via DHCP
        self.discovered_host = discovery_info.ip
        self.discovered_name = discovery_info.hostname
        self.discovered_serial = None
        self.discovered = True

        return await self.async_step_choice_manual_or_cloud()

    async def async_step_ssdp(
        self, discovery_info: SsdpServiceInfo
    ) -> ConfigFlowResult:
        """Handle device discovery coming from SSDP."""

        url = URL(discovery_info.ssdp_location or "")

        serial = discovery_info.upnp.get(ATTR_UPNP_SERIAL)

        if url.host is None or not serial:
            return self.async_abort(reason="invalid_discovery_info")

        if is_link_local(ip_address(url.host)):
            return self.async_abort(reason="link_local_not_supported")

        await self.async_set_unique_id(serial)

        self._abort_if_unique_id_configured(updates={CONF_HOST: url.host})
        self.context.update(
            {
                "title_placeholders": {
                    "name": discovery_info.upnp.get(
                        ATTR_UPNP_FRIENDLY_NAME, "LaMetric TIME"
                    ),
                },
                "configuration_url": "https://developer.lametric.com",
            }
        )

        self.discovered = True
        self.discovered_host = str(url.host)
        self.discovered_name = str(
            discovery_info.upnp.get(ATTR_UPNP_FRIENDLY_NAME, "LaMetric TIME")
        )
        self.discovered_serial = serial

        return await self.async_step_choice_manual_or_cloud()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle device discovery coming from Zeroconf."""

        if is_link_local(discovery_info.ip_address):
            return self.async_abort(reason="link_local_address")

        self._async_abort_entries_match({CONF_HOST: discovery_info.host})

        self.context.update(
            {
                "title_placeholders": {
                    "name": discovery_info.name.removesuffix(
                        "._lametric-api._tcp.local."
                    ),
                },
                "configuration_url": "https://developer.lametric.com",
            }
        )

        self.discovered = True
        self.discovered_host = discovery_info.host
        self.discovered_name = discovery_info.name.removesuffix(
            "._lametric-api._tcp.local."
        )
        self.discovered_serial = None

        return await self.async_step_choice_manual_or_cloud()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start the flow from the user-initiated entry point."""

        return await self.async_step_choice_manual_or_cloud()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start the flow for reauthentication."""

        return await self.async_step_choice_manual_or_cloud()

    async def async_step_choice_manual_or_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the menu to choose manual setup or cloud OAuth."""
        return self.async_show_menu(
            step_id="choice_manual_or_cloud",
            menu_options=["pick_implementation", "manual"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the manual entry form and validate host/API key on submit."""

        validation_errors: dict[str, str] = {}

        if user_input is not None:
            if self.discovered:
                host = self.discovered_host
            elif self.source == SOURCE_REAUTH:
                host = self._get_reauth_entry().data[CONF_HOST]
            else:
                host = user_input[CONF_HOST]

            try:
                return await self._async_step_create_entry(
                    host, user_input[CONF_API_KEY]
                )

            except AbortFlow:
                raise

            except LaMetricConnectionError as error:
                LOGGER.error(
                    "Connection error while validating LaMetric device at %s: %s",
                    host,
                    error,
                )

                validation_errors["base"] = "cannot_connect"

            except Exception:
                LOGGER.exception(
                    "Unexpected error validating LaMetric device at %s", host
                )

                validation_errors["base"] = "unknown"

        schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                )
            }
        )

        if not self.discovered and self.source != SOURCE_REAUTH:
            schema = schema.extend({vol.Required(CONF_HOST): TextSelector()})

        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            description_placeholders={"devices_url": DEVICES_URL},
            errors=validation_errors,
        )

    async def async_step_cloud(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Load cloud devices after OAuth2 authentication completes."""

        cloud = LaMetricCloud(
            token=data["token"]["access_token"],
            session=async_get_clientsession(self.hass),
        )

        self.cloud_devices = {
            device.serial_number: device
            for device in sorted(await cloud.devices, key=lambda d: d.name)
        }

        if not self.cloud_devices:
            return self.async_abort(reason="no_cloud_devices")

        return await self.async_step_cloud_device_selection()

    async def async_step_cloud_device_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a cloud device and validate connectivity."""

        if self.discovered:
            user_input = {CONF_DEVICE: self.discovered_serial}

        elif self.source == SOURCE_REAUTH:
            reauth_id = self._get_reauth_entry().unique_id

            if reauth_id not in self.cloud_devices:
                return self.async_abort(reason="device_not_in_cloud")

            user_input = {CONF_DEVICE: reauth_id}

        elif len(self.cloud_devices) == 1:
            user_input = {
                CONF_DEVICE: list(self.cloud_devices.values())[0].serial_number
            }

        validation_errors: dict[str, str] = {}

        if user_input is not None:
            device = self.cloud_devices[user_input[CONF_DEVICE]]

            try:
                return await self._async_step_create_entry(
                    str(device.ipv4_internal), device.api_key
                )

            except AbortFlow:
                raise

            except LaMetricConnectionError as error:
                LOGGER.error(
                    "Connection error while validating LaMetric device at %s: %s",
                    device.ipv4_internal,
                    error,
                )

                validation_errors["base"] = "cannot_connect"

            except Exception:
                LOGGER.exception(
                    "Unexpected error validating LaMetric device at %s",
                    device.ipv4_internal,
                )

                validation_errors["base"] = "unknown"

        return self.async_show_form(
            step_id="cloud_device_selection",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE): SelectSelector(
                        SelectSelectorConfig(
                            mode=SelectSelectorMode.DROPDOWN,
                            options=[
                                SelectOptionDict(
                                    value=device.serial_number,
                                    label=device.name,
                                )
                                for device in self.cloud_devices.values()
                            ],
                        )
                    )
                }
            ),
            errors=validation_errors,
        )

    async def _async_step_create_entry(
        self, host: str, api_key: str
    ) -> ConfigFlowResult:
        """Connect to the device, send a welcome notification, and persist the entry.

        Sends a notification on the device to confirm connectivity before
        creating or updating the config entry. On reauth, reloads the existing
        entry instead of creating a new one.
        """

        device = LaMetricDevice(
            host=host, api_key=api_key, session=async_get_clientsession(self.hass)
        )

        state = await device.state

        if self.source != SOURCE_REAUTH:
            await self.async_set_unique_id(state.serial_number, raise_on_progress=False)

            self._abort_if_unique_id_configured(
                updates={CONF_HOST: device.host, CONF_API_KEY: device.api_key}
            )

        notify_sound: BuiltinSound | None = None

        if state.model != DeviceModels.SKY:
            notify_sound = BuiltinSound(id=NotificationSound.WIN)

        await device.send_notification(
            notification=Notification(
                priority=NotificationPriority.CRITICAL,
                icon_type=IconType.INFO,
                model=NotificationData(
                    cycles=2,
                    frames=[
                        SimpleFrame(text="Connected to Home Assistant!", icon=7956)
                    ],
                    sound=notify_sound,
                ),
            )
        )

        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates={CONF_HOST: device.host, CONF_API_KEY: device.api_key},
            )

        return self.async_create_entry(
            title=state.name,
            data={
                CONF_API_KEY: device.api_key,
                CONF_HOST: device.host,
                CONF_MAC: state.wifi.mac,
            },
        )

    async_oauth_create_entry = async_step_cloud
