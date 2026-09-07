import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings


class SetuClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        headers = {
            "client": "bridge",
            "Content-Type": "application/json",
            "User-Agent": "curl/8.7.1",
            "Accept": "*/*",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.settings.setu_auth_url,
                headers=headers,
                json={
                    "clientID": self.settings.setu_client_id,
                    "grant_type": "client_credentials",
                    "secret": self.settings.setu_client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + 3000
        return self._access_token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "x-product-instance-id": self.settings.setu_product_instance_id,
            "Content-Type": "application/json",
            "User-Agent": "curl/8.7.1",
            "Accept": "*/*",
        }

    async def list_fips(self) -> dict[str, Any]:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.settings.setu_fiu_base_url}/v2/fips",
                headers=self._headers(token),
            )
            response.raise_for_status()
            return response.json()

    async def create_consent(self, mobile: str, redirect_url: str) -> dict[str, Any]:
        token = await self.get_token()
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=365)
        data_start = now - timedelta(days=365)

        # In Setu AA v2, passing pure 10-digit mobile automatically routes to Setu AA consent UI
        clean_mobile = "".join(c for c in (mobile or "") if c.isdigit())
        if len(clean_mobile) > 10:
            clean_mobile = clean_mobile[-10:]
        vua = clean_mobile if len(clean_mobile) == 10 else "9999999999"

        payload = {
            "vua": vua,
            "redirectUrl": redirect_url,
            "fetchType": "PERIODIC",
            "consentMode": "STORE",
            "consentTypes": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
            "fiTypes": ["DEPOSIT"],
            "purpose": {
                "code": "101",
                "text": "Personal finance management and spending insights",
                "category": {"type": "string"},
                "refUri": "https://api.rebit.org.in/aa/purpose/101.xml",
            },
            "dataRange": {
                "from": data_start.strftime("%Y-%m-%dT00:00:00.000Z"),
                "to": end.strftime("%Y-%m-%dT00:00:00.000Z"),
            },
            "frequency": {"value": 30, "unit": "MONTH"},
            "consentDuration": {"unit": "MONTH", "value": 12},
            "dataLife": {"unit": "MONTH", "value": 12},
            "context": [],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.setu_fiu_base_url}/v2/consents",
                headers=self._headers(token),
                json=payload,
            )
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Consent creation failed ({response.status_code}): {response.text}",
                    request=response.request,
                    response=response,
                )
            return response.json()

    async def get_consent(self, request_id: str) -> dict[str, Any]:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.settings.setu_fiu_base_url}/v2/consents/{request_id}",
                headers=self._headers(token),
                params={"expanded": "true"},
            )
            response.raise_for_status()
            return response.json()

    async def create_fi_session(self, consent_id: str) -> dict[str, Any]:
        token = await self.get_token()
        now = datetime.now(timezone.utc)
        data_start = now - timedelta(days=365)
        payload = {
            "consentId": consent_id,
            "format": "json",
            "dataRange": {
                "from": data_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "to": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.settings.setu_fiu_base_url}/v2/sessions",
                headers=self._headers(token),
                json=payload,
            )
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"FI session creation failed: {response.text}",
                    request=response.request,
                    response=response,
                )
            return response.json()

    async def get_fi_session(self, session_id: str) -> dict[str, Any]:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.settings.setu_fiu_base_url}/v2/sessions/{session_id}",
                headers=self._headers(token),
            )
            response.raise_for_status()
            return response.json()


setu_client = SetuClient()
