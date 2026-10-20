from datetime import datetime, timedelta, timezone

from backend.deploy.auth import (
    SESSION_EXPIRED,
    SESSION_REVOKED,
    create_access_token,
    decode_token,
    session_error,
    should_touch,
    token_expiry,
)
from backend.deploy.config import settings

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)


def _session(**overrides) -> dict:
    base = {
        "sid": "abc123",
        "email": "doc@example.com",
        "created_at": NOW - timedelta(minutes=5),
        "last_activity_at": NOW - timedelta(minutes=1),
        "revoked_at": None,
    }
    base.update(overrides)
    return base


class TestSessionState:
    def test_fresh_session_ok(self):
        assert session_error(_session(), NOW) is None

    def test_missing_session_is_expired(self):
        assert session_error(None, NOW) == SESSION_EXPIRED

    def test_revoked_session_rejected(self):
        s = _session(revoked_at=NOW - timedelta(minutes=1))
        assert session_error(s, NOW) == SESSION_REVOKED

    def test_idle_beyond_timeout_expires(self):
        idle = settings.session_idle_timeout_minutes
        s = _session(last_activity_at=NOW - timedelta(minutes=idle + 1))
        assert session_error(s, NOW) == SESSION_EXPIRED

    def test_idle_within_window_ok(self):
        idle = settings.session_idle_timeout_minutes
        s = _session(last_activity_at=NOW - timedelta(minutes=idle) + timedelta(seconds=5))
        assert session_error(s, NOW) is None

    def test_absolute_cap_expires_active_session(self):
        hours = settings.session_absolute_timeout_hours
        s = _session(
            created_at=NOW - timedelta(hours=hours + 1),
            last_activity_at=NOW - timedelta(seconds=5),
        )
        assert session_error(s, NOW) == SESSION_EXPIRED

    def test_naive_stored_datetimes_are_treated_as_utc(self):
        idle = settings.session_idle_timeout_minutes
        s = _session(
            created_at=(NOW - timedelta(minutes=5)).replace(tzinfo=None),
            last_activity_at=(NOW - timedelta(minutes=idle + 1)).replace(tzinfo=None),
        )
        assert session_error(s, NOW) == SESSION_EXPIRED


class TestTouchThrottle:
    def test_recent_activity_does_not_touch(self):
        assert should_touch(_session(last_activity_at=NOW - timedelta(seconds=5)), NOW) is False

    def test_stale_activity_touches(self):
        interval = settings.session_touch_interval_seconds
        s = _session(last_activity_at=NOW - timedelta(seconds=interval + 1))
        assert should_touch(s, NOW) is True


class TestTokenClaims:
    def test_token_carries_sid_and_iat(self):
        token = create_access_token({"sub": "doc@example.com", "role": "doctor", "sid": "abc123"})
        payload = decode_token(token)
        assert payload["sid"] == "abc123"
        assert "iat" in payload
        assert "exp" in payload

    def test_legacy_token_has_no_sid(self):
        token = create_access_token({"sub": "doc@example.com", "role": "doctor"})
        assert "sid" not in decode_token(token)

    def test_expiry_capped_by_absolute_timeout(self, monkeypatch):
        monkeypatch.setattr(settings, "jwt_expire_minutes", 60 * 24 * 30)
        monkeypatch.setattr(settings, "session_absolute_timeout_hours", 1)
        assert token_expiry(NOW) == NOW + timedelta(hours=1)

    def test_expiry_uses_jwt_lifetime_when_shorter(self, monkeypatch):
        monkeypatch.setattr(settings, "jwt_expire_minutes", 60)
        monkeypatch.setattr(settings, "session_absolute_timeout_hours", 12)
        assert token_expiry(NOW) == NOW + timedelta(minutes=60)
