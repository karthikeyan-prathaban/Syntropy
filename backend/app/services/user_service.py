from app.core.crypto import decrypt_field, encrypt_field, mask_account_number, mask_email, mask_phone
from app.domain.models import User
from app.schemas.common import UserResponse


def encrypt_user_fields(mobile: str, email: str | None = None, vua: str | None = None) -> dict[str, str]:
    clean_mobile = "".join(c for c in mobile if c.isdigit())[-10:]
    vua_handle = vua or f"{clean_mobile}@onemoney"
    return {
        "mobile_enc": encrypt_field(clean_mobile),
        "email_enc": encrypt_field(email or ""),
        "vua_enc": encrypt_field(vua_handle),
    }


def user_to_response(user: User) -> UserResponse:
    mobile = decrypt_field(user.mobile_enc)
    email = decrypt_field(user.email_enc) or None
    vua = decrypt_field(user.vua_enc)
    return UserResponse(
        id=user.id,
        name=user.name,
        mobile=mask_phone(mobile),
        vua=vua,
        email=mask_email(email) if email else None,
        avatar_initials=user.avatar_initials,
        created_at=user.created_at,
    )
