from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.crypto import decrypt_field, encrypt_field


class StatementStorage:
    """Stores uploaded statements. S3-compatible in production, disk locally.

    Statement files contain raw account numbers and full narration, so the local
    backend encrypts at rest and the S3 backend relies on SSE plus a lifecycle rule.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def _key(self, user_id: int, filename: str) -> str:
        suffix = Path(filename).suffix[:10]
        return f"statements/{user_id}/{uuid.uuid4().hex}{suffix}"

    async def put(self, user_id: int, filename: str, data: bytes) -> str:
        key = self._key(user_id, filename)
        if self.settings.storage_backend == "s3":
            await asyncio.to_thread(self._s3_put, key, data)
        else:
            await asyncio.to_thread(self._local_put, key, data)
        return key

    async def get(self, key: str) -> bytes:
        if self.settings.storage_backend == "s3":
            return await asyncio.to_thread(self._s3_get, key)
        return await asyncio.to_thread(self._local_get, key)

    async def delete(self, key: str) -> None:
        if self.settings.storage_backend == "s3":
            await asyncio.to_thread(self._s3_delete, key)
        else:
            await asyncio.to_thread(self._local_delete, key)

    # --- local ------------------------------------------------------------
    def _local_path(self, key: str) -> Path:
        return Path(self.settings.storage_local_path) / key

    def _local_put(self, key: str, data: bytes) -> None:
        path = self._local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encrypt_field(data.decode("latin-1")))
        os.chmod(path, 0o600)

    def _local_get(self, key: str) -> bytes:
        return decrypt_field(self._local_path(key).read_text()).encode("latin-1")

    def _local_delete(self, key: str) -> None:
        self._local_path(key).unlink(missing_ok=True)

    # --- s3 ---------------------------------------------------------------
    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url or None,
            region_name=self.settings.s3_region,
            aws_access_key_id=self.settings.s3_access_key_id or None,
            aws_secret_access_key=self.settings.s3_secret_access_key or None,
        )

    def _s3_put(self, key: str, data: bytes) -> None:
        self._client().put_object(
            Bucket=self.settings.s3_bucket,
            Key=key,
            Body=data,
            ServerSideEncryption="AES256",
        )

    def _s3_get(self, key: str) -> bytes:
        return self._client().get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"].read()

    def _s3_delete(self, key: str) -> None:
        self._client().delete_object(Bucket=self.settings.s3_bucket, Key=key)


storage = StatementStorage()
