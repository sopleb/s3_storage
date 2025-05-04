"""Config flow for S3-compatible storage integration."""

from collections.abc import Mapping
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError, ParamValidationError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_REGION

from .const import (
    CONF_BUCKET_NAME,
    CONF_ACCESS_KEY_ID,
    CONF_SECRET_ACCESS_KEY,
    CONF_ENDPOINT_URL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class S3StorageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for S3-compatible storage."""

    async def validate_config(
        self, config: dict[str, Any]
    ) -> dict[str, str]:
        """Validate the configuration."""
        errors: dict[str, str] = {}

        try:
            session = boto3.Session(
                aws_access_key_id=config[CONF_ACCESS_KEY_ID],
                aws_secret_access_key=config[CONF_SECRET_ACCESS_KEY],
            )

            s3_client = session.client(
                "s3",
                endpoint_url=config.get(CONF_ENDPOINT_URL),
                region_name=config.get(CONF_REGION),
            )

            # Test if we can access the bucket
            s3_client.head_bucket(Bucket=config[CONF_BUCKET_NAME])

        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            if error_code in ["403", "InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                errors["base"] = "invalid_auth"
            elif error_code in ["404", "NoSuchBucket"]:
                errors["base"] = "cannot_connect"
            else:
                _LOGGER.exception("Unexpected S3 error")
                errors["base"] = "unknown"
        except ParamValidationError:
            errors["base"] = "invalid_config"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown exception occurred")
            errors["base"] = "unknown"

        return errors

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """User step for S3 Storage."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_ACCESS_KEY_ID: user_input[CONF_ACCESS_KEY_ID],
                    CONF_BUCKET_NAME: user_input[CONF_BUCKET_NAME],
                }
            )

            errors = await self.validate_config(user_input)

            if not errors:
                return self.async_create_entry(
                    title=f"{user_input.get(CONF_ENDPOINT_URL, 'AWS S3')}/{user_input[CONF_BUCKET_NAME]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_KEY_ID): str,
                    vol.Required(CONF_SECRET_ACCESS_KEY): str,
                    vol.Required(CONF_BUCKET_NAME, default="home-assistant-backups"): str,
                    vol.Optional(CONF_ENDPOINT_URL): str,
                    vol.Optional(CONF_REGION): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            config = {
                **reauth_entry.data,
                CONF_ACCESS_KEY_ID: user_input[CONF_ACCESS_KEY_ID],
                CONF_SECRET_ACCESS_KEY: user_input[CONF_SECRET_ACCESS_KEY],
            }
            errors = await self.validate_config(config)
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data=config,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_KEY_ID): str,
                    vol.Required(CONF_SECRET_ACCESS_KEY): str,
                }
            ),
            errors=errors,
        )