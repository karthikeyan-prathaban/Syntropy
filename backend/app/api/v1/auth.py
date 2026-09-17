from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.db.session import get_db
from app.domain.models import User
from app.schemas.common import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services.user_service import encrypt_user_fields, user_to_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    from app.core.crypto import decrypt_field

    enc = encrypt_user_fields(payload.mobile, payload.email)
    result = await db.execute(select(User))
    for u in result.scalars():
        if decrypt_field(u.email_enc) == payload.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    initials = "".join(w[0].upper() for w in payload.name.split()[:2]) or "NV"
    user = User(
        name=payload.name,
        hashed_password=hash_password(payload.password),
        avatar_initials=initials,
        **enc,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_response(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.core.crypto import decrypt_field

    result = await db.execute(select(User))
    user = None
    for u in result.scalars():
        if decrypt_field(u.email_enc) == payload.email:
            user = u
            break
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_response(user))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user_to_response(user)


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(name: str = "Demo User", mobile: str = "9876543210", db: AsyncSession = Depends(get_db)):
    enc = encrypt_user_fields(mobile)
    user = User(name=name, avatar_initials="DU", **enc)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=user_to_response(user))
