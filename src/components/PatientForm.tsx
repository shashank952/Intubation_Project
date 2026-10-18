'use client';

import { useState, FormEvent, useEffect } from 'react';
import { Activity, User, Stethoscope, ClipboardList, AlertCircle, Info, FlaskConical, Shuffle, ChevronDown, History } from 'lucide-react';
import type { PredictionInput } from '@/types';
import clsx from 'clsx';

interface PatientFormProps {
  onSubmit: (data: PredictionInput) => void;
  loading: boolean;
  initialData?: PredictionInput | null;
  compact?: boolean;
}

interface FormErrors {
  [key: string]: string;
}

const defaultFormData: PredictionInput = {
  patient_id: '',
  age: 0,
  gender: '',
  bmi: 0,
  mallampati_score: 0,
  tmd: 0,
  neck_circumference: 0,
  mouth_opening: 40,
  smd: 14,
  neck_movement: 85,
  beard: 'No',
  chest_size: 'Medium',
  neck_structure: 'Normal',
  jaw_movement: 'Normal',
  tissue_flexibility: 'Normal',
  previous_airway_records: 'No',
  disease_arthritis: 'No',
  disease_diabetes: 'No',
  disease_down_syndrome: 'No',
  breathing_snoring: 'No',
  breathing_sleep_apnea: 'No',
  symptom_voice_changes: 'No',
  symptom_difficulty_swallowing: 'No',
  symptom_cant_lie_flat: 'No',
  injury_swelling: 'No',
  injury_previous_neck_fracture: 'No',
  previous_emergencies_icu: 'No',
};

export default function PatientForm({ onSubmit, loading, initialData, compact }: PatientFormProps) {
  const [formData, setFormData] = useState<PredictionInput>(defaultFormData);
  const [errors, setErrors] = useState<FormErrors>({});
  const [activeSection, setActiveSection] = useState('demographics');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    setFormData(initialData ? { ...initialData } : { ...defaultFormData });
    setErrors({});
    setActiveSection('demographics');
    setShowAdvanced(false);
  }, [initialData]);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!formData.patient_id.trim()) newErrors.patient_id = 'Required';
    if (!formData.age || formData.age < 0 || formData.age > 120) newErrors.age = '0\u2013120';
    if (!formData.gender) newErrors.gender = 'Required';
    if (!formData.bmi || formData.bmi < 10 || formData.bmi > 60) newErrors.bmi = '10\u201360';
    if (!formData.mallampati_score || formData.mallampati_score < 1 || formData.mallampati_score > 4)
      newErrors.mallampati_score = '1\u20134 required';
    if (!formData.tmd || formData.tmd < 3 || formData.tmd > 12) newErrors.tmd = '3\u201312 cm';
    if (!formData.neck_circumference || formData.neck_circumference < 20 || formData.neck_circumference > 60)
      newErrors.neck_circumference = '20\u201360 cm';
    if (formData.mouth_opening === undefined || formData.mouth_opening < 10 || formData.mouth_opening > 80)
      newErrors.mouth_opening = '10\u201380 mm';
    if (formData.smd === undefined || formData.smd < 3 || formData.smd > 20)
      newErrors.smd = '3\u201320 cm';
    if (formData.neck_movement === undefined || formData.neck_movement < 30 || formData.neck_movement > 180)
      newErrors.neck_movement = '30\u2013180\u00b0';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit({
        ...formData,
        age: Number(formData.age),
        bmi: Number(formData.bmi),
        mallampati_score: Number(formData.mallampati_score),
        tmd: Number(formData.tmd),
        neck_circumference: Number(formData.neck_circumference),
        mouth_opening: Number(formData.mouth_opening),
        smd: Number(formData.smd),
        neck_movement: Number(formData.neck_movement),
      });
    }
  };

  const handleChange = (field: keyof PredictionInput, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
  };

  const inputClass = (field: string) =>
    clsx(
      'w-full px-3 py-2 text-sm rounded-[4px] border-2 bg-white dark:bg-neutral-800 transition-smooth focus:outline-none focus:ring-2 shadow-[5px_5px_0_#111111] dark:shadow-[5px_5px_0_#3F3F46]',
      errors[field]
        ? 'border-danger-500 focus:ring-danger-300 dark:border-danger-500'
        : 'border-black dark:border-neutral-600 focus:ring-brand-300 focus:border-brand-400 dark:focus:border-brand-400 hover:border-neutral-300 dark:hover:border-neutral-500'
    );

  const labelClass = 'block text-xs font-medium text-neutral-600 dark:text-neutral-300 mb-1.5';
  const sectionTab = (id: string, label: string, icon: React.ElementType) => {
    const Icon = icon;
    return (
      <button
        type="button"
        onClick={() => setActiveSection(id)}
        className={clsx(
          'flex flex-1 items-center justify-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-[3px] transition-smooth whitespace-nowrap',
          activeSection === id
            ? 'bg-brand-500 text-black shadow-[2px_2px_0_#111111]'
            : 'text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200/70 dark:hover:bg-neutral-700'
        )}
      >
        <Icon className="h-3.5 w-3.5" />
        {label}
      </button>
    );
  };

  const yesNoSelect = (field: keyof PredictionInput, label: string) => (
    <div>
      <label className={labelClass}>{label}</label>
      <select value={formData[field] as string} onChange={(e) => handleChange(field, e.target.value)}
        className={inputClass(field as string)}>
        <option value="No">No</option>
        <option value="Yes">Yes</option>
      </select>
    </div>
  );

  const generateRandomData = (): PredictionInput => {
    const genders = ['Male', 'Female'];
    const gender = genders[Math.random() < 0.5 ? 0 : 1];
    const age = Math.round(30 + Math.random() * 40 + (Math.random() < 0.3 ? 10 : 0));
    const bmi = Math.round((18 + Math.random() * 30 + (Math.random() < 0.4 ? 5 : 0)) * 10) / 10;
    const neck_circ = Math.round((28 + bmi * 0.35 + (Math.random() - 0.5) * 4) * 10) / 10;
    const mallampati_raw = bmi < 25
      ? (Math.random() < 0.4 ? 1 : Math.random() < 0.6 ? 2 : Math.random() < 0.7 ? 3 : 4)
      : bmi < 30
      ? (Math.random() < 0.2 ? 1 : Math.random() < 0.5 ? 2 : Math.random() < 0.8 ? 3 : 4)
      : (Math.random() < 0.1 ? 1 : Math.random() < 0.3 ? 2 : Math.random() < 0.6 ? 3 : 4);
    const mallampati_score = Math.min(4, Math.max(1, mallampati_raw));
    const tmd = Math.round(Math.max(3.5, Math.min(11, 8.5 - mallampati_score * 0.5 + (Math.random() - 0.5) * 1.5)) * 10) / 10;
    const mouth_opening = Math.round((35 + Math.random() * 20 + (mallampati_score > 3 ? -5 : 0)) * 10) / 10;
    const smd = Math.round((12 + Math.random() * 5 + (tmd < 6 ? -1 : 0)) * 10) / 10;
    const neck_movement = Math.round((70 + Math.random() * 30 + (bmi > 30 ? -10 : 0)) * 10) / 10;
    const beard = gender === 'Male' ? (Math.random() < 0.35 ? 'Yes' : 'No') : 'No';
    const chest_size = bmi < 25 ? 'Small' : bmi < 30 ? 'Medium' : 'Large';
    const neck_structure = bmi < 25 ? 'Normal' : (Math.random() < 0.4 ? 'Normal' : 'Abnormal');
    const jaw_movement = Math.random() < 0.75 ? 'Normal' : 'Reduced';
    const tissue_flexibility = Math.random() < 0.65 ? 'Normal' : 'Reduced';
    const prob = (p: number) => Math.random() < p;
    const previous_airway_records = prob(0.15) ? 'Yes' : 'No';
    const disease_arthritis = prob(Math.min(0.02 + age * 0.004, 0.8)) ? 'Yes' : 'No';
    const disease_diabetes = prob(Math.min(0.03 + age * 0.005, 0.8)) ? 'Yes' : 'No';
    const disease_down_syndrome = prob(0.005) ? 'Yes' : 'No';
    const breathing_snoring = prob(Math.min(0.2 + (bmi - 15) * 0.015, 0.85)) ? 'Yes' : 'No';
    const breathing_sleep_apnea = prob(Math.min(0.05 + (bmi - 15) * 0.008, 0.6)) ? 'Yes' : 'No';
    const symptom_voice_changes = prob(0.1) ? 'Yes' : 'No';
    const symptom_difficulty_swallowing = prob(0.15) ? 'Yes' : 'No';
    const symptom_cant_lie_flat = prob(0.12) ? 'Yes' : 'No';
    const injury_swelling = prob(0.08) ? 'Yes' : 'No';
    const injury_previous_neck_fracture = prob(0.03) ? 'Yes' : 'No';
    const previous_emergencies_icu = prob(0.12) ? 'Yes' : 'No';
    return {
      patient_id: `RAND-${Math.floor(1000 + Math.random() * 9000)}`,
      age, gender, bmi, mallampati_score, tmd, neck_circumference: neck_circ,
      mouth_opening, smd, neck_movement,
      beard, chest_size, neck_structure, jaw_movement, tissue_flexibility,
      previous_airway_records, disease_arthritis, disease_diabetes, disease_down_syndrome,
      breathing_snoring, breathing_sleep_apnea, symptom_voice_changes,
      symptom_difficulty_swallowing, symptom_cant_lie_flat, injury_swelling,
      injury_previous_neck_fracture, previous_emergencies_icu,
    };
  };

  const pad = compact ? 'p-3' : 'p-4';

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card">
      {!compact && (
        <div className="px-4 py-3 border-b-2 border-black dark:border-neutral-600">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-[4px] bg-brand-50 dark:bg-brand-950/30 flex items-center justify-center">
                <Activity className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
              </div>
              <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">Patient Entry</span>
            </div>
            <div className="flex gap-1">
              <button type="button" onClick={() => { handleChange('patient_id', 'TEST-EASY-001'); handleChange('age', '54'); handleChange('gender', 'Female'); handleChange('bmi', '23.7'); handleChange('mallampati_score', '1'); handleChange('tmd', '7.6'); handleChange('neck_circumference', '36.4'); handleChange('mouth_opening', '43.7'); handleChange('smd', '16.1'); handleChange('neck_movement', '96.4'); handleChange('previous_airway_records', 'No'); handleChange('disease_arthritis', 'No'); handleChange('disease_diabetes', 'No'); handleChange('disease_down_syndrome', 'No'); handleChange('breathing_snoring', 'No'); handleChange('breathing_sleep_apnea', 'No'); handleChange('symptom_voice_changes', 'No'); handleChange('symptom_difficulty_swallowing', 'No'); handleChange('symptom_cant_lie_flat', 'No'); handleChange('injury_swelling', 'No'); handleChange('injury_previous_neck_fracture', 'No'); handleChange('previous_emergencies_icu', 'No'); setErrors({}); setActiveSection('demographics'); }}
                title="Load easy test patient"
                className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded-[3px] border-2 border-black bg-success-100 text-success-800 hover:bg-success-200 transition-smooth">
                <FlaskConical className="h-2.5 w-2.5" /> E
              </button>
              <button type="button" onClick={() => { handleChange('patient_id', 'TEST-MOD-001'); handleChange('age', '54'); handleChange('gender', 'Female'); handleChange('bmi', '32.9'); handleChange('mallampati_score', '4'); handleChange('tmd', '6.1'); handleChange('neck_circumference', '39.2'); handleChange('mouth_opening', '50.9'); handleChange('smd', '15.7'); handleChange('neck_movement', '93.2'); handleChange('previous_airway_records', 'No'); handleChange('disease_arthritis', 'No'); handleChange('disease_diabetes', 'No'); handleChange('disease_down_syndrome', 'No'); handleChange('breathing_snoring', 'Yes'); handleChange('breathing_sleep_apnea', 'No'); handleChange('symptom_voice_changes', 'No'); handleChange('symptom_difficulty_swallowing', 'No'); handleChange('symptom_cant_lie_flat', 'Yes'); handleChange('injury_swelling', 'No'); handleChange('injury_previous_neck_fracture', 'No'); handleChange('previous_emergencies_icu', 'No'); setErrors({}); setActiveSection('demographics'); }}
                title="Load moderate test patient"
                className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded-[3px] border-2 border-black bg-warning-100 text-warning-800 hover:bg-warning-200 transition-smooth">
                <FlaskConical className="h-2.5 w-2.5" /> M
              </button>
              <button type="button" onClick={() => { handleChange('patient_id', 'TEST-DIFF-001'); handleChange('age', '58'); handleChange('gender', 'Female'); handleChange('bmi', '50.0'); handleChange('mallampati_score', '4'); handleChange('tmd', '5.7'); handleChange('neck_circumference', '46.8'); handleChange('mouth_opening', '40.0'); handleChange('smd', '18.4'); handleChange('neck_movement', '81.2'); handleChange('previous_airway_records', 'Yes'); handleChange('disease_arthritis', 'No'); handleChange('disease_diabetes', 'Yes'); handleChange('disease_down_syndrome', 'No'); handleChange('breathing_snoring', 'Yes'); handleChange('breathing_sleep_apnea', 'Yes'); handleChange('symptom_voice_changes', 'No'); handleChange('symptom_difficulty_swallowing', 'Yes'); handleChange('symptom_cant_lie_flat', 'Yes'); handleChange('injury_swelling', 'Yes'); handleChange('injury_previous_neck_fracture', 'No'); handleChange('previous_emergencies_icu', 'Yes'); setErrors({}); setActiveSection('demographics'); }}
                title="Load difficult test patient"
                className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded-[3px] border-2 border-black bg-danger-100 text-danger-800 hover:bg-danger-200 transition-smooth">
                <FlaskConical className="h-2.5 w-2.5" /> D
              </button>
              <button type="button" onClick={() => { setFormData(generateRandomData()); setErrors({}); setActiveSection('demographics'); }}
                title="Load random test patient"
                className="flex items-center gap-1 px-2.5 py-1 text-[10px] font-semibold rounded-[3px] border-2 border-black bg-neutral-100 text-neutral-700 hover:bg-neutral-200 transition-smooth">
                <Shuffle className="h-2.5 w-2.5" />
              </button>
            </div>
          </div>
          <div className="flex gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-[4px] border-2 border-black dark:border-neutral-600 overflow-x-auto no-scrollbar">
            {sectionTab('demographics', 'Basic', User)}
            {sectionTab('airway', 'Airway', Stethoscope)}
            {sectionTab('physical', 'Physical', ClipboardList)}
            {sectionTab('history', 'History', History)}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className={pad}>
        {compact ? (
          <div className="space-y-4">
            <div>
              <label htmlFor="patient_id" className={labelClass}>Patient ID <span className="text-danger-500">*</span></label>
              <input id="patient_id" type="text" placeholder="e.g. P-2024-0001"
                value={formData.patient_id} onChange={(e) => handleChange('patient_id', e.target.value)}
                className={inputClass('patient_id')} />
              {errors.patient_id && <p className="mt-0.5 text-[10px] text-danger-500">{errors.patient_id}</p>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label htmlFor="age" className={labelClass}>Age</label>
                <input id="age" type="number" min={0} max={120} placeholder="45"
                  value={formData.age || ''} onChange={(e) => handleChange('age', e.target.value)}
                  className={inputClass('age')} />
                {errors.age && <p className="mt-0.5 text-[10px] text-danger-500">{errors.age}</p>}
              </div>
              <div>
                <label htmlFor="gender" className={labelClass}>Gender</label>
                <select id="gender" value={formData.gender} onChange={(e) => handleChange('gender', e.target.value)} className={inputClass('gender')}>
                  <option value="">Select</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
                {errors.gender && <p className="mt-0.5 text-[10px] text-danger-500">{errors.gender}</p>}
              </div>
              <div>
                <label htmlFor="bmi" className={labelClass}>BMI</label>
                <input id="bmi" type="number" min={10} max={60} step={0.1} placeholder="28.5"
                  value={formData.bmi || ''} onChange={(e) => handleChange('bmi', e.target.value)}
                  className={inputClass('bmi')} />
                {errors.bmi && <p className="mt-0.5 text-[10px] text-danger-500">{errors.bmi}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="mallampati" className={labelClass}>Mallampati</label>
                <select id="mallampati" value={formData.mallampati_score || ''}
                  onChange={(e) => handleChange('mallampati_score', e.target.value)}
                  className={inputClass('mallampati_score')}>
                  <option value="">Select</option>
                  <option value="1">I</option><option value="2">II</option><option value="3">III</option><option value="4">IV</option>
                </select>
                {errors.mallampati_score && <p className="mt-0.5 text-[10px] text-danger-500">{errors.mallampati_score}</p>}
              </div>
              <div>
                <label htmlFor="tmd" className={labelClass}>TMD (cm)</label>
                <input id="tmd" type="number" min={3} max={12} step={0.1} placeholder="6.5"
                  value={formData.tmd || ''} onChange={(e) => handleChange('tmd', e.target.value)}
                  className={inputClass('tmd')} />
                {errors.tmd && <p className="mt-0.5 text-[10px] text-danger-500">{errors.tmd}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="neck" className={labelClass}>Neck (cm)</label>
                <input id="neck" type="number" min={20} max={60} step={0.1} placeholder="38.0"
                  value={formData.neck_circumference || ''} onChange={(e) => handleChange('neck_circumference', e.target.value)}
                  className={inputClass('neck_circumference')} />
                {errors.neck_circumference && <p className="mt-0.5 text-[10px] text-danger-500">{errors.neck_circumference}</p>}
              </div>
              <div>
                <label htmlFor="mouth_opening" className={labelClass}>Mouth (mm)</label>
                <input id="mouth_opening" type="number" min={10} max={80} step={0.5} placeholder="40.0"
                  value={formData.mouth_opening || ''} onChange={(e) => handleChange('mouth_opening', e.target.value)}
                  className={inputClass('mouth_opening')} />
                {errors.mouth_opening && <p className="mt-0.5 text-[10px] text-danger-500">{errors.mouth_opening}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="smd" className={labelClass}>SMD (cm)</label>
                <input id="smd" type="number" min={3} max={20} step={0.1} placeholder="14.0"
                  value={formData.smd || ''} onChange={(e) => handleChange('smd', e.target.value)}
                  className={inputClass('smd')} />
                {errors.smd && <p className="mt-0.5 text-[10px] text-danger-500">{errors.smd}</p>}
              </div>
              <div>
                <label htmlFor="neck_movement" className={labelClass}>Neck (&deg;)</label>
                <input id="neck_movement" type="number" min={30} max={180} step={1} placeholder="85"
                  value={formData.neck_movement || ''} onChange={(e) => handleChange('neck_movement', e.target.value)}
                  className={inputClass('neck_movement')} />
                {errors.neck_movement && <p className="mt-0.5 text-[10px] text-danger-500">{errors.neck_movement}</p>}
              </div>
            </div>
            <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1 text-[10px] font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 transition-smooth">
              <ChevronDown className={clsx('h-3 w-3 transition-transform', showAdvanced && 'rotate-180')} />
              {showAdvanced ? 'Less' : 'More'}
            </button>
            {showAdvanced && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Beard</label>
                  <select value={formData.beard} onChange={(e) => handleChange('beard', e.target.value)} className={inputClass('beard')}>
                    <option value="No">No</option><option value="Yes">Yes</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Chest</label>
                  <select value={formData.chest_size} onChange={(e) => handleChange('chest_size', e.target.value)} className={inputClass('chest_size')}>
                    <option value="Small">Small</option><option value="Medium">Medium</option><option value="Large">Large</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Neck</label>
                  <select value={formData.neck_structure} onChange={(e) => handleChange('neck_structure', e.target.value)} className={inputClass('neck_structure')}>
                    <option value="Normal">Normal</option><option value="Abnormal">Abnormal</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Jaw</label>
                  <select value={formData.jaw_movement} onChange={(e) => handleChange('jaw_movement', e.target.value)} className={inputClass('jaw_movement')}>
                    <option value="Normal">Normal</option><option value="Reduced">Reduced</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Tissue</label>
                  <select value={formData.tissue_flexibility} onChange={(e) => handleChange('tissue_flexibility', e.target.value)} className={inputClass('tissue_flexibility')}>
                    <option value="Normal">Normal</option><option value="Reduced">Reduced</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            {activeSection === 'demographics' && (
              <div className="space-y-4">
                <div>
                  <label htmlFor="patient_id" className={labelClass}>Patient ID <span className="text-danger-500">*</span></label>
                  <input id="patient_id" type="text" placeholder="e.g. P-2024-0001"
                    value={formData.patient_id} onChange={(e) => handleChange('patient_id', e.target.value)}
                    className={inputClass('patient_id')} />
                  {errors.patient_id && <p className="mt-0.5 text-[10px] text-danger-500">{errors.patient_id}</p>}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label htmlFor="age" className={labelClass}>Age</label>
                    <input id="age" type="number" min={0} max={120} placeholder="45"
                      value={formData.age || ''} onChange={(e) => handleChange('age', e.target.value)}
                      className={inputClass('age')} />
                    {errors.age && <p className="mt-0.5 text-[10px] text-danger-500">{errors.age}</p>}
                  </div>
                  <div>
                    <label htmlFor="gender" className={labelClass}>Gender</label>
                    <select id="gender" value={formData.gender} onChange={(e) => handleChange('gender', e.target.value)} className={inputClass('gender')}>
                      <option value="">Select</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>
                    {errors.gender && <p className="mt-0.5 text-[10px] text-danger-500">{errors.gender}</p>}
                  </div>
                  <div>
                    <label htmlFor="bmi" className={labelClass}>BMI</label>
                    <input id="bmi" type="number" min={10} max={60} step={0.1} placeholder="28.5"
                      value={formData.bmi || ''} onChange={(e) => handleChange('bmi', e.target.value)}
                      className={inputClass('bmi')} />
                    {errors.bmi && <p className="mt-0.5 text-[10px] text-danger-500">{errors.bmi}</p>}
                  </div>
                </div>
              </div>
            )}
            {activeSection === 'airway' && (
              <div className="space-y-4">
                <div>
                  <label htmlFor="mallampati" className={labelClass}>Mallampati Score</label>
                  <select id="mallampati" value={formData.mallampati_score || ''}
                    onChange={(e) => handleChange('mallampati_score', e.target.value)}
                    className={inputClass('mallampati_score')}>
                    <option value="">Select</option>
                    <option value="1">Class I</option><option value="2">Class II</option><option value="3">Class III</option><option value="4">Class IV</option>
                  </select>
                  {errors.mallampati_score && <p className="mt-0.5 text-[10px] text-danger-500">{errors.mallampati_score}</p>}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="tmd" className={labelClass}>TMD (cm)</label>
                    <input id="tmd" type="number" min={3} max={12} step={0.1} placeholder="6.5"
                      value={formData.tmd || ''} onChange={(e) => handleChange('tmd', e.target.value)}
                      className={inputClass('tmd')} />
                    {errors.tmd && <p className="mt-0.5 text-[10px] text-danger-500">{errors.tmd}</p>}
                  </div>
                  <div>
                    <label htmlFor="smd" className={labelClass}>SMD (cm)</label>
                    <input id="smd" type="number" min={3} max={20} step={0.1} placeholder="14.0"
                      value={formData.smd || ''} onChange={(e) => handleChange('smd', e.target.value)}
                      className={inputClass('smd')} />
                    {errors.smd && <p className="mt-0.5 text-[10px] text-danger-500">{errors.smd}</p>}
                  </div>
                </div>
              </div>
            )}
            {activeSection === 'physical' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="neck" className={labelClass}>Neck Circ (cm)</label>
                    <input id="neck" type="number" min={20} max={60} step={0.1} placeholder="38.0"
                      value={formData.neck_circumference || ''} onChange={(e) => handleChange('neck_circumference', e.target.value)}
                      className={inputClass('neck_circumference')} />
                    {errors.neck_circumference && <p className="mt-0.5 text-[10px] text-danger-500">{errors.neck_circumference}</p>}
                  </div>
                  <div>
                    <label htmlFor="mouth_opening" className={labelClass}>Mouth (mm)</label>
                    <input id="mouth_opening" type="number" min={10} max={80} step={0.5} placeholder="40.0"
                      value={formData.mouth_opening || ''} onChange={(e) => handleChange('mouth_opening', e.target.value)}
                      className={inputClass('mouth_opening')} />
                    {errors.mouth_opening && <p className="mt-0.5 text-[10px] text-danger-500">{errors.mouth_opening}</p>}
                  </div>
                </div>
                <div>
                  <label htmlFor="neck_movement" className={labelClass}>Neck (&deg;)</label>
                  <input id="neck_movement" type="number" min={30} max={180} step={1} placeholder="85"
                    value={formData.neck_movement || ''} onChange={(e) => handleChange('neck_movement', e.target.value)}
                    className={inputClass('neck_movement')} />
                  {errors.neck_movement && <p className="mt-0.5 text-[10px] text-danger-500">{errors.neck_movement}</p>}
                </div>
                <div className="border-t-2 border-black dark:border-neutral-600 pt-3">
                  <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-1 text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 transition-smooth">
                    <ChevronDown className={clsx('h-3 w-3 transition-transform', showAdvanced && 'rotate-180')} />
                    {showAdvanced ? 'Less' : 'More'} findings
                  </button>
                  {showAdvanced && (
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      {yesNoSelect('beard', 'Beard')}
                      <div>
                        <label className={labelClass}>Chest</label>
                        <select value={formData.chest_size} onChange={(e) => handleChange('chest_size', e.target.value)} className={inputClass('chest_size')}>
                          <option value="Small">Small</option><option value="Medium">Medium</option><option value="Large">Large</option>
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>Neck</label>
                        <select value={formData.neck_structure} onChange={(e) => handleChange('neck_structure', e.target.value)} className={inputClass('neck_structure')}>
                          <option value="Normal">Normal</option><option value="Abnormal">Abnormal</option>
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>Jaw</label>
                        <select value={formData.jaw_movement} onChange={(e) => handleChange('jaw_movement', e.target.value)} className={inputClass('jaw_movement')}>
                          <option value="Normal">Normal</option><option value="Reduced">Reduced</option>
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>Tissue</label>
                        <select value={formData.tissue_flexibility} onChange={(e) => handleChange('tissue_flexibility', e.target.value)} className={inputClass('tissue_flexibility')}>
                          <option value="Normal">Normal</option><option value="Reduced">Reduced</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
            {activeSection === 'history' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {yesNoSelect('previous_airway_records', 'Previous Airway Records')}
                  {yesNoSelect('disease_arthritis', 'Arthritis')}
                  {yesNoSelect('disease_diabetes', 'Diabetes')}
                  {yesNoSelect('disease_down_syndrome', 'Down Syndrome')}
                  {yesNoSelect('breathing_snoring', 'Snoring')}
                  {yesNoSelect('breathing_sleep_apnea', 'Sleep Apnea')}
                  {yesNoSelect('symptom_voice_changes', 'Voice Changes')}
                  {yesNoSelect('symptom_difficulty_swallowing', 'Difficulty Swallowing')}
                  {yesNoSelect('symptom_cant_lie_flat', "Can't Lie Flat")}
                  {yesNoSelect('injury_swelling', 'Swelling')}
                  {yesNoSelect('injury_previous_neck_fracture', 'Previous Neck Fracture')}
                  {yesNoSelect('previous_emergencies_icu', 'Previous Emergencies/ICU')}
                </div>
              </div>
            )}
          </>
        )}

        {Object.keys(errors).length > 0 && (
          <div className="mt-4 p-2 bg-danger-50 dark:bg-danger-900/20 border-2 border-black dark:border-neutral-600 rounded-[4px]">
            <p className="text-[10px] text-danger-600 dark:text-danger-400 flex items-center gap-1">
              <AlertCircle className="h-3 w-3" />
              Fix errors above before submitting
            </p>
          </div>
        )}

        <div className="mt-4">
          <button
            type="submit"
            disabled={loading}
            className={clsx(
              'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-[4px] text-sm font-bold text-black border-2 border-black transition-smooth shadow-[4px_4px_0_#111111]',
              loading
                ? 'bg-neutral-200 cursor-not-allowed'
                : 'bg-brand-500 hover:bg-brand-400 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_#111111] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none'
            )}
          >
            {loading && (
              <svg className="animate-spin h-4 w-4 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {loading ? 'Assessing...' : 'Assess Patient'}
            {!loading && <Activity className="h-4 w-4" />}
          </button>
        </div>
      </form>
    </div>
  );
}
