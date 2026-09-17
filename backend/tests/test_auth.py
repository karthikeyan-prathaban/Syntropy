import pytest
from sqlalchemy import select

from app.core.crypto import email_hash
from app.domain.models import User

SIGNUP = {
    "name": "Asha Rao",
    "email": "asha@example.com",
    "mobile": "9812345678",
    "password": "correct-horse-battery",
}


async def test_signup_stores_indexed_hash_not_plaintext(client, db):
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201

    user = (await db.execute(select(User))).scalar_one()
    assert user.email_hash == email_hash(SIGNUP["email"])
    assert SIGNUP["email"] not in (user.email_enc or "")
    assert user.email_enc.startswith("enc:")


async def test_login_is_a_single_indexed_lookup(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]


async def test_email_lookup_is_case_insensitive(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login", json={"email": "ASHA@Example.com", "password": SIGNUP["password"]}
    )
    assert response.status_code == 200


async def test_duplicate_signup_rejected(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 400


async def test_wrong_password_rejected(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_refresh_rotates_and_invalidates_the_old_token(client):
    signup = (await client.post("/api/v1/auth/signup", json=SIGNUP)).json()
    original = signup["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != original

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert reused.status_code == 401
    assert "reuse" in reused.json()["detail"].lower()


async def test_refresh_reuse_revokes_the_whole_family(client):
    signup = (await client.post("/api/v1/auth/signup", json=SIGNUP)).json()
    original = signup["refresh_token"]
    rotated = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    ).json()["refresh_token"]

    # Replaying the stolen token must also kill the legitimate successor.
    await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated})
    assert response.status_code == 401


async def test_me_requires_authentication(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_me_returns_masked_pii(auth_client):
    body = (await auth_client.get("/api/v1/auth/me")).json()
    assert "•" in body["mobile"]
    assert body["email"] and "•" in body["email"]


@pytest.mark.parametrize(
    "path", ["/api/v1/dashboard", "/api/v1/transactions", "/api/v1/analytics/cashflow"]
)
async def test_protected_endpoints_reject_anonymous(client, path):
    assert (await client.get(path)).status_code == 401
