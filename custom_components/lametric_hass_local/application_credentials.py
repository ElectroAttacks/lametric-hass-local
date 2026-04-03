"""Application credentials helpers for the LaMetric integration."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the OAuth2 authorization server for LaMetric."""
    return AuthorizationServer(
        authorize_url="https://developer.lametric.com/api/v2/oauth2/authorize",
        token_url="https://developer.lametric.com/api/v2/oauth2/token",
    )
