from pathlib import Path

from sqlalchemy import func, select

from app.domain.models import Merchant, RecurringSeries, Transaction

FIXTURES = Path(__file__).parent / "fixtures" / "statements"


async def _upload(client, filename: str):
    data = (FIXTURES / filename).read_bytes()
    return await client.post(
        "/api/v1/statements/upload",
        files={"file": (filename, data, "text/csv")},
    )


async def test_supported_banks_are_advertised(client):
    body = (await client.get("/api/v1/statements/supported-banks")).json()
    codes = {b["code"] for b in body["banks"]}
    assert {"HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "GENERIC"} <= codes


async def test_upload_requires_authentication(client):
    response = await _upload(client, "hdfc_sample.csv")
    assert response.status_code == 401


async def test_upload_detects_the_bank_and_imports_rows(auth_client, db):
    response = await _upload(auth_client, "hdfc_sample.csv")
    assert response.status_code == 202
    body = response.json()
    assert body["detected_bank"] == "HDFC"

    status = (await auth_client.get(f"/api/v1/statements/{body['id']}/status")).json()
    assert status["status"] == "completed", status.get("error")
    assert status["rows_imported"] == 6

    assert await db.scalar(select(func.count()).select_from(Transaction)) == 6


async def test_reuploading_the_same_file_adds_no_rows(auth_client, db):
    first = (await _upload(auth_client, "icici_sample.csv")).json()
    second = (await _upload(auth_client, "icici_sample.csv")).json()

    first_status = (await auth_client.get(f"/api/v1/statements/{first['id']}/status")).json()
    second_status = (await auth_client.get(f"/api/v1/statements/{second['id']}/status")).json()

    assert first_status["rows_imported"] == 5
    assert second_status["rows_imported"] == 0
    assert second_status["rows_duplicate"] == 5
    assert await db.scalar(select(func.count()).select_from(Transaction)) == 5


async def test_upload_triggers_merchant_enrichment(auth_client, db):
    await _upload(auth_client, "hdfc_sample.csv")

    merchants = {m.display_name for m in (await db.execute(select(Merchant))).scalars()}
    assert "Swiggy" in merchants
    assert "Amazon" in merchants
    # A bank rail prefix must never end up as a merchant.
    assert "Upi" not in merchants and "Neft" not in merchants


async def test_unsupported_file_type_is_rejected(auth_client):
    response = await auth_client.post(
        "/api/v1/statements/upload",
        files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
    )
    assert response.status_code == 415


async def test_empty_file_is_rejected(auth_client):
    response = await auth_client.post(
        "/api/v1/statements/upload", files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert response.status_code == 400


async def test_unreadable_statement_reports_a_useful_error(auth_client):
    response = await auth_client.post(
        "/api/v1/statements/upload",
        files={"file": ("junk.csv", b"nothing,useful\nhere,either", "text/csv")},
    )
    assert response.status_code == 422


async def test_uploads_are_listed_per_user(auth_client):
    await _upload(auth_client, "sbi_sample.csv")
    listing = (await auth_client.get("/api/v1/statements")).json()
    assert len(listing) == 1
    assert listing[0]["detected_bank"] == "SBI"


async def test_another_users_upload_is_not_visible(client):
    first = (
        await client.post(
            "/api/v1/auth/signup",
            json={"name": "Amit", "email": "a@x.com", "mobile": "9800000001", "password": "password-one"},
        )
    ).json()
    second = (
        await client.post(
            "/api/v1/auth/signup",
            json={"name": "Bela", "email": "b@x.com", "mobile": "9800000002", "password": "password-two"},
        )
    ).json()

    client.headers["Authorization"] = f"Bearer {first['access_token']}"
    upload = (await _upload(client, "axis_sample.csv")).json()

    client.headers["Authorization"] = f"Bearer {second['access_token']}"
    assert (await client.get(f"/api/v1/statements/{upload['id']}/status")).status_code == 404
    assert (await client.get("/api/v1/statements")).json() == []


async def test_analytics_reflect_the_uploaded_statement(auth_client):
    await _upload(auth_client, "axis_sample.csv")

    close = (await auth_client.get("/api/v1/analytics/monthly/2026-03")).json()
    assert close["income"] == 110000.0
    # The SIP is an investment, so it must not appear as spending.
    assert close["investments"] == 10000.0
    assert close["expense"] == 3384.0

    subscriptions = (await auth_client.get("/api/v1/analytics/subscriptions")).json()
    assert "monthly_cost" in subscriptions


async def test_transfer_between_two_uploaded_accounts_is_excluded(auth_client, db):
    """HDFC shows a 25,000 debit to self; ICICI shows the matching credit."""
    await _upload(auth_client, "hdfc_sample.csv")
    await _upload(auth_client, "icici_sample.csv")

    transfers = (
        await db.execute(select(Transaction).where(Transaction.is_transfer.is_(True)))
    ).scalars().all()
    assert len(transfers) == 2
    assert {t.txn_type for t in transfers} == {"DEBIT", "CREDIT"}

    close = (await auth_client.get("/api/v1/analytics/monthly/2026-03")).json()
    assert close["transfers_excluded"] == 25000.0


async def test_recurring_series_are_persisted(auth_client, db):
    await _upload(auth_client, "hdfc_sample.csv")
    # One statement month is not enough evidence for a series.
    count = await db.scalar(select(func.count()).select_from(RecurringSeries))
    assert count == 0


async def test_deleting_an_upload_keeps_the_transactions(auth_client, db):
    upload = (await _upload(auth_client, "kotak_sample.csv")).json()
    before = await db.scalar(select(func.count()).select_from(Transaction))

    assert (await auth_client.delete(f"/api/v1/statements/{upload['id']}")).status_code == 204
    assert await db.scalar(select(func.count()).select_from(Transaction)) == before
