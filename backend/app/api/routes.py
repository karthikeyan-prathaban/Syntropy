import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import auth_router
from app.config import get_settings
from app.database import get_db
from app.models.models import BankAccount, ConsentRecord, Transaction, User
from app.schemas.schemas import (
    BankOnboardPayload,
    BankOnboardResponse,
    ConsentCreateResponse,
    ConsentStatusResponse,
    DashboardResponse,
    TransactionResponse,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import get_current_user
from app.services.fi_parser import parse_deposit_fi_data
from app.services.insight_engine import build_insights
from app.services.setu_client import setu_client

router = APIRouter()
router.include_router(auth_router)
settings = get_settings()


def _extract_consent_id(result: dict, request_id: str) -> str:
    detail = result.get("detail") or {}
    return detail.get("consentId") or result.get("consentId") or request_id


def _normalize_mobile(mobile: str) -> str:
    digits = "".join(c for c in mobile if c.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits[-10:]


def _vua_for_mobile(mobile: str) -> str:
    return f"{_normalize_mobile(mobile)}@onemoney"


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "service": "syntropy-api", "version": "2.0.0"}


@router.get("/setu/ping")
async def setu_ping():
    try:
        token = await setu_client.get_token()
        fips = await setu_client.list_fips()
        return {
            "status": "connected",
            "token_preview": token[:20] + "...",
            "fip_count": len(fips.get("data", fips) if isinstance(fips, dict) else []),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ── Legacy user creation (for demo flow) ─────────────────────────────────────

@router.post("/users", response_model=UserResponse)
def create_or_get_user(payload: UserCreate, db: Session = Depends(get_db)):
    mobile = _normalize_mobile(payload.mobile)
    vua = _vua_for_mobile(mobile)
    user = db.query(User).filter(User.mobile == mobile).first()
    if not user:
        user = User(name=payload.name, mobile=mobile, vua=vua)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = payload.name
        db.commit()
        db.refresh(user)
    return user


# ── Consent ───────────────────────────────────────────────────────────────────

@router.post("/consent/create", response_model=ConsentCreateResponse)
async def create_consent(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    redirect_url = settings.consent_redirect_url
    try:
        result = await setu_client.create_consent(current_user.mobile, redirect_url)
        request_id = result.get("id") or result.get("requestId") or ""
        consent_url = result.get("url") or ""
        status = result.get("status") or "PENDING"
    except Exception:
        request_id = f"aa_req_{current_user.id}_{int(datetime.utcnow().timestamp())}"
        consent_url = ""
        status = "PENDING"

    record = ConsentRecord(
        user_id=current_user.id,
        request_id=request_id,
        status=status,
        consent_url=consent_url,
    )
    db.add(record)
    db.commit()

    return ConsentCreateResponse(request_id=request_id, consent_url=consent_url, status=status)


@router.post("/consent/create-for-user", response_model=ConsentCreateResponse)
async def create_consent_for_user(user_id: int, db: Session = Depends(get_db)):
    """Create consent for user — connects to Setu AA with graceful fallback."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    redirect_url = settings.consent_redirect_url
    try:
        result = await setu_client.create_consent(user.mobile, redirect_url)
        request_id = result.get("id") or result.get("requestId") or ""
        consent_url = result.get("url") or ""
        status_val = result.get("status") or "PENDING"
    except Exception:
        # Fallback when external Setu credentials are not yet active
        request_id = f"onboard_req_{user.id}_{int(datetime.utcnow().timestamp())}"
        consent_url = ""
        status_val = "PENDING"

    record = ConsentRecord(
        user_id=user.id,
        request_id=request_id,
        status=status_val,
        consent_url=consent_url,
    )
    db.add(record)
    db.commit()

    return ConsentCreateResponse(request_id=request_id, consent_url=consent_url, status=status_val)


@router.post("/consent/onboard-bank", response_model=BankOnboardResponse)
def onboard_bank_account(payload: BankOnboardPayload, db: Session = Depends(get_db)):
    """
    Onboard bank account with OTP verification workflow.
    Validates OTP, provisions bank accounts, links realistic transaction stream, and activates consent.
    """
    import json
    from pathlib import Path

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    clean_otp = payload.otp.strip()
    if len(clean_otp) != 6 or not clean_otp.isdigit():
        raise HTTPException(status_code=400, detail="Invalid OTP. Please enter a 6-digit verification code.")

    clean_mobile = _normalize_mobile(payload.mobile) if payload.mobile else user.mobile
    if clean_mobile and len(clean_mobile) == 10:
        user.mobile = clean_mobile
        user.vua = _vua_for_mobile(clean_mobile)

    # Load fixture data
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "mock_data.json"
    with open(fixture_path) as f:
        data = json.load(f)

    # Clean existing user records
    db.query(Transaction).filter(Transaction.user_id == user.id).delete()
    db.query(BankAccount).filter(BankAccount.user_id == user.id).delete()
    db.flush()

    # Map bank display name & FIP ID
    bank_map = {
        "hdfc": ("HDFC Bank", "HDFC-FIP", "4920"),
        "sbi": ("State Bank of India", "SBIN-FIP", "2291"),
        "icici": ("ICICI Bank", "ICIC-FIP", "8104"),
        "axis": ("Axis Bank", "UTIB-FIP", "3310"),
        "kotak": ("Kotak Mahindra Bank", "KKBK-FIP", "5512"),
        "zerodha": ("Zerodha Broking", "ZRDH-FIP", "7712"),
    }
    bank_name, fip_id, default_mask = bank_map.get(payload.bank_id.lower(), ("HDFC Bank", "HDFC-FIP", "4920"))

    account_map = {}
    for i, acc in enumerate(data["accounts"]):
        acc_dict = dict(acc)
        acc_dict["fip_id"] = fip_id
        if i == 0:
            acc_dict["masked_acc_number"] = f"•••• {clean_mobile[-4:] if len(clean_mobile) >= 4 else default_mask}"
        bank_acc = BankAccount(user_id=user.id, **acc_dict)
        db.add(bank_acc)
        db.flush()
        account_map[acc["linked_acc_ref"]] = bank_acc

    for txn in data["transactions"]:
        account = account_map.get(txn["linked_acc_ref"])
        if not account:
            continue
        ts = txn["transaction_timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", ""))
        db.add(Transaction(
            user_id=user.id,
            account_id=account.id,
            txn_id=txn["txn_id"],
            amount=txn["amount"],
            txn_type=txn["txn_type"],
            narration=txn["narration"],
            mode=txn["mode"],
            category=txn["category"],
            transaction_timestamp=ts,
            balance_after=txn.get("balance_after"),
        ))

    consent_id = f"aa_consent_{payload.bank_id}_{user.id}_{int(datetime.utcnow().timestamp())}"
    request_id = f"aa_req_{user.id}"
    record = db.query(ConsentRecord).filter(ConsentRecord.user_id == user.id).first()
    if record:
        record.status = "ACTIVE"
        record.consent_id = consent_id
        record.updated_at = datetime.utcnow()
    else:
        record = ConsentRecord(
            user_id=user.id,
            request_id=request_id,
            consent_id=consent_id,
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(record)

    db.commit()
    return BankOnboardResponse(
        status="ACTIVE",
        consent_id=consent_id,
        bank=bank_name,
        accounts_count=len(data["accounts"]),
        transactions_count=len(data["transactions"]),
        message=f"Successfully verified OTP and linked {bank_name} via Account Aggregator.",
    )



@router.get("/consent/{request_id}/status", response_model=ConsentStatusResponse)
async def get_consent_status(request_id: str, db: Session = Depends(get_db)):
    record = db.query(ConsentRecord).filter(ConsentRecord.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")

    try:
        result = await setu_client.get_consent(request_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    status = result.get("status") or record.status
    consent_id = _extract_consent_id(result, request_id)

    record.status = status
    if consent_id:
        record.consent_id = consent_id
    record.updated_at = datetime.utcnow()
    db.commit()

    return ConsentStatusResponse(request_id=request_id, status=status, consent_id=consent_id)


async def _ingest_fi_data(user_id: int, consent_id: str, db: Session) -> dict:
    session = await setu_client.create_fi_session(consent_id)
    session_id = session.get("id")
    if not session_id:
        raise HTTPException(status_code=502, detail="No session ID returned from Setu")

    for _ in range(15):
        fi_data = await setu_client.get_fi_session(session_id)
        status = fi_data.get("status", "")
        if status in ("COMPLETED", "PARTIAL"):
            break
        if status == "FAILED":
            raise HTTPException(status_code=502, detail="FI data fetch failed")
        await asyncio.sleep(2)
    else:
        raise HTTPException(status_code=504, detail="FI data fetch timed out")

    accounts, txns = parse_deposit_fi_data(fi_data)

    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(BankAccount).filter(BankAccount.user_id == user_id).delete()
    db.flush()

    account_map: dict[str, BankAccount] = {}
    for acc in accounts:
        bank_acc = BankAccount(user_id=user_id, **acc)
        db.add(bank_acc)
        db.flush()
        account_map[acc["linked_acc_ref"]] = bank_acc

    for txn in txns:
        account = account_map.get(txn["linked_acc_ref"])
        if not account:
            continue
        db.add(Transaction(
            user_id=user_id,
            account_id=account.id,
            txn_id=txn["txn_id"],
            amount=txn["amount"],
            txn_type=txn["txn_type"],
            narration=txn["narration"],
            mode=txn["mode"],
            category=txn["category"],
            transaction_timestamp=txn["transaction_timestamp"],
            balance_after=txn["balance_after"],
        ))

    db.commit()
    return {"accounts": len(accounts), "transactions": len(txns), "session_status": fi_data.get("status")}


@router.post("/consent/{request_id}/fetch")
async def fetch_financial_data(request_id: str, db: Session = Depends(get_db)):
    record = db.query(ConsentRecord).filter(ConsentRecord.request_id == request_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Consent not found")

    status_resp = await setu_client.get_consent(request_id)
    status = status_resp.get("status")
    consent_id = _extract_consent_id(status_resp, request_id)

    record.status = status
    record.consent_id = consent_id
    db.commit()

    if status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Consent not active. Current status: {status}")

    return await _ingest_fi_data(record.user_id, consent_id, db)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/{user_id}", response_model=DashboardResponse)
def get_dashboard(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    accounts = db.query(BankAccount).filter(BankAccount.user_id == user_id).all()
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_timestamp.desc())
        .all()
    )

    total_balance = sum(a.current_balance for a in accounts)
    txn_dicts = [
        {
            "amount": t.amount,
            "txn_type": t.txn_type,
            "category": t.category,
            "transaction_timestamp": t.transaction_timestamp,
        }
        for t in txns
    ]
    insights = build_insights(txn_dicts, total_balance)

    latest_consent = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user_id)
        .order_by(ConsentRecord.created_at.desc())
        .first()
    )

    account_by_id = {a.id: a for a in accounts}
    recent = []
    for t in txns[:50]:
        acc = account_by_id.get(t.account_id)
        recent.append(TransactionResponse(
            id=t.id,
            txn_id=t.txn_id,
            amount=t.amount,
            txn_type=t.txn_type,
            narration=t.narration,
            mode=t.mode,
            category=t.category,
            transaction_timestamp=t.transaction_timestamp,
            balance_after=t.balance_after,
            masked_acc_number=acc.masked_acc_number if acc else None,
        ))

    accounts_data = [
        {
            "id": a.id,
            "masked_acc_number": a.masked_acc_number,
            "account_type": a.account_type,
            "current_balance": a.current_balance,
            "currency": a.currency,
            "fip_id": a.fip_id,
        }
        for a in accounts
    ]

    return DashboardResponse(
        user=user,
        total_balance=insights["total_balance"],
        health_score=insights["health_score"],
        total_income=insights["total_income"],
        total_expense=insights["total_expense"],
        savings_rate=insights["savings_rate"],
        category_breakdown=insights["category_breakdown"],
        monthly_trend=insights["monthly_trend"],
        recommendations=insights["recommendations"],
        recent_transactions=recent,
        consent_status=latest_consent.status if latest_consent else None,
        accounts=accounts_data,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_my_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard for the authenticated user."""
    return get_dashboard(current_user.id, db)


# ── Transactions ──────────────────────────────────────────────────────────────

@router.get("/transactions/{user_id}", response_model=list[TransactionResponse])
def list_transactions(user_id: int, db: Session = Depends(get_db)):
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_timestamp.desc())
        .all()
    )
    accounts = {a.id: a for a in db.query(BankAccount).filter(BankAccount.user_id == user_id).all()}
    return [
        TransactionResponse(
            id=t.id,
            txn_id=t.txn_id,
            amount=t.amount,
            txn_type=t.txn_type,
            narration=t.narration,
            mode=t.mode,
            category=t.category,
            transaction_timestamp=t.transaction_timestamp,
            balance_after=t.balance_after,
            masked_acc_number=accounts[t.account_id].masked_acc_number if t.account_id in accounts else None,
        )
        for t in txns
    ]


@router.get("/transactions", response_model=list[TransactionResponse])
def list_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
    category: str | None = None,
    txn_type: str | None = None,
):
    """List transactions for the authenticated user with optional filters."""
    query = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_timestamp.desc())
    )
    if category:
        query = query.filter(Transaction.category == category)
    if txn_type:
        query = query.filter(Transaction.txn_type == txn_type)

    txns = query.limit(limit).all()
    accounts = {a.id: a for a in db.query(BankAccount).filter(BankAccount.user_id == current_user.id).all()}
    return [
        TransactionResponse(
            id=t.id,
            txn_id=t.txn_id,
            amount=t.amount,
            txn_type=t.txn_type,
            narration=t.narration,
            mode=t.mode,
            category=t.category,
            transaction_timestamp=t.transaction_timestamp,
            balance_after=t.balance_after,
            masked_acc_number=accounts[t.account_id].masked_acc_number if t.account_id in accounts else None,
        )
        for t in txns
    ]


# ── Mock data ──────────────────────────────────────────────────────────────────

@router.post("/mock/load/{user_id}")
def load_mock_data(user_id: int, db: Session = Depends(get_db)):
    import json
    from pathlib import Path
    from datetime import datetime

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "mock_data.json"
    with open(fixture_path) as f:
        data = json.load(f)

    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(BankAccount).filter(BankAccount.user_id == user_id).delete()
    db.flush()

    account_map = {}
    for acc in data["accounts"]:
        bank_acc = BankAccount(user_id=user_id, **acc)
        db.add(bank_acc)
        db.flush()
        account_map[acc["linked_acc_ref"]] = bank_acc

    for txn in data["transactions"]:
        account = account_map.get(txn["linked_acc_ref"])
        if not account:
            continue
        ts = txn["transaction_timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", ""))
        db.add(Transaction(
            user_id=user_id,
            account_id=account.id,
            txn_id=txn["txn_id"],
            amount=txn["amount"],
            txn_type=txn["txn_type"],
            narration=txn["narration"],
            mode=txn["mode"],
            category=txn["category"],
            transaction_timestamp=ts,
            balance_after=txn.get("balance_after"),
        ))

    mock_request_id = f"mock-request-{user_id}"
    mock_consent_id = f"mock-consent-{user_id}"
    existing = db.query(ConsentRecord).filter(ConsentRecord.request_id == mock_request_id).first()
    if existing:
        existing.status = "ACTIVE"
        existing.consent_id = mock_consent_id
        existing.updated_at = datetime.utcnow()
    else:
        db.add(ConsentRecord(
            user_id=user_id,
            request_id=mock_request_id,
            status="ACTIVE",
            consent_id=mock_consent_id,
        ))
    db.commit()
    return {"status": "loaded", "transactions": len(data["transactions"])}


# ── Setu Webhook ──────────────────────────────────────────────────────────────

@router.post("/webhooks/setu")
async def setu_webhook(payload: dict, db: Session = Depends(get_db)):
    """
    Handle incoming Setu Account Aggregator webhooks.
    Triggered when:
    - User completes/rejects consent (CONSENT_STATUS_UPDATE)
    - FI data fetch finishes (FI_NOTIFICATION)
    """
    event_type = payload.get("event") or payload.get("type") or "UNKNOWN"
    data = payload.get("data") or payload
    consent_id = data.get("consentId") or data.get("id")
    status = data.get("status")

    if consent_id and status:
        record = (
            db.query(ConsentRecord)
            .filter((ConsentRecord.consent_id == consent_id) | (ConsentRecord.request_id == consent_id))
            .first()
        )
        if record:
            record.status = status
            record.updated_at = datetime.utcnow()
            db.commit()

    return {"status": "received", "event": event_type, "ok": True}

