"""Tests for the image upload analysis.

The real YOLO model is never loaded here: a stub replaces ``get_model`` so the
tests run anywhere (CI included) without torch weights.
"""

from __future__ import annotations

import asyncio
import io

import numpy as np
import pytest
from fastapi import HTTPException
from PIL import Image

from backend.deploy import image_analysis as ia
from backend.deploy.routers import images as images_router


# ------------------------------------------------------------------ helpers


class _Tensor:
    def __init__(self, array):
        self._array = np.asarray(array)

    def cpu(self):
        return self

    def numpy(self):
        return self._array

    def __len__(self):
        return len(self._array)


class _Boxes:
    def __init__(self, xyxy, conf):
        self.xyxy = _Tensor(xyxy)
        self.conf = _Tensor(conf)

    def __len__(self):
        return len(self.xyxy.numpy())


class _Keypoints:
    def __init__(self, xy, conf):
        self.xy = _Tensor(xy)
        self.conf = _Tensor(conf)


class _Result:
    def __init__(self, boxes=None, keypoints=None):
        self.boxes = boxes
        self.keypoints = keypoints


class _StubModel:
    def __init__(self, result):
        self._result = result

    def predict(self, *args, **kwargs):
        return [self._result]


def _image_bytes(bgr: np.ndarray) -> bytes:
    rgb = bgr[:, :, ::-1]
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="PNG")
    return buffer.getvalue()


def _blank(width=200, height=260) -> np.ndarray:
    return np.full((height, width, 3), 180, dtype=np.uint8)


def _face_result() -> _Result:
    xyxy = [[50.0, 40.0, 150.0, 220.0]]
    conf = [0.9]
    keypoints = [[[70.0, 80.0], [130.0, 80.0], [100.0, 110.0], [80.0, 170.0], [120.0, 170.0]]]
    keypoint_conf = [[0.9, 0.9, 0.9, 0.9, 0.9]]
    return _Result(boxes=_Boxes(xyxy, conf), keypoints=_Keypoints(keypoints, keypoint_conf))


# -------------------------------------------------------------------- decode


def test_decode_rejects_empty():
    with pytest.raises(ValueError):
        ia.decode(b"")


def test_decode_rejects_garbage():
    with pytest.raises(ValueError):
        ia.decode(b"this is not an image")


def test_decode_returns_bgr():
    array = np.zeros((10, 12, 3), dtype=np.uint8)
    array[:, :, 2] = 255  # red in RGB -> should arrive as BGR with blue=0, red=255
    decoded = ia.decode(_image_bytes(array))
    assert decoded.shape == (10, 12, 3)
    assert decoded[0, 0, 2] == 255


# ------------------------------------------------------------------ quality


def test_quality_metrics_on_flat_image():
    metrics = ia.quality_metrics(_blank(400, 500))
    assert metrics["width"] == 400
    assert metrics["height"] == 500
    assert metrics["megapixels"] == 0.2
    assert metrics["blur_score"] < 1.0  # no edges
    assert 175 <= metrics["brightness_mean"] <= 185


# ------------------------------------------------------------------- redact


def test_redact_faces_blacks_the_eye_strip():
    bgr = np.full((300, 300, 3), 255, dtype=np.uint8)
    face = {
        "box": [50.0, 40.0, 250.0, 260.0],
        "score": 0.9,
        "keypoints": [[100.0, 100.0], [200.0, 100.0], [150.0, 150.0], [110.0, 220.0], [190.0, 220.0]],
        "keypoint_conf": [0.9] * 5,
    }
    drawn = ia.redact_faces(bgr, [face])
    assert drawn == 1
    strip = ia.eye_strip(face, 300, 300)
    x1, y1, x2, y2 = strip
    assert np.all(bgr[y1:y2, x1:x2] == 0)


# ------------------------------------------------------------------ analyze


def test_analyze_without_face_returns_no_preview(monkeypatch):
    monkeypatch.setattr(ia, "get_model", lambda: _StubModel(_Result(boxes=None)))
    result = ia.analyze(_image_bytes(_blank()))

    assert result["status"] == "no_face"
    assert result["redacted"] is False
    assert result["preview_data_uri"] is None
    assert result["faces_redacted"] == 0
    assert "no_face" in result["quality"]["issues"]


def test_analyze_with_face_redacts_and_returns_preview(monkeypatch):
    monkeypatch.setattr(ia, "get_model", lambda: _StubModel(_face_result()))
    result = ia.analyze(_image_bytes(_blank()))

    assert result["status"] == "ok"
    assert result["redacted"] is True
    assert result["faces_redacted"] == 1
    assert result["preview_data_uri"].startswith("data:image/jpeg;base64,")
    assert result["geometry"] is not None
    assert result["geometry"]["mouth_to_iod"] > 0
    assert result["auto_fill"] == {}


def test_analyze_flags_multiple_faces(monkeypatch):
    single = _face_result()
    boxes = _Boxes(
        [[50.0, 40.0, 150.0, 220.0], [160.0, 60.0, 240.0, 200.0]],
        [0.9, 0.8],
    )
    keypoints = _Keypoints(
        [
            [[70.0, 80.0], [130.0, 80.0], [100.0, 110.0], [80.0, 170.0], [120.0, 170.0]],
            [[180.0, 100.0], [230.0, 100.0], [205.0, 120.0], [185.0, 160.0], [225.0, 160.0]],
        ],
        [[0.9] * 5, [0.8] * 5],
    )
    monkeypatch.setattr(
        ia, "get_model", lambda: _StubModel(_Result(boxes=boxes, keypoints=keypoints))
    )
    result = ia.analyze(_image_bytes(_blank(300, 300)))

    assert result["faces_redacted"] == 2
    assert "multiple_faces" in result["quality"]["issues"]
    assert result["quality"]["usable"] is False


# ------------------------------------------------------------------- router


class _FakeUpload:
    def __init__(self, content_type: str, payload: bytes):
        self.content_type = content_type
        self._payload = payload

    async def read(self, size: int = -1) -> bytes:
        return self._payload


def test_router_rejects_wrong_content_type():
    upload = _FakeUpload("text/plain", b"hello")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(images_router.analyze_image(upload, "", {"sub": "u1", "role": "doctor"}))
    assert exc.value.status_code == 415


def test_router_rejects_oversized_upload():
    payload = b"x" * (images_router.MAX_UPLOAD_BYTES + 1)
    upload = _FakeUpload("image/jpeg", payload)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(images_router.analyze_image(upload, "", {"sub": "u2", "role": "doctor"}))
    assert exc.value.status_code == 413


def test_router_rejects_invalid_patient_id():
    upload = _FakeUpload("image/jpeg", b"x")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(images_router.analyze_image(upload, "../etc", {"sub": "u3", "role": "doctor"}))
    assert exc.value.status_code == 400
