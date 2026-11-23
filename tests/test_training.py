import numpy as np
import torch

from backend.training.loss import FocalLoss, ContrastiveAlignmentLoss
from backend.training.metrics import compute_metrics


class TestFocalLoss:
    def test_output_is_scalar_and_finite(self):
        loss_fn = FocalLoss(gamma=2.0)
        logits = torch.randn(8, 3)
        targets = torch.randint(0, 3, (8,))
        loss = loss_fn(logits, targets)
        assert loss.dim() == 0
        assert torch.isfinite(loss)

    def test_reduction_sum_is_larger_than_mean(self):
        logits = torch.randn(8, 3)
        targets = torch.randint(0, 3, (8,))
        summed = FocalLoss(gamma=2.0, reduction="sum")(logits, targets)
        mean = FocalLoss(gamma=2.0, reduction="mean")(logits, targets)
        assert summed >= mean

    def test_gamma_zero_equals_cross_entropy(self):
        logits = torch.randn(8, 3)
        targets = torch.randint(0, 3, (8,))
        focal = FocalLoss(gamma=0.0)(logits, targets)
        ce = torch.nn.functional.cross_entropy(logits, targets)
        assert torch.allclose(focal, ce)


class TestContrastiveAlignmentLoss:
    def test_output_is_scalar_and_finite(self):
        loss_fn = ContrastiveAlignmentLoss()
        tab = torch.randn(16, 128)
        img = torch.randn(16, 128)
        loss = loss_fn(tab, img)
        assert loss.dim() == 0
        assert torch.isfinite(loss)


class TestComputeMetrics:
    def test_perfect_predictions(self):
        labels = np.array([0, 0, 1, 1, 2, 2])
        preds = np.array([0, 0, 1, 1, 2, 2])
        probs = np.eye(3)[labels]
        m = compute_metrics(labels, preds, probs, num_classes=3)
        assert m["accuracy"] == 1.0
        assert m["auc_roc"] >= 0.99
        assert m["f1_weighted"] == 1.0
        assert all(s == 1.0 for s in m["sensitivity_per_class"])
        assert all(s == 1.0 for s in m["specificity_per_class"])

    def test_accuracy_with_one_mistake(self):
        labels = np.array([0, 1, 2, 0, 1, 2])
        preds = np.array([0, 1, 2, 0, 1, 1])
        probs = np.eye(3)[preds]
        m = compute_metrics(labels, preds, probs, num_classes=3)
        assert abs(m["accuracy"] - 5 / 6) < 1e-6

    def test_confusion_matrix_shape(self):
        labels = np.array([0, 1, 2, 0, 1, 2])
        preds = np.array([0, 1, 2, 0, 1, 1])
        probs = np.eye(3)[preds]
        m = compute_metrics(labels, preds, probs, num_classes=3)
        assert len(m["confusion_matrix"]) == 3
        assert all(len(row) == 3 for row in m["confusion_matrix"])
