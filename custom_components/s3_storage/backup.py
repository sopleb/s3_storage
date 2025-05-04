"""Support for S3-compatible Storage backup."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from functools import wraps
import json
import logging
from typing import Any, Concatenate

import aioboto3
from botocore.exceptions import ClientError

from homeassistant.components.backup import (
    AgentBackup,
    BackupAgent,
    BackupAgentError,
    BackupNotFound,
    suggested_filename,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_ACCESS_KEY_ID,
    CONF_BUCKET_NAME,
    CONF_ENDPOINT_URL,
    CONF_SECRET_ACCESS_KEY,
    DATA_BACKUP_AGENT_LISTENERS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
METADATA_VERSION = "1"


async def async_get_backup_agents(
    hass: HomeAssistant,
) -> list[BackupAgent]:
    """Return a list of backup agents."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return [S3StorageBackupAgent(hass, entry) for entry in entries]


@callback
def async_register_backup_agents_listener(
    hass: HomeAssistant,
    *,
    listener: Callable[[], None],
    **kwargs: Any,
) -> Callable[[], None]:
    """Register a listener to be called when agents are added or removed."""
    hass.data.setdefault(DATA_BACKUP_AGENT_LISTENERS, []).append(listener)

    @callback
    def remove_listener() -> None:
        """Remove the listener."""
        hass.data[DATA_BACKUP_AGENT_LISTENERS].remove(listener)
        if not hass.data[DATA_BACKUP_AGENT_LISTENERS]:
            hass.data.pop(DATA_BACKUP_AGENT_LISTENERS)

    return remove_listener


def handle_backup_errors[_R, **P](
    func: Callable[Concatenate[S3StorageBackupAgent, P], Coroutine[Any, Any, _R]],
) -> Callable[Concatenate[S3StorageBackupAgent, P], Coroutine[Any, Any, _R]]:
    """Handle backup errors."""

    @wraps(func)
    async def wrapper(
        self: S3StorageBackupAgent, *args: P.args, **kwargs: P.kwargs
    ) -> _R:
        try:
            return await func(self, *args, **kwargs)
        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code", "")
            _LOGGER.debug(
                "Error during backup in %s: Code %s, message %s",
                func.__name__,
                error_code,
                str(err),
                exc_info=True,
            )
            raise BackupAgentError(
                f"Error during backup operation in {func.__name__}:"
                f" Code {error_code}, message: {str(err)}"
            ) from err

    return wrapper


class S3StorageBackupAgent(BackupAgent):
    """S3-compatible storage backup agent."""

    domain = DOMAIN

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize the S3 storage backup agent."""
        super().__init__()
        self._entry = entry
        self.name = entry.title
        self.unique_id = entry.entry_id
        self._session = aioboto3.Session()

    async def _get_client(self):
        """Get S3 client."""
        return await self._session.client(
            "s3",
            endpoint_url=self._entry.data.get(CONF_ENDPOINT_URL),
            aws_access_key_id=self._entry.data[CONF_ACCESS_KEY_ID],
            aws_secret_access_key=self._entry.data[CONF_SECRET_ACCESS_KEY],
        ).__aenter__()

    @handle_backup_errors
    async def async_download_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> AsyncIterator[bytes]:
        """Download a backup file."""
        key = await self._find_object_by_backup_id(backup_id)
        if key is None:
            raise BackupNotFound(f"Backup {backup_id} not found")

        client = await self._get_client()
        try:
            response = await client.get_object(
                Bucket=self._entry.data[CONF_BUCKET_NAME],
                Key=key
            )
            async with response["Body"] as stream:
                while chunk := await stream.read(8192):
                    yield chunk
        finally:
            await client.__aexit__(None, None, None)

    @handle_backup_errors
    async def async_upload_backup(
        self,
        *,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
        backup: AgentBackup,
        **kwargs: Any,
    ) -> None:
        """Upload a backup."""
        metadata = {
            "metadata_version": METADATA_VERSION,
            "backup_id": backup.backup_id,
            "backup_metadata": json.dumps(backup.as_dict()),
        }

        filename = suggested_filename(backup)
        client = await self._get_client()
        try:
            data = b""
            async for chunk in await open_stream():
                data += chunk

            await client.put_object(
                Bucket=self._entry.data[CONF_BUCKET_NAME],
                Key=filename,
                Body=data,
                Metadata=metadata,
            )
        finally:
            await client.__aexit__(None, None, None)

    @handle_backup_errors
    async def async_delete_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete a backup file."""
        key = await self._find_object_by_backup_id(backup_id)
        if key is None:
            raise BackupNotFound(f"Backup {backup_id} not found")

        client = await self._get_client()
        try:
            await client.delete_object(
                Bucket=self._entry.data[CONF_BUCKET_NAME],
                Key=key
            )
        finally:
            await client.__aexit__(None, None, None)

    @handle_backup_errors
    async def async_list_backups(self, **kwargs: Any) -> list[AgentBackup]:
        """List backups."""
        backups: list[AgentBackup] = []
        client = await self._get_client()
        try:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._entry.data[CONF_BUCKET_NAME]):
                for obj in page.get("Contents", []):
                    response = await client.head_object(
                        Bucket=self._entry.data[CONF_BUCKET_NAME],
                        Key=obj["Key"]
                    )
                    metadata = response.get("Metadata", {})
                    if metadata.get("metadata_version") == METADATA_VERSION:
                        backups.append(
                            AgentBackup.from_dict(json.loads(metadata["backup_metadata"]))
                        )
        finally:
            await client.__aexit__(None, None, None)

        return backups

    @handle_backup_errors
    async def async_get_backup(
        self,
        backup_id: str,
        **kwargs: Any,
    ) -> AgentBackup:
        """Return a backup."""
        key = await self._find_object_by_backup_id(backup_id)
        if key is None:
            raise BackupNotFound(f"Backup {backup_id} not found")

        client = await self._get_client()
        try:
            response = await client.head_object(
                Bucket=self._entry.data[CONF_BUCKET_NAME],
                Key=key
            )
            metadata = response.get("Metadata", {})
            return AgentBackup.from_dict(json.loads(metadata["backup_metadata"]))
        finally:
            await client.__aexit__(None, None, None)

    async def _find_object_by_backup_id(self, backup_id: str) -> str | None:
        """Find an object by backup id."""
        client = await self._get_client()
        try:
            paginator = client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self._entry.data[CONF_BUCKET_NAME]):
                for obj in page.get("Contents", []):
                    response = await client.head_object(
                        Bucket=self._entry.data[CONF_BUCKET_NAME],
                        Key=obj["Key"]
                    )
                    metadata = response.get("Metadata", {})
                    if (
                        metadata.get("metadata_version") == METADATA_VERSION
                        and backup_id == metadata.get("backup_id")
                    ):
                        return obj["Key"]
        finally:
            await client.__aexit__(None, None, None)
        return None