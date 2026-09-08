"""Object storage for execution payloads above the inline threshold. See
docs/10-database-schema.md #10.6 (ADR-009): payloads under 64 KB are stored
inline as JSONB; above that, bytes go here and only the object key is kept.

Lives in `app.core` (a leaf module) since it is generic infra, not an engine
concern -- `app.modules.executions` reads `execution_data.kind` and calls
this to resolve `object`-kind rows.

No S3-compatible endpoint is configured in this environment (`s3_endpoint`
is unset in `.env`) -- `NullObjectStorage` is what actually runs here, and
it fails loudly rather than silently dropping a payload. `S3ObjectStorage`
is a real, from-scratch AWS SigV4 client (no `boto3`/`aioboto3` dependency
for a feature this environment cannot reach anyway) but is **not
live-verified** in this project for the same reason Docker-based
testcontainers aren't: nothing reachable to verify it against.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import get_settings


class ObjectStorageNotConfiguredError(RuntimeError):
    pass


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class NullObjectStorage:
    """Used whenever `s3_endpoint`/`s3_bucket` are unset. Raises instead of
    silently accepting a payload it cannot actually store -- a truncated
    execution is a visible, honest failure; a silently-lost one is not."""

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        raise ObjectStorageNotConfiguredError(
            "No object storage configured; payload exceeds the inline threshold "
            "and cannot be offloaded. Set S3_ENDPOINT/S3_BUCKET to enable it."
        )

    async def get(self, key: str) -> bytes:
        raise ObjectStorageNotConfiguredError("No object storage configured")

    async def delete(self, key: str) -> None:
        raise ObjectStorageNotConfiguredError("No object storage configured")


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


class S3ObjectStorage:
    """Minimal AWS SigV4 client over `httpx` for S3-compatible object
    storage (AWS S3, MinIO, R2, ...). Supports the three operations the
    execution payload path needs -- not a general-purpose S3 SDK."""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._client = httpx.AsyncClient(timeout=30.0)

    def _signing_key(self, date_stamp: str) -> bytes:
        k_date = _sign(f"AWS4{self._secret_key}".encode(), date_stamp)
        k_region = _sign(k_date, self._region)
        k_service = _sign(k_region, "s3")
        return _sign(k_service, "aws4_request")

    def _signed_headers(
        self, *, method: str, key: str, payload: bytes
    ) -> dict[str, str]:
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(payload).hexdigest()
        host = httpx.URL(self._endpoint).host
        canonical_uri = f"/{self._bucket}/{quote(key, safe='')}"
        canonical_headers = (
            f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_request = "\n".join(
            [method, canonical_uri, "", canonical_headers, signed_headers, payload_hash]
        )
        credential_scope = f"{date_stamp}/{self._region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signing_key = self._signing_key(date_stamp)
        signature = hmac.new(
            signing_key, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        authorization = (
            f"AWS4-HMAC-SHA256 Credential={self._access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization,
        }

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        headers = self._signed_headers(method="PUT", key=key, payload=data)
        headers["Content-Type"] = content_type
        url = f"{self._endpoint}/{self._bucket}/{quote(key, safe='')}"
        response = await self._client.put(url, content=data, headers=headers)
        response.raise_for_status()

    async def get(self, key: str) -> bytes:
        headers = self._signed_headers(method="GET", key=key, payload=b"")
        url = f"{self._endpoint}/{self._bucket}/{quote(key, safe='')}"
        response = await self._client.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    async def delete(self, key: str) -> None:
        headers = self._signed_headers(method="DELETE", key=key, payload=b"")
        url = f"{self._endpoint}/{self._bucket}/{quote(key, safe='')}"
        response = await self._client.delete(url, headers=headers)
        response.raise_for_status()


def build_object_storage() -> ObjectStorage:
    settings = get_settings()
    if not settings.s3_endpoint or not settings.s3_bucket or not settings.s3_access_key:
        return NullObjectStorage()
    return S3ObjectStorage(
        endpoint=settings.s3_endpoint,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key.get_secret_value(),
        secret_key=(settings.s3_secret_key or settings.s3_access_key).get_secret_value(),
    )
