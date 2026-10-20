# Multimodal Difficult Airway Prediction — Project Plan

---

## 1. PROJECT OVERVIEW

- **Goal:** Predict difficult airway (intubation difficulty) before procedure using patient data + medical images
- **Target:** Multi-class — **Easy / Moderate / Difficult**
- **End use:** Clinical decision support tool for anesthesiologists
- **Status:** Data collection / planning phase

---

## 2. DATA

### 2.1 Tabular Data (30 columns in dataset.xlsx)

| Category | Parameters |
|----------|-----------|
| **Demographics** | Patient_ID, Gender, Age |
| **Previous records** | Previous airway records (easy/difficult/unknown) |
| **Disease history** | Arthritis, Diabetes, Down syndrome |
| **Breathing** | Snoring, Sleep apnea |
| **Symptoms** | Voice changes, Difficulty swallowing, Can't lie flat |
| **Injury** | Swelling, Previous neck fracture |
| **ICU history** | Previous emergencies / ICU admission |
| **Physical** | BMI, BMI category, Neck circumference, Beard, Chest size, Neck structure |
| **Airway features** | Mouth opening, Mallampati score (I-IV), Thyromental distance (TMD), TMD category, Sternomental distance (SMD), Jaw movement, Neck movement (degrees + category), Tissue flexibility |

*Image-derived columns (teeth visibility, jaw/mouth size, facial structure, side profile, neck tissue/fat, ultrasound tongue thickness, CT/MRI findings) removed from dataset.xlsx.*

### 2.3 Data Requirements

- Minimum **500+ patients** recommended for deep learning
- Each patient: 1 row in xlsx
- Label each case as Easy / Moderate / Difficult (based on Cormack-Lehane grade or intubation outcome)
- Split at patient level: 80% train, 10% val, 10% test (never split same patient across sets)

---

## 3. TECHNOLOGY STACK

| Layer | Technology | Why |
|-------|-----------|-----|
| **Language** | Python 3.10 | Industry standard for ML |
| **Deep learning** | PyTorch + torchvision | Flexible, research-standard, custom architectures |
| **Image models** | timm (PyTorch Image Models) | Pretrained ResNet / EfficientNet |
| **Tabular models** | pytorch-tabular | TabTransformer for mixed categorical/numerical |
| **Image processing** | OpenCV, Pillow | Resize, augment, normalize images |
| **Medical images** | SimpleITK | DICOM / CT / MRI loading and window-level normalization |
| **Data handling** | pandas, numpy | Tabular preprocessing |
| **Experiment tracking** | MLflow | Log metrics, params, model artifacts |
| **Explainability** | Captum | SHAP for tabular, Grad-CAM for images |
| **Export** | ONNX | Cross-platform inference |
| **Deployment** | FastAPI + Streamlit | API backend + web UI |
| **Container** | Docker | Consistent deployment |

### System Specs

- **GPU:** NVIDIA GeForce GTX 1650 Ti (4GB VRAM)
- **CUDA:** 13.2
- **Memory:** 4GB VRAM (limits batch size and model size)

---

## 4. ARCHITECTURE — MULTIMODAL MODEL

### 4.1 Component Overview

```
  TABULAR (30 features)                IMAGES (5 modalities)
         │                                      │
  ┌──────┴──────┐               ┌───────────────┴───────────────┐
  │ TabEncoder  │               │  Face CNN    Side CNN         │
  │ TabTransf.  │               │  Neck CNN    Ultrasound CNN   │
  │             │               │  CT/MRI CNN                   │
  └──────┬──────┘               └───────────────┬───────────────┘
         │                                      │
    e_tab ∈ ℝ¹²⁸                     e_img_i ∈ ℝ¹²⁸ each
         │                                      │
         └──────────────┬───────────────────────┘
                        ▼
           ┌──────────────────────┐
           │   FUSION MODULE      │
           │  Cross-Attention     │
           │  (tab ↔ images)      │
           └──────────┬───────────┘
                      ▼
              Combined Embedding
                      ▼
           ┌──────────────────────┐
           │  CLASSIFICATION HEAD │
           │  MLP: 256 → 128 → 3  │
           └──────────┬───────────┘
                      ▼
              [Easy] [Moderate] [Difficult]
```

### 4.2 Component Details

| Component | What it is | Details |
|-----------|-----------|---------|
| **TabEncoder** | TabTransformer | Handles mixed categorical + numerical columns. Embeds each categorical, adds learnable positional encoding, passes through Transformer layers. Output: 128-dim vector |
| **ImageEncoder** | ResNet-50 (pretrained) | One per modality OR shared weights for similar modalities (face + profile share backbone). Remove classification head, take global avg pool features. Output: 128-dim vector per image |
| **Fusion** | Cross-Attention | Multi-head attention between tabular embedding (query) and image embeddings (keys/values) — lets the model learn which image features matter given the patient's clinical profile |
| **Head** | MLP + Softmax | 256 → 128 → 3 layers with Dropout(0.3) + GELU activations |

### 4.3 Design Rationale

- **TabTransformer** chosen over simple MLP: handles missing data better, natively processes categoricals
- **ResNet-50** chosen over Vision Transformer: better with limited data (500-1000 patients)
- **Cross-attention fusion** over concatenation: model learns modality interactions dynamically
- **Per-modality CNN branches**: each image type has different characteristics (RGB vs ultrasound vs CT)

---

## 5. PREPROCESSING

### 5.1 Tabular Preprocessing

- Categorical columns → Label Encoding + Embedding (TabTransformer handles this internally)
- Numerical columns → Z-score normalization (mean=0, std=1)
- Missing values → Learnable mask embedding (TabTransformer native support) or mode/mean imputation for simple baselines
- Mallampati Score (I-IV) → Ordinal encoding (preserves ranking)
- Yes/No columns → Binary (0/1)

### 5.2 Image Preprocessing

| Step | Details |
|------|---------|
| **Resize** | All images to 224×224 pixels |
| **Normalization** | Per-modality: ImageNet stats for RGB photos, window-level normalization for CT/MRI (e.g., [-1000, 1000] HU → [0,1]) |
| **Format** | All converted to 3-channel tensors (repeat grayscale if needed) |

### 5.3 Image Augmentation (training only)

- Random horizontal flip
- Random rotation (±10°)
- Color jitter (brightness ±0.2, contrast ±0.2) — for RGB photos only
- Random affine (translate ±10%)
- Elastic deformation — for ultrasound and CT (tissue deformation is realistic)
- *No augmentation for validation/test*

### 5.4 Class Imbalance Handling

- Check distribution of Easy / Moderate / Difficult in training set
- Apply one of:
  - **Weighted loss** — higher weight for minority classes
  - **Oversampling** — duplicate minority class samples
  - **Focal Loss** — reduces loss for well-classified examples, focuses on hard ones

---

## 6. TRAINING

### 6.1 Training Strategy (3 stages)

| Stage | What | Why |
|-------|------|-----|
| **Stage 1: Baselines** | Train tabular-only model + image-only model separately | Establish performance floor — quantify how much multimodal adds |
| **Stage 2: Pretrain encoders** | Freeze image encoder, train TabEncoder + Fusion + Head | Stabilizes training before full fine-tune |
| **Stage 3: End-to-end** | Unfreeze all, fine-tune everything with low LR (1e-5) | Let modalities adapt to each other |

### 6.2 Training Configuration

| Parameter | Value |
|-----------|-------|
| Batch size | 8–16 (limited by 4GB VRAM) |
| Gradient accumulation | 2–4 steps (effective batch = 32–64) |
| Optimizer | AdamW (weight decay = 1e-4) |
| Learning rate | 1e-3 (pretrain), 1e-5 (fine-tune) |
| LR scheduler | Cosine annealing with warmup (10% of total steps) |
| Epochs | 50–100 (early stopping patience = 10) |
| Mixed precision | torch.cuda.amp — FP16 to save VRAM |
| Loss function | Cross-Entropy Loss + Auxiliary contrastive loss (align tab/image embeddings) |

### 6.3 Regularization

- Dropout (0.3) in MLP head
- Weight decay (1e-4)
- Label smoothing (0.1)
- Early stopping on validation loss
- ReduceLROnPlateau if validation plateaus

---

## 7. TESTING & EVALUATION

### 7.1 Metrics

| Metric | Why it matters |
|--------|---------------|
| **AUC-ROC** (per class) | Overall discriminative ability |
| **Sensitivity / Recall** | How many difficult airways we catch (critical — missing one is dangerous) |
| **Specificity** | How many easy airways we correctly identify |
| **Precision** | How many predicted-difficult are actually difficult |
| **F1-score** | Harmonic mean of precision & recall |
| **Negative Predictive Value** | When we say "easy," how often is it correct? (very important for safety) |
| **Confusion Matrix** | See misclassifications between Moderate↔Difficult, etc. |

### 7.2 Evaluation Protocol

- Evaluate on held-out test set (10% of data) — never seen during training
- Stratified k-fold cross-validation (5-fold) for robust estimates
- Report metrics with 95% confidence intervals
- Calibration curve + temperature scaling for well-calibrated probabilities

### 7.3 Ablation Studies

| Experiment | What it tests |
|------------|--------------|
| Tabular only | How far can clinical data alone go? |
| Image only (all 5) | How far can images alone go? |
| Multimodal (full) | The complete model |
| Drop face image | Which modality is most important? |
| Drop ultrasound | |
| Drop CT/MRI | |
| TabTransformer → simple MLP | Is complex tabular encoder worth it? |
| Concatenation → cross-attention | Does attention fusion help? |

### 7.4 Explainability

- **SHAP** on tabular features — which clinical factors drive predictions most?
- **Grad-CAM** on images — which regions of face/neck/ultrasound mattered?
- **Attention weights** from fusion module — which image modality was most influential for each prediction?

---

## 8. FULL PIPELINE (END-TO-END)

### 8.1 Data Collection Flow

```
Hospital / Clinic
     │
      ├── Patient examination → Enter 30 tabular params into dataset.xlsx
      ├── Capture 5 images → Save to patient folder
     └── Record intubation outcome → Label as Easy/Moderate/Difficult
                              │
                              ▼
                    Raw dataset ready for preprocessing
```

### 8.2 Training Pipeline

```
Raw Data
    │
    ▼
Preprocessing Script
    ├── Load dataset.xlsx → encode + normalize tabular
    ├── Load images → resize + augment
    └── Save processed tensors (or use on-the-fly in DataLoader)
    │
    ▼
Model Training (3 stages)
    ├── Stage 1: Baselines
    ├── Stage 2: Pretrain encoders
    └── Stage 3: End-to-end fine-tune
    │
    ▼
Evaluation
    ├── Test set metrics
    ├── Confusion matrix
    ├── Ablation experiments
    └── Explainability (SHAP + Grad-CAM)
    │
    ▼
Export
    └── TorchScript → ONNX → model.onnx
```

### 8.3 Deployment Pipeline

```
model.onnx
    │
    ▼
FastAPI Backend
    ├── POST /predict
    │   Input: JSON (tabular) + image files
    │   Output: { "risk": "Moderate",
    │             "probabilities": {
    │               "Easy": 0.15,
    │               "Moderate": 0.70,
    │               "Difficult": 0.15
    │             },
    │             "explanation": { "shap": {...}, "gradcam": {...} }
    │           }
    │
    └── GET /health — health check
    │
    ▼
Streamlit Frontend
    ├── Form: enter patient parameters
    ├── Upload: 5 images
    ├── Predict: show risk score + confidence
    └── Explain: show SHAP bar chart + Grad-CAM heatmaps
    │
    ▼
Docker container (API + UI)
    └── Deploy to server / cloud
```

---

## 9. DIRECTORY STRUCTURE

```
D:\Minor_Project\
├── dataset.xlsx                      # Tabular data template (30 columns)
├── project_plan.md                   # This file
├── AGENTS.md                         # Instructions for ML agents
├── data/
│   ├── raw/
│   │   ├── patient_001/
│   │   │   ├── face.jpg
│   │   │   ├── side_profile.jpg
│   │   │   ├── neck.jpg
│   │   │   ├── ultrasound.png
│   │   │   └── ct_mri.dcm
│   │   ├── patient_002/
│   │   └── ...
│   ├── processed/                    # Preprocessed tensors
│   └── splits/                       # Train/val/test patient ID lists
├── src/
│   ├── data/
│   │   ├── dataset.py                # PyTorch Dataset class
│   │   ├── preprocessing.py          # Tabular encode + normalize
│   │   ├── transforms.py             # Image augmentations
│   │   └── loaders.py                # DataLoader builders
│   ├── models/
│   │   ├── tab_encoder.py            # TabTransformer
│   │   ├── image_encoder.py          # ResNet-50 backbone
│   │   ├── fusion.py                 # Cross-attention fusion
│   │   └── multimodal_model.py       # Full model assembly
│   ├── training/
│   │   ├── trainer.py                # Training loop
│   │   ├── loss.py                   # BCE + contrastive loss
│   │   └── metrics.py                # AUC, sensitivity, etc.
│   ├── explain/
│   │   ├── shap_explainer.py         # SHAP for tabular
│   │   └── gradcam.py                # Grad-CAM for images
│   └── deploy/
│       ├── api.py                    # FastAPI app
│       ├── frontend.py               # Streamlit UI
│       ├── export.py                 # ONNX export
│       └── Dockerfile
├── configs/
│   ├── train_config.yaml             # Hyperparameters
│   └── data_config.yaml              # Data paths + preprocessing params
├── notebooks/
│   ├── 01_eda.ipynb                  # Exploratory data analysis
│   ├── 02_baselines.ipynb            # Tab-only + image-only baselines
│   └── 03_ablation.ipynb             # Ablation experiments
└── requirements.txt                  # All Python dependencies
```

---

## 10. IMPLEMENTATION PLAN (ORDERED)

| Step | Task | Est. Time |
|------|------|-----------|
| 1 | Install PyTorch, torchvision, timm, and all dependencies | 30 min |
| 2 | Create directory structure (src/, data/, configs/, notebooks/) | 15 min |
| 3 | Write tabular preprocessing script (encode + normalize 30 columns) | 1 hr |
| 4 | Write Dataset class that loads xlsx + images per patient | 1 hr |
| 5 | Build TabEncoder (TabTransformer) | 2 hr |
| 6 | Build ImageEncoder (ResNet-50 with per-modality branches) | 2 hr |
| 7 | Build Fusion module (cross-attention) | 2 hr |
| 8 | Assemble full MultimodalModel | 1 hr |
| 9 | Write training loop with mixed precision + early stopping | 2 hr |
| 10 | Train tabular-only baseline | — |
| 11 | Train image-only baseline | — |
| 12 | Train full multimodal model | — |
| 13 | Run ablation experiments | — |
| 14 | Implement SHAP + Grad-CAM explainability | — |
| 15 | Export to ONNX | — |
| 16 | Build FastAPI + Streamlit deployment | — |
| 17 | Dockerize | — |

---

## 11. KEY DECISIONS SUMMARY

| Decision | Choice | Reason |
|----------|--------|--------|
| Framework | PyTorch | Research flexibility, custom architectures |
| Tabular model | TabTransformer | Mixed categorical/num, handles missing data |
| Image model | ResNet-50 | Good with limited data, 4GB VRAM friendly |
| Fusion | Cross-attention | Learns modality interactions dynamically |
| Loss | CE + contrastive | Better embedding alignment |
| Deployment | FastAPI + Streamlit | Simple, Python-native, fast to build |
| Export | ONNX | Cross-platform, optimized inference |

---

## 12. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| Small dataset (<500) | Model overfits | Transfer learning, stronger augmentation, simpler model (EfficientNet-B0 instead of ResNet-50) |
| Class imbalance (mostly Easy) | Model ignores Moderate/Difficult | Weighted loss, oversampling, Focal Loss |
| Missing images per patient | Can't train multimodal | Set image to zeros + mask, or use partial-data training |
| 4GB VRAM | Can't train large models | Mixed precision, batch size=8, gradient accumulation, use EfficientNet |
| No CT/MRI available | Lose one modality | Train without it — still works with 4 image types |

---

## 13. QUICK START (WHEN DATA IS READY)

```bash
# 1. Install dependencies
pip install torch torchvision timm pytorch-tabular pandas numpy opencv-python scikit-learn mlflow captum onnx onnxruntime fastapi uvicorn streamlit

# 2. Preprocess data
python src/data/preprocessing.py --input dataset.xlsx --image-dir data/raw

# 3. Train model
python src/training/trainer.py --config configs/train_config.yaml

# 4. Evaluate
python src/training/evaluate.py --checkpoint checkpoints/best.pt

# 5. Export
python src/deploy/export.py --checkpoint checkpoints/best.pt --output model.onnx

# 6. Run API
uvicorn backend.deploy.api:app --host 0.0.0.0 --port 8000

# 7. Run UI
streamlit run src/deploy/frontend.py
```

---

## 14. FILES IN THIS REPO (CURRENT)

| File | Purpose |
|------|---------|
| `dataset.xlsx` | Tabular data template (30 columns, blank) |
| `project_plan.md` | This document |
| `AGENTS.md` | Instructions for AI agents working on this repo |
| `PPTS_&_Folders/` | Source materials (PDFs, PPTX) |

---

## 15. PRODUCTION IDEA — LLM Clinical Assistant + DevOps

### 15.1 LLM-Powered Clinical Assistant

**Concept:**
After the multimodal model predicts the airway difficulty class (Easy/Moderate/Difficult), an LLM consumes the prediction + explainability outputs + raw patient data and generates a natural-language clinical narrative to assist the doctor.

**End-to-end flow:**

```
Patient Data + Images
         │
         ▼
  ┌─────────────────────────┐
  │ Multimodal Model         │──→ Prediction: "Difficult Airway (p=0.87)"
  └──────────┬──────────────┘
             │
             ▼
  ┌─────────────────────────┐
  │ Explainability           │──→ SHAP: Mallampati IV +0.32, TMD<6cm
  │ (SHAP + Grad-CAM)        │     Grad-CAM: Neck tissue highlighted
  └──────────┬──────────────┘
             │
             ▼
  ┌─────────────────────────┐
  │ Prompt Assembler         │
  │ Builds structured prompt │
  │ from prediction + data   │
  └──────────┬──────────────┘
             │
             ▼
  ┌─────────────────────────┐
  │  LLM (local via Ollama)  │
  │  llama3 / mistral /      │
  │  meditron / bio-mistral  │
  └──────────┬──────────────┘
             │
             ▼
  ┌────────────────────────────────────────────────────┐
  │ Clinical Narrative (sent to Streamlit dashboard)    │
  │                                                     │
  │ "⚠️ HIGH RISK — Difficult Intubation Likely         │
  │                                                     │
  │ Key risk factors identified:                        │
  │ • Mallampati Class IV                               │
  │ • Thyromental distance < 6 cm                       │
  │ • Neck circumference > 43 cm                        │
  │ • Limited neck extension (< 80°)                    │
  │ • Obesity (BMI 34 — Obese Class I)                  │
  │                                                     │
  │ Recommendations:                                    │
  │ • Prepare video laryngoscope                        │
  │ • Consider awake fiberoptic intubation              │
  │ • Have emergency front-of-neck airway cart ready    │
  │ • Senior anesthesiologist should be present"        │
  └────────────────────────────────────────────────────┘
```

**Healthcare-specific LLMs (all open-weight, all runnable locally):**

| Model | Size | License | Fits 4GB VRAM? | How to run | Why it's good |
|-------|------|---------|----------------|------------|---------------|
| **QVAC MedPsy** (Tether Data) | **1.7B / 4B** | ✅ Apache 2.0 | ✅ Yes — Q4_K_M GGUF ~2.3 GB | `ollama pull qvac/medpsy` | Built for edge medical deployment, beats models 2-7x its size, dedicated medical reasoning benchmarks |
| **MedGemma** (Google) | **4B / 27B** | ✅ Open weights (free for research) | ✅ Yes — GGUF ~2.6 GB | `ollama pull medgemma` | Trained on medical text + images + EHR. 4B fits easily. MedGemma 1.5 adds CT/MRI understanding |
| **ClinicDx** (built on MedGemma 4B) | **4B** | ✅ Apache 2.0 | ✅ Yes — GGUF 3.9 GB | `ollama pull clinicdx` or llama.cpp | Full CDS system: structured 6-section assessments, WHO guideline citations, EMR-agnostic API |
| **Meissa** | **4B** | ✅ Open weights (HuggingFace) | ✅ Yes (needs vLLM, not Ollama) | `pip install vllm` + HF download | Matches/exceeds GPT-4 on 10/16 medical benchmarks, agentic capabilities (tool use, multi-turn) |
| **Med42-v2** (M42 Health) | **8B / 70B** | ✅ Open weights (HF) | ⚠️ 8B Q4 is ~5 GB — may need CPU offloading | `ollama pull med42` | Built on LLaMA-3, 8B version outperforms GPT-4 on medical QA benchmarks |
| **Open Meditron** (EPFL) | **8B / 70B** | ✅ Fully open (Apache 2.0) | ⚠️ Same as Med42 — 8B needs ~5 GB | `ollama pull meditron` | Fully open pipeline, clinician-audited training corpus |
| **General models (fallback)** | — | ✅ Various | ✅ Yes | Already on your machine | llama3 / mistral / phi-3 work for simple summarization but lack medical-specific training |

**👉 Top recommendation for this project:** **QVAC MedPsy 4B** (Apache 2.0, purpose-built medical, 2.3 GB GGUF, runs directly via your existing Ollama) or **MedGemma 4B** (Google, medical-specialized, 2.6 GB GGUF).

**Why local LLM (Ollama) is the right call for a clinical tool:**
- Patient data never leaves the hospital
- No internet dependency
- No recurring API costs
- HIPAA/GDPR compliant out of the box
- Your machine already has Ollama running (`ollama.exe` detected in system processes)

**What goes into the prompt:**
```
SYSTEM: You are a clinical decision support assistant for anesthesiologists.
Your role is to explain the airway assessment results in plain language
and provide actionable recommendations.

USER:
Prediction: {difficulty_class}
Confidence: {probability}%
Top risk factors (from SHAP):
- {feature_1}: +{contribution}
- {feature_2}: +{contribution}
- {feature_3}: +{contribution}

Patient Profile:
- Age: {age}, Gender: {gender}
- BMI: {bmi} ({bmi_category})
- Mallampati: {score}
- TMD: {tmd_cm} cm
- Neck circumference: {neck_circ} cm
- Comorbidities: {diabetes}, {arthritis}, {down_syndrome}

Explain the situation to the doctor and recommend
specific preparations for intubation.
```

**Dashboard UI layout (Streamlit):**

```
┌─────────────────────────────────────────────────────┐
│  Header: Multimodal Airway Assessment Tool          │
├──────────────────┬──────────────────────────────────┤
│  LEFT PANEL      │  RIGHT PANEL                     │
│                  │                                  │
│  Patient Form    │  LLM Clinical Narrative           │
│  ┌────────────┐  │  ┌────────────────────────────┐  │
│  │ Age: [__]  │  │  │ ⚠️ HIGH RISK               │  │
│  │ Gender: [ ]│  │  │                            │  │
│  │ BMI:  [__] │  │  │ Key risk factors:           │  │
│  │ ...        │  │  │ • Mallampati IV             │  │
│  │            │  │  │ • TMD < 6cm                 │  │
│  │ Upload     │  │  │ • Neck circ > 43cm          │  │
│  │ Images:    │  │  │                            │  │
│  │ [Browse..] │  │  │ Recommendations:            │  │
│  └────────────┘  │  │ • Video laryngoscope        │  │
│                  │  │ • Awake fiberoptic          │  │
│  [PREDICT]       │  │ • Emergency cart ready      │  │
│                  │  └────────────────────────────┘  │
│  Prediction:     │                                  │
│  ┌────────────┐  │  Explanation (SHAP + Grad-CAM)   │
│  │ Difficult  │  │  ┌────────────────────────────┐  │
│  │ 87%        │  │  │ SHAP bar chart              │  │
│  └────────────┘  │  │ Grad-CAM heatmap            │  │
│                  │  └────────────────────────────┘  │
└──────────────────┴──────────────────────────────────┘
```

---

### 15.2 DevOps & Deployment

**Architecture diagram:**

```
                         ┌──────────┐
                         │  GitHub   │
                         │  Actions  │ (CI/CD)
                         └────┬─────┘
                              │ push
                              ▼
                    ┌──────────────────┐
                    │  Container       │
                    │  Registry        │
                    │  (Docker Hub)    │
                    └────────┬─────────┘
                             │ pull
                             ▼
              ┌──────────────────────────────┐
              │        docker-compose         │
              │  (local dev or cloud VM)      │
              │                              │
              │  ┌──────┐  ┌──────┐  ┌────┐ │
              │  │ API  │  │  UI  │  │ LLM│ │
              │  │:8000 │  │:8501 │  │:11434│
              │  └──┬───┘  └──────┘  └────┘ │
              │     │        │               │
              │     └────────┴───────────────┘
              └──────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Cloud Deployment     │
              │ (AWS ECS / Azure)    │
              └──────────────────────┘
```

**Docker Compose (local development):**

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  ui:
    build:
      context: .
      dockerfile: Dockerfile.ui
    ports:
      - "8501:8501"
    depends_on:
      - api
    environment:
      - API_URL=http://api:8000

  llm:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_models:
```

**CI/CD Pipeline (GitHub Actions):**

```yaml
name: Build & Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Lint
        run: pip install black ruff && ruff check src/ && black --check src/

      - name: Test
        run: pip install -r requirements.txt && pytest tests/

      - name: Build & push Docker images
        run: |
          docker build -t api -f Dockerfile.api .
          docker build -t ui -f Dockerfile.ui .
          docker tag api ghcr.io/${{ github.repository }}/api:latest
          docker tag ui ghcr.io/${{ github.repository }}/ui:latest
          docker push ghcr.io/${{ github.repository }}/api:latest
          docker push ghcr.io/${{ github.repository }}/ui:latest

      - name: Deploy to cloud
        run: |
          # AWS ECS / Azure ACI / GCP Cloud Run deploy script
          echo "Deploying..."
```

**Deployment options:**

| Option | Effort | Monthly Cost | Use Case |
|--------|--------|-------------|----------|
| **Local hospital server** (Docker Compose) | Low | Hardware only | On-prem, zero data exposure |
| **Single cloud VM** (AWS EC2 G4dn.xlarge / Azure NCas) | Medium | ~$100-200/mo | MVP / pilot |
| **Kubernetes** (EKS / AKS / GKE) | High | ~$200-500+/mo | Production, HA, auto-scaling |

**Infrastructure choices for the cloud VM approach:**

| Service | GPU Instance | vCPU | RAM | GPU | VRAM | Est. Cost |
|---------|-------------|------|-----|-----|------|-----------|
| AWS | g4dn.xlarge | 4 | 16 GB | T4 | 16 GB | ~$0.526/hr |
| Azure | NCas_T4_v3 | 4 | 28 GB | T4 | 16 GB | ~$0.526/hr |
| GCP | n1-standard-4 + T4 | 4 | 15 GB | T4 | 16 GB | ~$0.473/hr |

**GitHub secrets needed for CI/CD:**
- `GHCR_TOKEN` — to push Docker images
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — if deploying to AWS
- `AZURE_CREDENTIALS` — if deploying to Azure

**Monitoring & observability:**

| Tool | What it monitors |
|------|-----------------|
| **Prometheus** | API request count, latency p50/p95/p99, error rate |
| **Grafana** | Dashboard of all metrics (GPU utilization, memory, prediction throughput) |
| **MLflow** | Model version tracking, inference logs, drift detection |
| **Docker logs** | Application errors, LLM response times |

**Production checklist:**

- [ ] Request/response logging (patient ID, prediction, latency) — HIPAA compliant (no PHI in logs)
- [ ] Rate limiting on API
- [ ] Model versioning via MLflow registry
- [ ] A/B testing route for model comparison
- [ ] Health checks on all containers
- [ ] Auto-restart on failure (Docker restart policy / K8s liveness probes)
- [ ] GPU monitoring (nvidia-smi exporter for Prometheus)
- [ ] Backup strategy for model weights and configs
- [ ] SSL/TLS for API and dashboard
- [ ] Authentication (simple JWT or hospital SSO / LDAP)

---

### 15.3 Updated Directory Structure (additions)

```
├── src/
│   ├── deploy/
│   │   ├── api.py                    # FastAPI app
│   │   ├── frontend.py               # Streamlit UI
│   │   ├── export.py                 # ONNX export
│   │   ├── llm_assistant.py          # Prompt builder + Ollama client
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.ui
│   │   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── deploy.yml                # CI/CD pipeline
├── monitoring/
│   ├── prometheus.yml                # Prometheus config
│   └── grafana/
│       └── dashboard.json            # Prebuilt dashboard
└── requirements.txt                  # Updated with:
                                     #   streamlit, ollama, prometheus-client
```

### 15.4 Quick Start (with LLM)

```bash
# 1. Download local LLM via Ollama
ollama pull llama3

# 2. Run all services
docker-compose up --build

# 3. Open dashboard
open http://localhost:8501

# 4. Enter patient data → Predict → Read LLM narrative
```

---

## 16. PROJECT AGENTS

5 specialized subagents in `.opencode/agent/`:

| Agent | File | Focus area |
|-------|------|-----------|
| **ML Engineer** | `ml-engineer.md` | Model architecture, training, evaluation, explainability |
| **DevOps Engineer** | `devops-engineer.md` | Docker, CI/CD, cloud deployment, monitoring |
| **Frontend Dev** | `frontend-dev.md` | Streamlit dashboard, API, LLM prompt assembly |
| **Backend DB Engineer** | `backend-db-engineer.md` | MongoDB, CRUD, data persistence |
| **Data Scientist** | `data-scientist.md` | Data generation, EDA, synthetic data, validation |

Invoke via `@agent-name` in chat (e.g., `@ml-engineer`).

### Agent architecture summary

```
                    ┌─────────────────────┐
                    │     User Chat        │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ @ml-engineer     │  │ @frontend-dev   │  │ @data-scientist │
│ Models, training │  │ UI, API, LLM    │  │ Data, EDA       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
┌─────────────────┐  ┌─────────────────┐
│ @devops-engineer │  │ @backend-db-    │
│ Docker, CI/CD    │  │ engineer         │
└─────────────────┘  │ MongoDB, CRUD    │
                     └─────────────────┘
```
