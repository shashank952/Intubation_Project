import torch
import torch.nn as nn
from torch.cuda.amp import autocast, GradScaler
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Dict, Optional
import mlflow
import numpy as np
from .loss import FocalLoss, ContrastiveAlignmentLoss
from .metrics import compute_metrics


class Trainer:
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        num_epochs: int = 100,
        patience: int = 10,
        device: str = "cuda",
        checkpoint_dir: str = "checkpoints",
        use_amp: bool = True,
        class_weights: Optional[torch.Tensor] = None,
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.num_epochs = num_epochs
        self.patience = patience
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.use_amp = use_amp and device == "cuda"

        self.classifier_loss = FocalLoss(alpha=class_weights.to(device) if class_weights is not None else None)
        self.alignment_loss = ContrastiveAlignmentLoss()
        self.optimizer = torch.optim.AdamW(
            model.parameters(), lr=learning_rate, weight_decay=weight_decay
        )
        self.scaler = GradScaler(enabled=self.use_amp)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer, T_0=10, T_mult=2
        )
        self.best_val_loss = float("inf")
        self.epochs_no_improve = 0

    def train_epoch(self) -> Dict[str, float]:
        self.model.train()
        total_loss = 0.0
        total_cls = 0.0
        total_align = 0.0
        num_batches = 0

        for batch in self.train_loader:
            numerical, categorical_indices, images, labels = batch
            labels = labels.to(self.device)
            numerical = numerical.to(self.device)
            categorical_indices = [c.to(self.device) for c in categorical_indices]

            with autocast(enabled=self.use_amp):
                logits = self.model(numerical, categorical_indices, images)
                cls_loss = self.classifier_loss(logits, labels)
                loss = cls_loss

            self.optimizer.zero_grad()
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()

            total_loss += loss.item()
            total_cls += cls_loss.item()
            num_batches += 1

        return {
            "loss": total_loss / num_batches,
            "cls_loss": total_cls / num_batches,
        }

    @torch.no_grad()
    def validate(self) -> Dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        all_labels = []
        all_preds = []
        all_probs = []
        num_batches = 0

        for batch in self.val_loader:
            numerical, categorical_indices, images, labels = batch
            labels = labels.to(self.device)
            numerical = numerical.to(self.device)
            categorical_indices = [c.to(self.device) for c in categorical_indices]

            with autocast(enabled=self.use_amp):
                logits = self.model(numerical, categorical_indices, images)
                loss = self.classifier_loss(logits, labels)

            total_loss += loss.item()
            probs = torch.softmax(logits, dim=-1)
            preds = probs.argmax(dim=-1)

            all_labels.append(labels.cpu().numpy())
            all_preds.append(preds.cpu().numpy())
            all_probs.append(probs.cpu().numpy())
            num_batches += 1

        labels_np = np.concatenate(all_labels)
        preds_np = np.concatenate(all_preds)
        probs_np = np.concatenate(all_probs)

        metrics = compute_metrics(labels_np, preds_np, probs_np, num_classes=logits.size(-1))
        metrics["val_loss"] = total_loss / num_batches
        return metrics

    def fit(self):
        mlflow.set_experiment("airway_multimodal")
        with mlflow.start_run():
            mlflow.log_params({
                "epochs": self.num_epochs,
                "patience": self.patience,
                "optimizer": "AdamW",
                "scheduler": "CosineAnnealingWarmRestarts",
                "amp": self.use_amp,
            })

            for epoch in range(self.num_epochs):
                train_metrics = self.train_epoch()
                val_metrics = self.validate()

                mlflow.log_metrics({
                    "train_loss": train_metrics["loss"],
                    "val_loss": val_metrics["val_loss"],
                    "val_accuracy": val_metrics["accuracy"],
                    "val_auc": val_metrics["auc_roc"],
                    "val_f1": val_metrics["f1_weighted"],
                }, step=epoch)

                self.scheduler.step()

                print(
                    f"Epoch {epoch+1}/{self.num_epochs} | "
                    f"Train Loss: {train_metrics['loss']:.4f} | "
                    f"Val Loss: {val_metrics['val_loss']:.4f} | "
                    f"Acc: {val_metrics['accuracy']:.4f} | "
                    f"AUC: {val_metrics['auc_roc']:.4f}"
                )

                if val_metrics["val_loss"] < self.best_val_loss:
                    self.best_val_loss = val_metrics["val_loss"]
                    self.epochs_no_improve = 0
                    torch.save(self.model.state_dict(), self.checkpoint_dir / "best.pt")
                else:
                    self.epochs_no_improve += 1
                    if self.epochs_no_improve >= self.patience:
                        print(f"Early stopping at epoch {epoch+1}")
                        break

            mlflow.log_artifact(str(self.checkpoint_dir / "best.pt"))
