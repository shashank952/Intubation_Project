from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from typing import List
from datetime import datetime, timezone
import torch
import pandas as pd
import numpy as np
import joblib
from bson import ObjectId
from bson.errors import InvalidId

from ..database import get_db
from ..auth import get_current_user, require_role
from ..schemas import PredictionInput, PredictionOut, LLMReportOut
from ..model_loader import predict_tabular
from ..llm_assistant import generate_reports
from backend.data.preprocessing import CATEGORICAL_COLS, NUMERICAL_COLS

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

_scaler = None


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


@router.post("")
async def run_prediction(
    data: PredictionInput, user: dict = Depends(require_role("doctor"))
):
    db = get_db()
    patient = await db.patients.find_one({"patient_id": data.patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    numerical, categorical = _prepare_input(data)
    result = predict_tabular(numerical, categorical)

    prob_score = result["probabilities"]
    weighted = (0 * prob_score.get("Easy", 0) + 50 * prob_score.get("Moderate", 0) + 100 * prob_score.get("Difficult", 0))
    risk_score = round(weighted / 100, 3)

    pred_doc = {
        "patient_id": data.patient_id,
        "prediction": result["prediction"],
        "confidence": result["confidence"],
        "probabilities": result["probabilities"],
        "risk_score": risk_score,
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
        "summary": summary or "",
        "recommendations": recommendations or "",
        "summary_source": summary_source,
        "recommendations_source": recommendations_source,
        "created_at": datetime.now(timezone.utc),
    }
    await db.llm_reports.insert_one(llm_doc)
    llm_doc.pop("_id", None)

    return {
        "prediction": pred_doc,
        "clinical_summary": summary,
        "recommendations": recommendations,
        "report_sources": {
            "summary": summary_source,
            "recommendations": recommendations_source,
        },
    }


@router.get("", response_model=List[PredictionOut])
async def list_predictions(
    patient_id: str = None, skip: int = 0, limit: int = 50,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    query = {}
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
    return None


@router.get("/export/csv")
async def export_csv(user: dict = Depends(require_role("doctor"))):
    from fastapi.responses import StreamingResponse
    import io, csv

    db = get_db()
    cursor = db.predictions.find({}, {"_id": 0}).sort("created_at", -1)
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
