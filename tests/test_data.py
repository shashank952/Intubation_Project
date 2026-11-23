import numpy as np
import pandas as pd
import torch
from PIL import Image

from backend.data.transforms import get_train_transforms, get_val_transforms
from backend.data.dataset import AirwayDataset
from backend.data.preprocessing import CATEGORICAL_COLS, NUMERICAL_COLS


def _make_image(size: int = 64) -> Image.Image:
    return Image.fromarray(np.random.randint(0, 255, (size, size, 3), dtype=np.uint8))


def _write_minimal_xlsx(path) -> None:
    data = {"Patient_ID": ["P-0001"], "Target": [1]}
    for col in NUMERICAL_COLS:
        data[col] = [40.0]
    for col in CATEGORICAL_COLS:
        data[col] = [1]
    pd.DataFrame(data).to_excel(path, index=False)


class TestTransforms:
    def test_train_transform_output_shape(self):
        out = get_train_transforms()(_make_image())
        assert out.shape == (3, 224, 224)

    def test_val_transform_output_shape(self):
        out = get_val_transforms()(_make_image())
        assert out.shape == (3, 224, 224)

    def test_val_transform_is_deterministic(self):
        img = _make_image()
        transform = get_val_transforms()
        a = transform(img)
        b = transform(img)
        assert torch.allclose(a, b)


class TestAirwayDataset:
    def test_getitem_shapes(self, tmp_path):
        xlsx = tmp_path / "data.xlsx"
        _write_minimal_xlsx(xlsx)
        ds = AirwayDataset(
            xlsx_path=str(xlsx), image_root=str(tmp_path / "images"), target_col="Target"
        )
        numerical, categorical, images, label = ds[0]
        assert numerical.shape == (len(NUMERICAL_COLS),)
        assert len(categorical) == len(CATEGORICAL_COLS)
        assert all(c.dim() == 0 for c in categorical)
        assert set(images.keys()) == set(AirwayDataset.MODALITIES)
        assert label.item() == 1

    def test_len(self, tmp_path):
        xlsx = tmp_path / "data.xlsx"
        _write_minimal_xlsx(xlsx)
        ds = AirwayDataset(
            xlsx_path=str(xlsx), image_root=str(tmp_path / "images"), target_col="Target"
        )
        assert len(ds) == 1

    def test_missing_images_return_none(self, tmp_path):
        xlsx = tmp_path / "data.xlsx"
        _write_minimal_xlsx(xlsx)
        ds = AirwayDataset(
            xlsx_path=str(xlsx), image_root=str(tmp_path / "nonexistent"), target_col="Target"
        )
        _, _, images, _ = ds[0]
        assert all(v is None for v in images.values())
