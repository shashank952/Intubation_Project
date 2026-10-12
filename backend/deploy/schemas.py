from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    admin = "admin"
    doctor = "doctor"
    viewer = "viewer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: RoleEnum = RoleEnum.doctor


class UserOut(BaseModel):
    email: str
    role: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PatientCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    age: int = Field(ge=0, le=120)
    gender: str = Field(min_length=1, max_length=32)
    bmi: float = Field(ge=10, le=60)
    mallampati: str = Field(min_length=1, max_length=32)
    tmd: float = Field(ge=3, le=12)
    neck_circumference: float = Field(ge=20, le=60)
    comorbidities: Optional[dict] = None

    @field_validator("comorbidities")
    @classmethod
    def _safe_comorbidities(cls, v):
        if v is None:
            return v
        if len(v) > 50:
            raise ValueError("comorbidities: too many keys")
        for k in v:
            if not isinstance(k, str) or k.startswith("$") or "." in k:
                raise ValueError("comorbidities: invalid key")
        return v


class PatientOut(PatientCreate):
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PredictionInput(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    age: float = Field(ge=0, le=120)
    gender: str = Field(max_length=32)
    bmi: float = Field(ge=10, le=60)
    mallampati_score: float = Field(ge=1, le=4)
    tmd: float = Field(ge=3, le=12)
    neck_circumference: float = Field(ge=20, le=60)
    mouth_opening: Optional[float] = Field(default=40.0, ge=0, le=100)
    smd: Optional[float] = Field(default=14.0, ge=0, le=40)
    neck_movement: Optional[float] = Field(default=85.0, ge=0, le=180)
    previous_airway_records: Optional[str] = "No"
    disease_arthritis: Optional[str] = "No"
    disease_diabetes: Optional[str] = "No"
    disease_down_syndrome: Optional[str] = "No"
    breathing_snoring: Optional[str] = "No"
    breathing_sleep_apnea: Optional[str] = "No"
    symptom_voice_changes: Optional[str] = "No"
    symptom_difficulty_swallowing: Optional[str] = "No"
    symptom_cant_lie_flat: Optional[str] = "No"
    injury_swelling: Optional[str] = "No"
    injury_previous_neck_fracture: Optional[str] = "No"
    previous_emergencies_icu: Optional[str] = "No"
    bmi_category: Optional[str] = "Normal"
    beard: Optional[str] = "No"
    chest_size: Optional[str] = "Medium"
    neck_structure: Optional[str] = "Normal"
    tmd_category: Optional[str] = "Normal"
    jaw_movement: Optional[str] = "Normal"
    neck_movement_category: Optional[str] = "Normal"
    tissue_flexibility: Optional[str] = "Normal"

    @model_validator(mode="after")
    def _limit_string_lengths(self):
        for name, val in self.__dict__.items():
            if isinstance(val, str) and len(val) > 64:
                raise ValueError(f"{name} exceeds 64 characters")
        return self


class PredictionOut(BaseModel):
    id: Optional[str] = None
    patient_id: str
    prediction: str
    confidence: float
    probabilities: dict
    risk_score: float
    created_at: datetime


class LLMReportOut(BaseModel):
    prediction_id: str
    summary: str
    recommendations: str
    summary_source: Optional[str] = None
    recommendations_source: Optional[str] = None
    created_at: datetime
