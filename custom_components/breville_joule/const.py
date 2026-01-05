"""Constants for the Breville Joule integration."""

from datetime import timedelta

DOMAIN = "breville_joule"

# Update coordinator
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

# API endpoints
AUTH_URL = "https://my.breville.com/oauth/token"
APPLIANCES_URL = "https://iot-api.breville.com/user/v2/user/{user_id}/appliances"
WEBSOCKET_URL = "wss://iot-api-ws.breville.com/applianceProxy"

# Device info
MANUFACTURER = "Breville"
JOULE_MODEL = "BSV600"

# Client constants
CLIENT_ID = "A2IYXGeuX1g8s049YEri6WC6hu2wlrMZ"
AUTH_REALM = "Salesforce"
AUTH_SCOPE = "openid profile email offline_access"
AUTH_AUDIENCE = "https://iden-prod.us.auth0.com/userinfo"
USER_AGENT = "Breville/827 CFNetwork/1568.200.51 Darwin/24.1.0"
