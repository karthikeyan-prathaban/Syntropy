import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import email_hash
from app.core.deps import require_demo_routes
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    issue_refresh_token,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.domain.models import User
from app.schemas.common import (
    EmailVerifyRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.user_service import encrypt_user_fields, user_to_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TTL_SECONDS = 30 * 60
VERIFY_TTL_SECONDS = 24 * 60 * 60


async def _find_by_email(db: AsyncSession, email: str) -> User | None:
    """Indexed lookup on the email hash. The previous full-table scan with per-row
    decryption made login O(n) in the number of users."""
    result = await db.execute(select(User).where(User.email_hash == email_hash(email)))
    return result.scalar_one_or_none()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, request: Request, db: AsyncSession = Depends(get_db)):
    if await _find_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    initials = "".join(w[0].upper() for w in payload.name.split()[:2]) or "NV"
    user = User(
        name=payload.name,
        email_hash=email_hash(payload.email),
        hashed_password=hash_password(payload.password),
        avatar_initials=initials,
        **encrypt_user_fields(payload.mobile, payload.email),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    refresh = await issue_refresh_token(db, user.id, user_agent=request.headers.get("user-agent"))
    await db.commit()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=refresh,
        user=user_to_response(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _find_by_email(db, payload.email)
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    refresh = await issue_refresh_token(db, user.id, user_agent=request.headers.get("user-agent"))
    await db.commit()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=refresh,
        user=user_to_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, new_refresh = await rotate_refresh_token(
        db, payload.refresh_token, user_agent=request.headers.get("user-agent")
    )
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=new_refresh,
        user=user_to_response(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await revoke_all_refresh_tokens(db, user.id)
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user_to_response(user)


@router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    user = await _find_by_email(db, payload.email)
    # Always the same response, so this endpoint cannot be used to enumerate accounts.
    response = {"status": "sent", "detail": "If the account exists, a reset link has been sent"}
    if not user:
        return response

    token = secrets.token_urlsafe(32)
    redis = await get_redis()
    if redis is None:
        logger.warning("Password reset requested but Redis is unavailable")
        return response
    await redis.setex(f"pwreset:{token}", RESET_TTL_SECONDS, str(user.id))

    if not get_settings().is_production:
        response["debug_token"] = token
    return response


@router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="Password reset is temporarily unavailable")
    user_id = await redis.get(f"pwreset:{payload.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(payload.new_password)
    # A password change invalidates every existing session.
    await revoke_all_refresh_tokens(db, user.id)
    await db.commit()
    await redis.delete(f"pwreset:{payload.token}")
    return {"status": "updated"}


@router.post("/verify-email/request")
async def request_email_verification(user: User = Depends(get_current_user)):
    if user.email_verified:
        return {"status": "already_verified"}
    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="Verification is temporarily unavailable")
    token = secrets.token_urlsafe(32)
    await redis.setex(f"emailverify:{token}", VERIFY_TTL_SECONDS, str(user.id))
    payload = {"status": "sent"}
    if not get_settings().is_production:
        payload["debug_token"] = token
    return payload


@router.post("/verify-email/confirm")
async def confirm_email_verification(payload: EmailVerifyRequest, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="Verification is temporarily unavailable")
    user_id = await redis.get(f"emailverify:{payload.token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user = (await db.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.email_verified = True
    await db.commit()
    await redis.delete(f"emailverify:{payload.token}")
    return {"status": "verified"}


@router.post("/demo-login", response_model=TokenResponse, dependencies=[Depends(require_demo_routes)])
async def demo_login(
    request: Request,
    name: str = "Demo User",
    mobile: str = "9876543210",
    db: AsyncSession = Depends(get_db),
):
    demo_email = f"demo+{secrets.token_hex(6)}@novaa.local"
    user = User(
        name=name,
        avatar_initials="DU",
        is_demo=True,
        email_hash=email_hash(demo_email),
        **encrypt_user_fields(mobile, demo_email),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    refresh = await issue_refresh_token(db, user.id, user_agent=request.headers.get("user-agent"))
    await db.commit()
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=refresh,
        user=user_to_response(user),
    )
