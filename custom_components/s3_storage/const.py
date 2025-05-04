"""Constants for the S3 Storage integration."""

from collections.abc import Callable
from typing import Final

from homeassistant.util.hass_dict import HassKey

DOMAIN: Final = "s3_storage"

CONF_ACCESS_KEY_ID: Final = "storage_account_key"
CONF_SECRET_ACCESS_KEY: Final = "account_name"
CONF_BUCKET_NAME: Final = "container_name"
CONF_ENDPOINT_URL: Final = "endpoint_url"

DATA_BACKUP_AGENT_LISTENERS: HassKey[list[Callable[[], None]]] = HassKey(
    f"{DOMAIN}.backup_agent_listeners"
)
