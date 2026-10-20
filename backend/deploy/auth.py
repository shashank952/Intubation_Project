import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {"admin": 3, "doctor": 2, "viewer": 1}

SESSION_EXPIRED = "session_expired"
SESSION_REVOKED = "session_revoked"
RELOGIN_REQUIRED = "relogin_required"


def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    absolute_cap = now + timedelta(hours=settings.session_absolute_timeout_hours)
    if absolute_cap < expire:
        expire = absolute_cap
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid token"},
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def token_expiry(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=settings.jwt_expire_minutes)
    absolute_cap = now + timedelta(hours=settings.session_absolute_timeout_hours)
    return min(expiry, absolute_cap)


async def create_session(email: str) -> str:
    sid = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    await get_db().sessions.insert_one({
        "sid": sid,
        "email": email,
        "created_at": now,
        "last_activity_at": now,
        "revoked_at": None,
    })
    return sid


async def revoke_session(sid: str) -> None:
    await get_db().sessions.update_one(
        {"sid": sid, "revoked_at": None},
        {"$set": {"revoked_at": datetime.now(timezone.utc)}},
    )


def session_error(session: Optional[dict], now: datetime) -> Optional[str]:
    """None when the session is usable, else the rejection code."""
    if session is None:
        return SESSION_EXPIRED
    if session.get("revoked_at"):
        return SESSION_REVOKED
    idle_seconds = settings.session_idle_timeout_minutes * 60
    if (now - _as_utc(session["last_activity_at"])).total_seconds() > idle_seconds:
        return SESSION_EXPIRED
    absolute_seconds = settings.session_absolute_timeout_hours * 3600
    if (now - _as_utc(session["created_at"])).total_seconds() > absolute_seconds:
        return SESSION_EXPIRED
    return None


def should_touch(session: dict, now: datetime) -> bool:
    elapsed = (now - _as_utc(session["last_activity_at"])).total_seconds()
    return elapsed >= settings.session_touch_interval_seconds


def _session_error_response(code: str) -> HTTPException:
    messages = {
        RELOGIN_REQUIRED: "Session predates session tracking. Sign in again.",
        SESSION_REVOKED: "Session was signed out. Sign in again.",
        SESSION_EXPIRED: "Session expired due to inactivity. Sign in again.",
    }
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": messages.get(code, "Session invalid")},
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Not authenticated"},
        )
    payload = decode_token(credentials.credentials)
    email = payload.get("sub")
    sid = payload.get("sid")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid token"},
        )
    if not sid:
        raise _session_error_response(RELOGIN_REQUIRED)

    db = get_db()
    now = datetime.now(timezone.utc)
    session = await db.sessions.find_one({"sid": sid})
    error = session_error(session, now)
    if error:
        raise _session_error_response(error)
    if should_touch(session, now):
        await db.sessions.update_one(
            {"sid": sid, "revoked_at": None},
            {"$set": {"last_activity_at": now}},
        )

    # ponytail: read role fresh from DB so deleted/downgraded users lose access immediately
    doc = await db.users.find_one({"email": email})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "user_not_found", "message": "User not found"},
        )
    return {"sub": email, "role": doc["role"], "sid": sid}


def require_role(min_role: str):
    async def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if ROLE_HIERARCHY.get(current_user.get("role", "viewer"), 0) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker
