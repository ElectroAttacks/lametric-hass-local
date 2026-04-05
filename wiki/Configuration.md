# Configuration

After installation, go to **Settings → Devices & Services → Add Integration** and search for **LaMetric Local**.

## Option 1 — Manual entry

Provide the local IP address of the device and its **API key**.
You can find the API key in the LaMetric Developer portal under **My Devices** → select a device → **API key**.

## Option 2 — Cloud-assisted entry (recommended)

The cloud path retrieves the device's IP address and API key automatically via the LaMetric Cloud OAuth 2.0 flow.

1. Sign in at [developer.lametric.com](https://developer.lametric.com) and create a new application (type: **Personal** is sufficient).
2. Set the **OAuth2 Redirect URI** to match your Home Assistant instance, e.g. `https://<your-ha-url>/auth/external/callback`.
3. Copy the **Client ID** and **Client Secret** from the app settings.
4. In Home Assistant, go to **Settings → Devices & Services → Application Credentials**, click **Add Application Credential**, select **LaMetric Local**, and enter your Client ID and Client Secret.
5. Proceed with the integration setup and choose **Import from LaMetric Cloud**.

> **Note:** HACS custom integrations cannot ship bundled OAuth credentials. The credentials you create belong to your own developer account and are never shared with anyone else.

## Discovery

The integration supports automatic device discovery via:

- **Zeroconf** (`_lametric-api._tcp.local.`)
- **SSDP** (`urn:schemas-upnp-org:device:LaMetric:1`)
- **DHCP** (hostname pattern `lametric-*`)
