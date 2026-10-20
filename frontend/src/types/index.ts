export interface User {
  email: string;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Patient {
  patient_id: string;
  age: number;
  gender: string;
  bmi: number;
  mallampati: string;
  tmd: number;
  neck_circumference: number;
  comorbidities?: Record<string, string>;
  created_at: string;
}

export interface PredictionInput {
  patient_id: string;
  age: number;
  gender: string;
  bmi: number;
  mallampati_score: number;
  tmd: number;
  neck_circumference: number;
  mouth_opening?: number;
  smd?: number;
  neck_movement?: number;
  previous_airway_records?: string;
  disease_arthritis?: string;
  disease_diabetes?: string;
  disease_down_syndrome?: string;
  breathing_snoring?: string;
  breathing_sleep_apnea?: string;
  symptom_voice_changes?: string;
  symptom_difficulty_swallowing?: string;
  symptom_cant_lie_flat?: string;
  injury_swelling?: string;
  injury_previous_neck_fracture?: string;
  previous_emergencies_icu?: string;
  bmi_category?: string;
  beard?: string;
  chest_size?: string;
  neck_structure?: string;
  tmd_category?: string;
  jaw_movement?: string;
  neck_movement_category?: string;
  tissue_flexibility?: string;
}

export interface PredictionResult {
  prediction: string;
  confidence: number;
  risk_score: number;
  probabilities: Record<string, number>;
}

export interface PredictionResponse {
  prediction: PredictionResult;
  clinical_summary: string;
  recommendations: string;
  report_sources?: { summary?: string; recommendations?: string };
}

export interface PredictionHistory {
  id: string;
  patient_id: string;
  prediction: string;
  confidence: number;
  risk_score: number;
  probabilities: Record<string, number>;
  created_at: string;
}

export interface LLMReport {
  prediction_id: string;
  summary: string;
  recommendations: string;
  summary_source?: string;
  recommendations_source?: string;
  created_at: string;
}

export interface LlmStatus {
  connected: boolean;
  model: string;
  latency_ms: number | null;
}
