from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    admin = "admin"
    doctor = "doctor"
    viewer = "viewer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RoleEnum = RoleEnum.doctor

    @field_validator("password")
    @classmethod
    def _strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one digit")
        return v


class UserOut(BaseModel):
    email: str
    role: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    expires_at: Optional[datetime] = None
    idle_timeout_seconds: Optional[int] = None
    warning_seconds: Optional[int] = None


class HeartbeatOut(BaseModel):
    server_time: datetime
    expires_at: datetime
    idle_timeout_seconds: int
    warning_seconds: int


# patient_id is used in URL paths (/api/patients/{patient_id}) and as a DB key —
# restrict to a conservative identifier charset.
_PATIENT_ID_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"


class PatientCreate(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64, pattern=_PATIENT_ID_PATTERN)
    age: int = Field(ge=0, le=120)
    gender: str = Field(min_length=1, max_length=32)
    bmi: float = Field(ge=10, le=60)
    mallampati: str = Field(min_length=1, max_length=32)
    tmd: float = Field(ge=3, le=12)
    neck_circumference: float = Field(ge=20, le=60)
    comorbidities: Optional[dict] = None

    @field_validator("gender")
    @classmethod
    def _valid_gender(cls, v: str) -> str:
        if v.strip().lower() not in ("male", "female", "other"):
            raise ValueError("gender must be one of: male, female, other")
        return v

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
    patient_id: str = Field(min_length=1, max_length=64, pattern=_PATIENT_ID_PATTERN)
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

    teeth: Optional[str] = Field(default=None, max_length=32)
    chest_size_cm: Optional[float] = Field(default=None, ge=30, le=150)

    @field_validator("gender")
    @classmethod
    def _valid_gender(cls, v: str) -> str:
        if v.strip().lower() not in ("male", "female", "other"):
            raise ValueError("gender must be one of: male, female, other")
        return v

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
    model_version: Optional[str] = None
    created_at: datetime


class LLMReportOut(BaseModel):
    prediction_id: str
    summary: str
    recommendations: str
    summary_source: Optional[str] = None
    recommendations_source: Optional[str] = None
    created_at: datetime

class ImageQualityOut(BaseModel):
    width: int
    height: int
    megapixels: float
    blur_score: float
    brightness_mean: float
    brightness_std: float
    faces: int
    face_area_frac: Optional[float] = None
    usable: bool
    issues: List[str] = Field(default_factory=list)


class ImageGeometryOut(BaseModel):
    iod_px: Optional[float] = None
    mouth_width_px: Optional[float] = None
    mouth_to_iod: Optional[float] = None
    mouth_to_face_w: Optional[float] = None
    yaw_proxy: Optional[float] = None
    roll_proxy: Optional[float] = None
    mouth_dark_frac: Optional[float] = None
    mouth_open_extent: Optional[float] = None


class ImageAnalyzeOut(BaseModel):
    status: str
    redacted: bool
    faces_redacted: int
    quality: ImageQualityOut
    geometry: Optional[ImageGeometryOut] = None
    auto_fill: dict = Field(default_factory=dict)
    auto_fill_note: str
    preview_data_uri: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class ImageViewResultOut(BaseModel):
    status: str
    usable: bool
    issues: List[str] = Field(default_factory=list)
    quality: ImageQualityOut
    geometry: Optional[ImageGeometryOut] = None
    preview_data_uri: Optional[str] = None
    view_metrics: Dict[str, Optional[float]] = Field(default_factory=dict)


class NdmsViewsOut(BaseModel):
    frontal: Optional[ImageViewResultOut] = None
    teeth: Optional[ImageViewResultOut] = None
    tongue: Optional[ImageViewResultOut] = None
    jawline: Optional[ImageViewResultOut] = None


class NdmsComponentOut(BaseModel):
    name: str
    value: float
    weight: float
    note: str


class ImageNdmsOut(BaseModel):
    score: Optional[float] = None
    confidence: float
    views_used: List[str] = Field(default_factory=list)
    missing_views: List[str] = Field(default_factory=list)
    components: List[NdmsComponentOut] = Field(default_factory=list)
    risk_contribution: Optional[float] = None
    blended_risk: Optional[float] = None
    max_contribution: float
    views: NdmsViewsOut
    note: str
