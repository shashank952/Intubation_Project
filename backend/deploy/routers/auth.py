import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..schemas import TokenOut, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory throttles (per-process). Move to a shared store if running multiple workers.
_WINDOW_SECONDS = 900
_MAX_FAILED_PER_EMAIL = 5
_MAX_LOGIN_PER_IP = 30
_MAX_REGISTER_PER_IP = 10

_failed_attempts = defaultdict(list)
_login_by_ip = defaultdict(list)
_register_by_ip = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(store, key):
    now = time.time()
    store[key] = [t for t in store[key] if now - t < _WINDOW_SECONDS]
    return store[key]


@router.post("/register", status_code=201)
async def register(user: UserCreate, request: Request):
    ip = _client_ip(request)
    if len(_prune(_register_by_ip, ip)) >= _MAX_REGISTER_PER_IP:
        raise HTTPException(status_code=429, detail="Too many sign-ups. Try again later.")
    db = get_db()
    email = user.email.strip().lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = user.model_dump(exclude={"password"})
    doc["email"] = email
    doc["role"] = "doctor"  # registration never grants admin
    doc["hashed_password"] = hash_password(user.password)
    await db.users.insert_one(doc)
    _register_by_ip[ip].append(time.time())
    return {"message": "User created", "email": email}


@router.post("/login", response_model=TokenOut)
async def login(user: UserCreate, request: Request):
    ip = _client_ip(request)
    db = get_db()
    email = user.email.strip().lower()
    if len(_prune(_failed_attempts, email)) >= _MAX_FAILED_PER_EMAIL:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    if len(_prune(_login_by_ip, ip)) >= _MAX_LOGIN_PER_IP:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    _login_by_ip[ip].append(time.time())
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(user.password, doc["hashed_password"]):
        _failed_attempts[email].append(time.time())
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _failed_attempts.pop(email, None)
    token = create_access_token({"sub": email, "role": doc["role"]})
    return TokenOut(access_token=token, user=UserOut(email=email, role=doc["role"]))


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(email=current_user["sub"], role=current_user["role"])
