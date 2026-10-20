import pytest
from fastapi import HTTPException

import backend.deploy.routers.predictions as pred_router
from backend.deploy.routers.predictions import _enforce_prediction_rate_limit


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    pred_router._pred_timestamps.clear()
    yield
    pred_router._pred_timestamps.clear()


ADMIN = {"sub": "admin@x.com", "role": "admin"}
DOCTOR = {"sub": "doc@x.com", "role": "doctor"}


def test_admin_bypasses_rate_limit():
    for _ in range(50):
        _enforce_prediction_rate_limit(ADMIN)


def test_doctor_limited_to_max_per_window():
    for _ in range(pred_router._MAX_PREDS_PER_WINDOW):
        _enforce_prediction_rate_limit(DOCTOR)
    with pytest.raises(HTTPException) as exc_info:
        _enforce_prediction_rate_limit(DOCTOR)
    assert exc_info.value.status_code == 429


def test_rate_limit_is_per_user():
    for _ in range(pred_router._MAX_PREDS_PER_WINDOW):
        _enforce_prediction_rate_limit(DOCTOR)
    other = {"sub": "doc2@x.com", "role": "doctor"}
    _enforce_prediction_rate_limit(other)
