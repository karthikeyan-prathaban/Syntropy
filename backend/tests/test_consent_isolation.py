"""The consent endpoints previously looked up records by request_id alone, which let
any authenticated user read and re-fetch another user's consent."""

import pytest
from sqlalchemy import select

from app.domain.models import ConsentRecord, User


async def _make_user(client, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"name": "User", "email": email, "mobile": "9800000000", "password": "hunter2-hunter2"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


async def test_consent_status_requires_authentication(client):
    response = await client.get("/api/v1/consent/req-123/status")
    assert response.status_code == 401


async def test_consent_fetch_requires_authentication(client):
    response = await client.post("/api/v1/consent/req-123/fetch")
    assert response.status_code == 401


@pytest.mark.parametrize("method,suffix", [("get", "status"), ("post", "fetch")])
async def test_other_users_consent_is_not_reachable(client, db, method, suffix):
    victim_token = await _make_user(client, "victim@example.com")
    attacker_token = await _make_user(client, "attacker@example.com")

    victim = (
        await db.execute(select(User).where(User.email_hash.is_not(None)).order_by(User.id))
    ).scalars().first()
    db.add(
        ConsentRecord(
            user_id=victim.id,
            request_id="victim-request",
            consent_id="victim-consent",
            status="ACTIVE",
        )
    )
    await db.commit()

    # The owner can see it.
    owner = await getattr(client, method)(
        f"/api/v1/consent/victim-request/{suffix}",
        headers={"Authorization": f"Bearer {victim_token}"},
    )
    assert owner.status_code != 404

    # Anyone else gets a 404, not the record.
    intruder = await getattr(client, method)(
        f"/api/v1/consent/victim-request/{suffix}",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert intruder.status_code == 404


async def test_revoke_scoped_to_owner(client, db):
    victim_token = await _make_user(client, "v2@example.com")
    attacker_token = await _make_user(client, "a2@example.com")
    victim = (await db.execute(select(User).order_by(User.id))).scalars().first()
    db.add(
        ConsentRecord(
            user_id=victim.id, request_id="r2", consent_id="c2", status="ACTIVE"
        )
    )
    await db.commit()

    response = await client.post(
        "/api/v1/consent/c2/revoke", headers={"Authorization": f"Bearer {attacker_token}"}
    )
    assert response.status_code == 404
    assert victim_token  # the victim's consent remains untouched

    record = (
        await db.execute(select(ConsentRecord).where(ConsentRecord.consent_id == "c2"))
    ).scalar_one()
    await db.refresh(record)
    assert record.status == "ACTIVE"
