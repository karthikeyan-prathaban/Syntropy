from pathlib import Path

from sqlalchemy import func, select

from app.domain.models import BankAccount, Merchant, StatementUpload, Transaction

FIXTURES = Path(__file__).parent / "fixtures" / "statements"


async def test_purge_removes_every_trace_of_financial_data(auth_client, db):
    await auth_client.post(
        "/api/v1/statements/upload",
        files={"file": ("hdfc_sample.csv", (FIXTURES / "hdfc_sample.csv").read_bytes(), "text/csv")},
    )
    assert await db.scalar(select(func.count()).select_from(Transaction)) > 0

    response = await auth_client.delete("/api/v1/me/data")
    assert response.status_code == 200
    assert response.json()["status"] == "purged"

    for model in (Transaction, BankAccount, Merchant, StatementUpload):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_purge_requires_authentication(client):
    assert (await client.delete("/api/v1/me/data")).status_code == 401


async def test_purge_leaves_other_users_alone(client):
    first = (
        await client.post(
            "/api/v1/auth/signup",
            json={"name": "Amit", "email": "p1@x.com", "mobile": "9800000011", "password": "password-one"},
        )
    ).json()
    second = (
        await client.post(
            "/api/v1/auth/signup",
            json={"name": "Bela", "email": "p2@x.com", "mobile": "9800000012", "password": "password-two"},
        )
    ).json()

    data = (FIXTURES / "sbi_sample.csv").read_bytes()
    for token in (first["access_token"], second["access_token"]):
        client.headers["Authorization"] = f"Bearer {token}"
        await client.post(
            "/api/v1/statements/upload", files={"file": ("sbi_sample.csv", data, "text/csv")}
        )

    client.headers["Authorization"] = f"Bearer {first['access_token']}"
    await client.delete("/api/v1/me/data")

    client.headers["Authorization"] = f"Bearer {second['access_token']}"
    remaining = (await client.get("/api/v1/dashboard")).json()
    assert len(remaining["accounts"]) == 1
