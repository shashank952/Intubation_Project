from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from collections import defaultdict
import asyncio
import time
import torch
import pandas as pd
import numpy as np
import joblib
from bson import ObjectId
from bson.errors import InvalidId

from ..database import get_db, audit_log
from ..auth import get_current_user, require_role, is_admin
from ..schemas import PredictionInput, PredictionOut, LLMReportOut
from ..config import settings
from ..model_loader import predict_tabular
from .. import real_model, image_analysis
from ..real_model_input import to_model_features
from ..llm_assistant import generate_reports
from backend.data.preprocessing import CATEGORICAL_COLS, NUMERICAL_COLS

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

_scaler = None

_PRED_WINDOW_SECONDS = 60
_MAX_PREDS_PER_WINDOW = 10
_pred_timestamps: dict = defaultdict(list)

_MAX_IMAGE_BYTES = 8 * 1024 * 1024
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def _owner_query(user: dict) -> dict:
    return {} if is_admin(user) else {"owner_id": user["sub"]}


def _enforce_prediction_rate_limit(user: dict) -> None:
    if is_admin(user):
        return
    now = time.time()
    key = user["sub"]
    _pred_timestamps[key] = [t for t in _pred_timestamps[key] if now - t < _PRED_WINDOW_SECONDS]
    if len(_pred_timestamps[key]) >= _MAX_PREDS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many assessments. Try again shortly.")
    _pred_timestamps[key].append(now)


def _get_scaler():
    global _scaler
    if _scaler is None:
        path = Path(__file__).resolve().parent.parent.parent.parent / "checkpoints" / "tabular_scaler.pkl"
        if path.exists():
            _scaler = joblib.load(path)
    return _scaler


def _prepare_input(data: PredictionInput):
    df = pd.DataFrame([{
        "Age": data.age,
        "BMI": data.bmi,
        "Neck_Circumference_cm": data.neck_circumference,
        "Mouth_Opening_mm": data.mouth_opening,
        "Thyromental_Distance_TMD_cm": data.tmd,
        "Sternomental_Distance_SMD_cm": data.smd,
        "Neck_Movement_Degrees": data.neck_movement,
    }])
    scaler = _get_scaler()
    if scaler is not None:
        df[NUMERICAL_COLS] = scaler.transform(df[NUMERICAL_COLS])
    numerical = torch.tensor(df[NUMERICAL_COLS].values, dtype=torch.float32)
    cat_values = {
        "Gender": 1 if data.gender.lower() == "male" else 0,
        "Mallampati_Score": max(0, min(3, int(data.mallampati_score) - 1)),
        "Previous_Airway_Records": 1 if str(getattr(data, "previous_airway_records", "no")).lower() in ("yes","y") else 0,
        "Disease_Arthritis": 1 if str(getattr(data, "disease_arthritis", "no")).lower() in ("yes","y") else 0,
        "Disease_Diabetes": 1 if str(getattr(data, "disease_diabetes", "no")).lower() in ("yes","y") else 0,
        "Disease_Down_Syndrome": 1 if str(getattr(data, "disease_down_syndrome", "no")).lower() in ("yes","y") else 0,
        "Breathing_Snoring": 1 if str(getattr(data, "breathing_snoring", "no")).lower() in ("yes","y") else 0,
        "Breathing_Sleep_Apnea": 1 if str(getattr(data, "breathing_sleep_apnea", "no")).lower() in ("yes","y") else 0,
        "Symptom_Voice_Changes": 1 if str(getattr(data, "symptom_voice_changes", "no")).lower() in ("yes","y") else 0,
        "Symptom_Difficulty_Swallowing": 1 if str(getattr(data, "symptom_difficulty_swallowing", "no")).lower() in ("yes","y") else 0,
        "Symptom_Cant_Lie_Flat": 1 if str(getattr(data, "symptom_cant_lie_flat", "no")).lower() in ("yes","y") else 0,
        "Injury_Swelling": 1 if str(getattr(data, "injury_swelling", "no")).lower() in ("yes","y") else 0,
        "Injury_Previous_Neck_Fracture": 1 if str(getattr(data, "injury_previous_neck_fracture", "no")).lower() in ("yes","y") else 0,
        "Previous_Emergencies_ICU": 1 if str(getattr(data, "previous_emergencies_icu", "no")).lower() in ("yes","y") else 0,
    }
    bmi_val = data.bmi or 0
    if bmi_val < 25:
        bmi_cat_idx = 0  # Normal
    elif bmi_val < 30:
        bmi_cat_idx = 1  # Overweight
    else:
        bmi_cat_idx = 2  # Obese
    cat_values["BMI_Category"] = bmi_cat_idx

    tmd_val = data.tmd or 0
    if tmd_val >= 6.5:
        cat_values["TMD_Category"] = 0  # Easy
    elif tmd_val >= 6.0:
        cat_values["TMD_Category"] = 1  # Medium
    else:
        cat_values["TMD_Category"] = 2  # Difficult

    neck_move_val = data.neck_movement or 0
    if neck_move_val >= 80:
        cat_values["Neck_Movement_Category"] = 0  # Normal
    elif neck_move_val >= 70:
        cat_values["Neck_Movement_Category"] = 1  # Borderline
    else:
        cat_values["Neck_Movement_Category"] = 2  # Risky

    beard_raw = str(getattr(data, "beard", "no")).lower()
    cat_values["Beard"] = 1 if beard_raw in ("yes","y") else 0
    chest_raw = str(getattr(data, "chest_size", "medium")).lower()
    chest_map = {"small": 0, "medium": 0, "large": 1}
    cat_values["Chest_Size"] = chest_map.get(chest_raw, 0)
    neck_struct_raw = str(getattr(data, "neck_structure", "normal")).lower()
    cat_values["Neck_Structure"] = 2 if neck_struct_raw == "abnormal" else 1
    jaw_raw = str(getattr(data, "jaw_movement", "normal")).lower()
    jaw_map = {"normal": 0, "reduced": 1}
    cat_values["Jaw_Movement"] = jaw_map.get(jaw_raw, 0)
    tissue_raw = str(getattr(data, "tissue_flexibility", "normal")).lower()
    cat_values["Tissue_Flexibility"] = 1 if tissue_raw == "reduced" else 0
    categorical = []
    for col in CATEGORICAL_COLS:
        val = cat_values.get(col, 0)
        categorical.append(torch.tensor([val], dtype=torch.long))
    return numerical, categorical


async def _predict_core(
    data: PredictionInput,
    user: dict,
    image_results: Optional[dict] = None,
) -> dict:
    _enforce_prediction_rate_limit(user)
    db = get_db()
    patient = await db.patients.find_one({"patient_id": data.patient_id, **_owner_query(user)})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    imputed_features: list[str] = []
    if settings.prediction_model == "real":
        features, imputed_features = to_model_features(data)
        result = await asyncio.to_thread(real_model.predict, features)
    else:
        numerical, categorical = _prepare_input(data)
        # torch inference is CPU-bound — run off the event loop so concurrent
        # requests don't stall behind one prediction
        result = await asyncio.to_thread(predict_tabular, numerical, categorical)

    prob_score = result["probabilities"]
    weighted = (0 * prob_score.get("Easy", 0) + 50 * prob_score.get("Moderate", 0) + 100 * prob_score.get("Difficult", 0))
    base_risk = round(weighted / 100, 3)

    risk_score = base_risk
    image_fields: dict = {}
    if image_results:
        ndms = image_analysis.compute_ndms(image_results)
        contribution = ndms.get("risk_contribution")
        if contribution is not None:
            blended_pct = image_analysis.blend_risk(round(base_risk * 100, 1), contribution)
            if blended_pct is not None:
                risk_score = round(blended_pct / 100.0, 3)
        image_fields = {
            "ndms_score": ndms.get("score"),
            "ndms_confidence": ndms.get("confidence"),
            "image_contribution": contribution,
            "image_views_used": ndms.get("views_used") or [],
        }

    pred_doc = {
        "patient_id": data.patient_id,
        "owner_id": user["sub"],
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "probabilities": result["probabilities"],
        "risk_score": risk_score,
        "base_risk_score": base_risk,
        "model_version": result.get("model_version"),
        "model_used": settings.prediction_model,
        "imputed_features": imputed_features,
        **image_fields,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = await db.predictions.insert_one(pred_doc)
    pred_doc["id"] = str(insert_result.inserted_id)
    pred_doc.pop("_id", None)

    patient_data = data.model_dump()
    summary, summary_source, recommendations, recommendations_source = await generate_reports(
        result["prediction"], result["confidence"], result["probabilities"], patient_data
    )

    llm_doc = {
        "prediction_id": pred_doc["id"],
        "owner_id": user["sub"],
        "summary": summary or "",
        "recommendations": recommendations or "",
        "summary_source": summary_source,
        "recommendations_source": recommendations_source,
        "created_at": datetime.now(timezone.utc),
    }
    await db.llm_reports.insert_one(llm_doc)
    llm_doc.pop("_id", None)

    await audit_log(db, user["sub"], "predict", "prediction", data.patient_id)

    return {
        "prediction": pred_doc,
        "clinical_summary": summary,
        "recommendations": recommendations,
        "report_sources": {
            "summary": summary_source,
            "recommendations": recommendations_source,
        },
        "model_used": settings.prediction_model,
        "imputed_features": imputed_features,
        "image": image_fields or None,
    }


@router.post("")
async def run_prediction(
    data: PredictionInput, user: dict = Depends(require_role("doctor"))
):
    return await _predict_core(data, user)


@router.post("/with-images")
async def run_prediction_with_images(
    data: str = Form(...),
    frontal: Optional[UploadFile] = File(None),
    teeth: Optional[UploadFile] = File(None),
    tongue: Optional[UploadFile] = File(None),
    jawline: Optional[UploadFile] = File(None),
    user: dict = Depends(require_role("doctor")),
):
    try:
        payload = PredictionInput.model_validate_json(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid prediction payload: {exc}") from exc

    uploads = {"frontal": frontal, "teeth": teeth, "tongue": tongue, "jawline": jawline}
    has_images = any(upload is not None for upload in uploads.values())
    results: dict = {}
    for view, upload in uploads.items():
        if upload is None:
            results[view] = None
            continue
        if upload.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Only JPEG or PNG images are accepted.")
        contents = await upload.read(_MAX_IMAGE_BYTES + 1)
        if not contents:
            raise HTTPException(status_code=400, detail=f"Empty upload for {view}.")
        if len(contents) > _MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Image exceeds the 8 MB limit.")
        try:
            results[view] = await asyncio.to_thread(image_analysis.analyze, contents, view)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Image analysis is unavailable.") from exc

    return await _predict_core(payload, user, image_results=results if has_images else None)


_MAX_LIST_LIMIT = 200


@router.get("", response_model=List[PredictionOut])
async def list_predictions(
    patient_id: str = None, skip: int = 0, limit: int = 50,
    user: dict = Depends(get_current_user),
):
    skip = max(0, skip)
    limit = max(0, min(limit, _MAX_LIST_LIMIT))
    db = get_db()
    query = _owner_query(user)
    if patient_id:
        query["patient_id"] = patient_id
    cursor = db.predictions.find(query).skip(skip).limit(limit).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(PredictionOut(**doc))
    return results


@router.get("/{prediction_id}/report", response_model=LLMReportOut)
async def get_llm_report(prediction_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.llm_reports.find_one({"prediction_id": prediction_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found")
    if not is_admin(user) and doc.get("owner_id") and doc["owner_id"] != user["sub"]:
        raise HTTPException(status_code=404, detail="Report not found")
    return LLMReportOut(**doc)


@router.delete("/{prediction_id}", status_code=204)
async def delete_prediction(
    prediction_id: str, user: dict = Depends(require_role("admin"))
):
    db = get_db()
    try:
        oid = ObjectId(prediction_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid prediction id")
    pred = await db.predictions.delete_one({"_id": oid})
    if pred.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prediction not found")
    await db.llm_reports.delete_one({"prediction_id": prediction_id})
    await audit_log(db, user["sub"], "delete", "prediction", prediction_id)
    return None


@router.get("/export/csv")
async def export_csv(user: dict = Depends(require_role("doctor"))):
    from fastapi.responses import StreamingResponse
    import io, csv

    db = get_db()
    cursor = db.predictions.find(_owner_query(user), {"_id": 0}).sort("created_at", -1)
    rows = await cursor.to_list(length=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(row.values())
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=predictions.csv"},
    )
