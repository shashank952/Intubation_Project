import type { PredictionHistory, PredictionResponse, LLMReport } from '@/types';

export const DEMO_USER = { email: 'doctor1@demo.airwaymd', role: 'doctor' };

export const DEMO_HISTORY: PredictionHistory[] = [
  {
    id: 'demo-1',
    patient_id: 'P-2024-0001',
    prediction: 'Difficult',
    confidence: 0.91,
    risk_score: 0.87,
    probabilities: { Easy: 0.03, Moderate: 0.06, Difficult: 0.91 },
    created_at: '2026-10-18T09:24:00.000Z',
  },
  {
    id: 'demo-2',
    patient_id: 'P-2024-0002',
    prediction: 'Easy',
    confidence: 0.95,
    risk_score: 0.08,
    probabilities: { Easy: 0.95, Moderate: 0.04, Difficult: 0.01 },
    created_at: '2026-10-17T14:02:00.000Z',
  },
  {
    id: 'demo-3',
    patient_id: 'P-2024-0003',
    prediction: 'Moderate',
    confidence: 0.78,
    risk_score: 0.55,
    probabilities: { Easy: 0.15, Moderate: 0.78, Difficult: 0.07 },
    created_at: '2026-10-16T11:47:00.000Z',
  },
  {
    id: 'demo-4',
    patient_id: 'P-2024-0004',
    prediction: 'Easy',
    confidence: 0.89,
    risk_score: 0.12,
    probabilities: { Easy: 0.89, Moderate: 0.08, Difficult: 0.03 },
    created_at: '2026-10-15T16:10:00.000Z',
  },
  {
    id: 'demo-5',
    patient_id: 'P-2024-0005',
    prediction: 'Difficult',
    confidence: 0.84,
    risk_score: 0.79,
    probabilities: { Easy: 0.05, Moderate: 0.11, Difficult: 0.84 },
    created_at: '2026-10-14T08:33:00.000Z',
  },
  {
    id: 'demo-6',
    patient_id: 'P-2024-0006',
    prediction: 'Moderate',
    confidence: 0.71,
    risk_score: 0.49,
    probabilities: { Easy: 0.22, Moderate: 0.71, Difficult: 0.07 },
    created_at: '2026-10-13T13:05:00.000Z',
  },
];

export const DEMO_RESULT: PredictionResponse = {
  prediction: {
    prediction: 'Moderate',
    confidence: 0.82,
    risk_score: 0.58,
    probabilities: { Easy: 0.11, Moderate: 0.82, Difficult: 0.07 },
  },
  clinical_summary:
    'Mallampati class III with reduced thyromental distance suggests moderately limited laryngeal view.\nNeck circumference and BMI indicate elevated soft-tissue obstruction risk.\nNo prior difficult intubation documented.',
  recommendations:
    'Pre-oxygenate thoroughly and position with ramped head elevation.\nPrepare video laryngoscopy and a supraglottic airway as backup.\nHave an experienced airway operator immediately available.\nConsider awake fibreoptic intubation if the airway exam worsens.',
  report_sources: { summary: 'llm', recommendations: 'llm' },
};

export const DEMO_REPORT: LLMReport = {
  prediction_id: 'demo-3',
  summary:
    'Mallampati class III with reduced thyromental distance suggests moderately limited laryngeal view.\nNeck circumference and BMI indicate elevated soft-tissue obstruction risk.\nNo prior difficult intubation documented.',
  recommendations:
    'Pre-oxygenate thoroughly and position with ramped head elevation.\nPrepare video laryngoscopy and a supraglottic airway as backup.\nHave an experienced airway operator immediately available.',
  summary_source: 'llm',
  recommendations_source: 'llm',
  created_at: '2026-10-16T11:47:00.000Z',
};
