"""
Train the tabular-only model on dataset.xlsx.
No images involved — pure TabTransformer on 30 clinical parameters.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score
import sys
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32
EPOCHS = 100
PATIENCE = 15
LR = 1e-3
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1  # prevents overconfident logits that collapse into a bimodal Easy/Difficult split

CATEGORICAL_COLS = [
    "Gender", "Previous_Airway_Records",
    "Disease_Arthritis", "Disease_Diabetes", "Disease_Down_Syndrome",
    "Breathing_Snoring", "Breathing_Sleep_Apnea",
    "Symptom_Voice_Changes", "Symptom_Difficulty_Swallowing", "Symptom_Cant_Lie_Flat",
    "Injury_Swelling", "Injury_Previous_Neck_Fracture",
    "Previous_Emergencies_ICU",
    "BMI_Category", "Beard", "Chest_Size", "Neck_Structure",
    "Mallampati_Score", "TMD_Category",
    "Jaw_Movement", "Neck_Movement_Category", "Tissue_Flexibility",
]

NUMERICAL_COLS = [
    "Age", "BMI", "Neck_Circumference_cm",
    "Mouth_Opening_mm", "Thyromental_Distance_TMD_cm",
    "Sternomental_Distance_SMD_cm", "Neck_Movement_Degrees",
]

TARGET_COL = "Target"
ID_COL = "Patient_ID"


def load_and_split(xlsx_path: str, test_size: float = 0.15, val_size: float = 0.15, seed: int = 42):
    df = pd.read_excel(xlsx_path)
    ids = df[ID_COL].values
    y = df[TARGET_COL].values

    train_ids, temp_ids, y_train, y_temp = train_test_split(
        ids, y, test_size=test_size + val_size, random_state=seed, stratify=y
    )
    val_ids, test_ids, y_val, y_test = train_test_split(
        temp_ids, y_temp, test_size=test_size / (test_size + val_size),
        random_state=seed, stratify=y_temp
    )
    train_df = df[df[ID_COL].isin(train_ids)].copy()
    val_df = df[df[ID_COL].isin(val_ids)].copy()
    test_df = df[df[ID_COL].isin(test_ids)].copy()

    return train_df, val_df, test_df


def preprocess(train_df, val_df, test_df):
    scaler = StandardScaler()
    train_df[NUMERICAL_COLS] = scaler.fit_transform(train_df[NUMERICAL_COLS])
    val_df[NUMERICAL_COLS] = scaler.transform(val_df[NUMERICAL_COLS])
    test_df[NUMERICAL_COLS] = scaler.transform(test_df[NUMERICAL_COLS])

    label_encoders = {}
    cat_cardinalities = []
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        combined = pd.concat([train_df[col], val_df[col], test_df[col]]).astype(str).unique()
        le.fit(combined)
        train_df[col] = le.transform(train_df[col].astype(str))
        val_df[col] = le.transform(val_df[col].astype(str))
        test_df[col] = le.transform(test_df[col].astype(str))
        label_encoders[col] = le
        cat_cardinalities.append(len(le.classes_))

    return train_df, val_df, test_df, scaler, label_encoders, cat_cardinalities


def df_to_tensors(df, cat_cardinalities):
    numerical = torch.tensor(df[NUMERICAL_COLS].values, dtype=torch.float32)
    cat_tensors = []
    for i, col in enumerate(CATEGORICAL_COLS):
        cat_tensors.append(torch.tensor(df[col].values, dtype=torch.long).clamp(0, cat_cardinalities[i] - 1))
    labels = torch.tensor(df[TARGET_COL].values, dtype=torch.long)
    return numerical, cat_tensors, labels


def train_epoch(model, loader, optimizer, loss_fn, device, num_cat=22):
    model.train()
    total_loss = 0
    for batch in loader:
        numerical = batch[0].to(device)
        cat_tensors = [batch[i+1].to(device) for i in range(num_cat)]
        labels = batch[-1].to(device)

        optimizer.zero_grad()
        logits = model(numerical, cat_tensors)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)


@torch.no_grad()
def evaluate(model, loader, loss_fn, device, num_classes=3, num_cat=22):
    model.eval()
    total_loss = 0
    all_labels = []
    all_preds = []
    all_probs = []

    for batch in loader:
        numerical = batch[0].to(device)
        cat_tensors = [batch[i+1].to(device) for i in range(num_cat)]
        labels = batch[-1].to(device)

        logits = model(numerical, cat_tensors)
        loss = loss_fn(logits, labels)
        probs = torch.softmax(logits, dim=-1)
        preds = probs.argmax(dim=-1)

        total_loss += loss.item()
        all_labels.append(labels.cpu().numpy())
        all_preds.append(preds.cpu().numpy())
        all_probs.append(probs.cpu().numpy())

    labels = np.concatenate(all_labels)
    preds = np.concatenate(all_preds)
    probs = np.concatenate(all_probs)

    cm = confusion_matrix(labels, preds)
    report = classification_report(labels, preds, target_names=["Easy", "Moderate", "Difficult"], digits=3)

    sensitivities, specificities = [], []
    for i in range(num_classes):
        tp = cm[i, i]
        fn = cm[i, :].sum() - tp
        fp = cm[:, i].sum() - tp
        tn = cm.sum() - (tp + fn + fp)
        sensitivities.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
        specificities.append(tn / (tn + fp) if (tn + fp) > 0 else 0.0)

    try:
        auc = roc_auc_score(labels, probs, multi_class="ovr")
    except Exception:
        auc = 0.0

    metrics = {
        "val_loss": total_loss / len(loader),
        "accuracy": (preds == labels).mean(),
        "auc_roc": auc,
        "sensitivity": sensitivities,
        "specificity": specificities,
        "confusion_matrix": cm,
    }
    return metrics, report


def main():
    print(f"Device: {DEVICE}")
    print(f"Loading dataset.xlsx...")
    train_df, val_df, test_df = load_and_split(str(ROOT / "dataset.xlsx"))

    print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    print(f"Preprocessing...")
    train_df, val_df, test_df, scaler, label_encoders, cat_cardinalities = preprocess(
        train_df, val_df, test_df
    )

    num_numerical = len(NUMERICAL_COLS)
    print(f"Numerical: {num_numerical}, Categorical: {len(cat_cardinalities)}")

    train_num, train_cat, train_labels = df_to_tensors(train_df, cat_cardinalities)
    val_num, val_cat, val_labels = df_to_tensors(val_df, cat_cardinalities)
    test_num, test_cat, test_labels = df_to_tensors(test_df, cat_cardinalities)

    train_loader = DataLoader(
        TensorDataset(train_num, *train_cat, train_labels),
        batch_size=BATCH_SIZE, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(val_num, *val_cat, val_labels),
        batch_size=BATCH_SIZE, shuffle=False
    )
    test_loader = DataLoader(
        TensorDataset(test_num, *test_cat, test_labels),
        batch_size=BATCH_SIZE, shuffle=False
    )

    from backend.models.tabular_model import TabularModel
    model = TabularModel(
        num_numerical=num_numerical,
        cat_cardinalities=cat_cardinalities,
        num_classes=3,
        embed_dim=64,
        tab_output_dim=128,
        dropout=0.3,
    ).to(DEVICE)

    class_counts = train_df[TARGET_COL].value_counts().sort_index()
    weight = torch.tensor(
        [len(train_df) / (len(class_counts) * class_counts[i]) for i in range(len(class_counts))],
        dtype=torch.float32
    ).to(DEVICE)
    loss_fn = nn.CrossEntropyLoss(weight=weight, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=5, factor=0.5)

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

    print(f"\nTraining for up to {EPOCHS} epochs (early stopping patience={PATIENCE})...")
    for epoch in range(EPOCHS):
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, DEVICE, len(cat_cardinalities))
        metrics, _ = evaluate(model, val_loader, loss_fn, DEVICE, num_cat=len(cat_cardinalities))

        scheduler.step(metrics["val_loss"])

        if metrics["val_loss"] < best_val_loss:
            best_val_loss = metrics["val_loss"]
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(
                f"  Epoch {epoch+1:3d}/{EPOCHS} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {metrics['val_loss']:.4f} | "
                f"Acc: {metrics['accuracy']:.4f} | "
                f"AUC: {metrics['auc_roc']:.4f}"
            )

        if epochs_no_improve >= PATIENCE:
            print(f"  Early stopping at epoch {epoch+1}")
            break

    print(f"\nBest val loss: {best_val_loss:.4f}")

    model.load_state_dict(best_state)
    torch.save(best_state, ROOT / "checkpoints" / "tabular_best.pt")
    print("Model saved to checkpoints/tabular_best.pt")

    print("\n" + "=" * 60)
    print("FINAL TEST SET EVALUATION")
    print("=" * 60)
    test_metrics, test_report = evaluate(model, test_loader, loss_fn, DEVICE, num_cat=len(cat_cardinalities))
    print(test_report)
    print(f"AUC-ROC (OVR): {test_metrics['auc_roc']:.4f}")
    print(f"Accuracy:      {test_metrics['accuracy']:.4f}")
    print(f"Sensitivity (Easy/Moderate/Difficult): {[f'{s:.3f}' for s in test_metrics['sensitivity']]}")
    print(f"Specificity (Easy/Moderate/Difficult): {[f'{s:.3f}' for s in test_metrics['specificity']]}")
    print(f"\nConfusion Matrix:")
    print(test_metrics["confusion_matrix"])


if __name__ == "__main__":
    main()
