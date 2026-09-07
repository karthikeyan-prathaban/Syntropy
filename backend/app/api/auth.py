"""
Authentication API routes for Syntropy.
Handles user signup, login, and profile endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_mobile(mobile: str) -> str:
    digits = "".join(c for c in mobile if c.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits[-10:]


def _make_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


@auth_router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    # Check email uniqueness
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    mobile = _normalize_mobile(payload.mobile)
    vua = f"{mobile}@onemoney"

    # Check mobile uniqueness
    existing = db.query(User).filter(User.mobile == mobile).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        mobile=mobile,
        vua=vua,
        hashed_password=hash_password(payload.password),
        avatar_initials=_make_initials(payload.name),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return current_user


@auth_router.post("/demo-login", response_model=TokenResponse)
def demo_login(name: str, mobile: str, db: Session = Depends(get_db)):
    """Quick demo login — creates guest user if not exists (no password required)."""
    digits = "".join(c for c in mobile if c.isdigit())
    digits = digits[-10:]
    vua = f"{digits}@onemoney"

    user = db.query(User).filter(User.mobile == digits).first()
    if not user:
        user = User(
            name=name.strip(),
            mobile=digits,
            vua=vua,
            avatar_initials=_make_initials(name),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name.strip()
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
