import torch
from backend.models.tabular_model import TabularModel
from backend.models.tab_encoder import TabEncoder
from backend.models.fusion import CrossAttentionFusion

CAT_CARDINALITIES = [2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 3, 4, 3, 3, 3, 2]


def _categorical_tensors(batch: int, cardinalities: list) -> list:
    return [torch.randint(0, k, (batch,), dtype=torch.long) for k in cardinalities]


class TestTabEncoder:
    def test_forward_shape(self):
        model = TabEncoder(num_numerical=7, cat_cardinalities=CAT_CARDINALITIES, output_dim=128)
        numerical = torch.randn(4, 7)
        cats = _categorical_tensors(4, CAT_CARDINALITIES)
        out = model(numerical, cats)
        assert out.shape == (4, 128)

    def test_out_of_range_categorical_is_clamped(self):
        model = TabEncoder(num_numerical=7, cat_cardinalities=CAT_CARDINALITIES, output_dim=128)
        numerical = torch.randn(2, 7)
        cats = [torch.tensor([k - 1, k + 5], dtype=torch.long) for k in CAT_CARDINALITIES]
        out = model(numerical, cats)
        assert out.shape == (2, 128)


class TestTabularModel:
    def test_forward_shape_and_classes(self):
        model = TabularModel(num_numerical=7, cat_cardinalities=CAT_CARDINALITIES, num_classes=3)
        numerical = torch.randn(4, 7)
        cats = _categorical_tensors(4, CAT_CARDINALITIES)
        logits = model(numerical, cats)
        assert logits.shape == (4, 3)

    def test_deterministic_in_eval(self):
        model = TabularModel(num_numerical=7, cat_cardinalities=CAT_CARDINALITIES, num_classes=3)
        model.eval()
        numerical = torch.randn(2, 7)
        cats = _categorical_tensors(2, CAT_CARDINALITIES)
        with torch.no_grad():
            a = model(numerical, cats)
            b = model(numerical, cats)
        assert torch.allclose(a, b)


class TestCrossAttentionFusion:
    def test_no_images_returns_tab_projected(self):
        fusion = CrossAttentionFusion(tab_dim=128, img_dim=128, embed_dim=256)
        tab = torch.randn(2, 128)
        out = fusion(tab, {"face": None, "neck": None})
        assert out.shape == (2, 128)

    def test_with_single_image_modality(self):
        fusion = CrossAttentionFusion(tab_dim=128, img_dim=128, embed_dim=256)
        tab = torch.randn(2, 128)
        img = torch.randn(2, 128)
        out = fusion(tab, {"face": img, "neck": None})
        assert out.shape == (2, 128)

    def test_with_multiple_image_modalities(self):
        fusion = CrossAttentionFusion(tab_dim=128, img_dim=128, embed_dim=256)
        tab = torch.randn(2, 128)
        images = {"face": torch.randn(2, 128), "neck": torch.randn(2, 128)}
        out = fusion(tab, images)
        assert out.shape == (2, 128)
