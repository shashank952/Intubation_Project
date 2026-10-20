"""
Seed the database with an admin user for testing.
Run: python scripts/seed_db.py

Passwords are generated with a CSPRNG and printed ONCE to stdout — they are
never hard-coded and never written to a file.
"""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from backend.deploy.database import connect_db, close_db, get_db
from backend.deploy.auth import hash_password


def _random_password() -> str:
    # 16 url-safe random chars; includes letters + digits via token_urlsafe.
    return secrets.token_urlsafe(12)


async def _seed_user(db, email: str, role: str) -> str:
    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"{role} user already exists ({email}) — skipping")
        return ""
    password = _random_password()
    await db.users.insert_one({
        "email": email,
        "hashed_password": hash_password(password),
        "role": role,
    })
    print(f"Created {role} user: {email}")
    print(f"  password: {password}  <-- store this now; it will not be shown again")
    return password


async def seed():
    await connect_db()
    db = get_db()
    await _seed_user(db, "admin@airwaymd.com", "admin")
    await _seed_user(db, "doctor1@airwaymd.com", "doctor")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
