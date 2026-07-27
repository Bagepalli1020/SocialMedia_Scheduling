from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.schemas.auth import TokenData
from app.models.user import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    *,
    user_id: int,
    organization_id: int,
    role: UserRole,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "organization_id": organization_id,
        "role": role.value if isinstance(role, UserRole) else role,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        organization_id = int(payload.get("organization_id"))
        role = UserRole(payload.get("role"))
        email = payload.get("email")
        if not email:
            raise ValueError("Missing email in token")
        return TokenData(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            email=email,
        )
    except (JWTError, ValueError, TypeError) as exc:
        raise ValueError("Invalid token") from exc
