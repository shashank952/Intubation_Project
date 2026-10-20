import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.deploy.auth import (
    ROLE_HIERARCHY,
    create_access_token,
    decode_token,
    hash_password,
    is_admin,
    require_role,
    verify_password,
)


class TestPasswords:
    def test_hash_verify_roundtrip(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert verify_password("secret123", hashed)
        assert not verify_password("wrongpass1", hashed)


class TestTokens:
    def test_token_roundtrip(self):
        token = create_access_token({"sub": "doc@example.com", "role": "doctor"})
        payload = decode_token(token)
        assert payload["sub"] == "doc@example.com"
        assert payload["role"] == "doctor"

    def test_expired_token_rejected(self):
        token = create_access_token(
            {"sub": "doc@example.com"},
            expires_delta=timedelta(seconds=-10),
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "doc@example.com"})
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token + "tamper")
        assert exc_info.value.status_code == 401


class TestRoles:
    def test_is_admin(self):
        assert is_admin({"role": "admin"})
        assert not is_admin({"role": "doctor"})
        assert not is_admin({})

    def test_role_hierarchy_ordering(self):
        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["doctor"] < ROLE_HIERARCHY["admin"]

    def test_require_role_allows_sufficient_role(self):
        checker = require_role("doctor")
        user = asyncio.run(checker(current_user={"sub": "a@b.com", "role": "admin"}))
        assert user["role"] == "admin"

    def test_require_role_blocks_insufficient_role(self):
        checker = require_role("doctor")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(checker(current_user={"sub": "a@b.com", "role": "viewer"}))
        assert exc_info.value.status_code == 403

    def test_require_role_blocks_unknown_role(self):
        checker = require_role("viewer")
        with pytest.raises(HTTPException):
            asyncio.run(checker(current_user={"sub": "a@b.com", "role": "ghost"}))
