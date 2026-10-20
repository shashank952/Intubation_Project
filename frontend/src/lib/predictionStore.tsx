'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { createPatient, runPrediction } from '@/lib/api';
import type { PredictionInput, PredictionResponse } from '@/types';

export type PredictionStatus = 'idle' | 'running' | 'done' | 'error';

interface PredictionContextValue {
  status: PredictionStatus;
  lastSubmittedPatient: PredictionInput | null;
  predictionResult: PredictionResponse | null;
  error: string;
  elapsedSeconds: number;
  startAssessment: (data: PredictionInput) => void;
  clearAssessment: () => void;
  dismissError: () => void;
}

const PredictionContext = createContext<PredictionContextValue | null>(null);

const PATIENT_KEY = 'bg_last_patient';
const RESULT_KEY = 'bg_last_result';

function readJson<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function PredictionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<PredictionStatus>('idle');
  const [lastSubmittedPatient, setLastSubmittedPatient] =
    useState<PredictionInput | null>(null);
  const [predictionResult, setPredictionResult] =
    useState<PredictionResponse | null>(null);
  const [error, setError] = useState('');
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [, setTick] = useState(0);

  const controllerRef = useRef<AbortController | null>(null);
  const runningRef = useRef(false);

  // Restore persisted patient + result on mount (survives full page refresh).
  useEffect(() => {
    const patient = readJson<PredictionInput>(PATIENT_KEY);
    const result = readJson<PredictionResponse>(RESULT_KEY);
    if (patient) setLastSubmittedPatient(patient);
    if (result) {
      setPredictionResult(result);
      setStatus('done');
    }
  }, []);

  // Persist patient + result so a hard refresh keeps them too.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (lastSubmittedPatient) {
      window.localStorage.setItem(PATIENT_KEY, JSON.stringify(lastSubmittedPatient));
    } else {
      window.localStorage.removeItem(PATIENT_KEY);
    }
  }, [lastSubmittedPatient]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (predictionResult) {
      window.localStorage.setItem(RESULT_KEY, JSON.stringify(predictionResult));
    } else {
      window.localStorage.removeItem(RESULT_KEY);
    }
  }, [predictionResult]);

  // Live elapsed-seconds ticker while a prediction is running.
  useEffect(() => {
    if (status !== 'running') return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [status]);

  const clearAssessment = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    runningRef.current = false;
    setStatus('idle');
    setLastSubmittedPatient(null);
    setPredictionResult(null);
    setError('');
    setStartedAt(null);
  }, []);

  const dismissError = useCallback(() => {
    setError('');
    setStatus((s) => (s === 'error' ? 'idle' : s));
  }, []);

  const startAssessment = useCallback((data: PredictionInput) => {
    if (runningRef.current) return;

    runningRef.current = true;
    const controller = new AbortController();
    controllerRef.current = controller;

    setStatus('running');
    setLastSubmittedPatient(data);
    setPredictionResult(null);
    setError('');
    setStartedAt(Date.now());

    // Hard safety timeout — never hang forever.
    const timeout = setTimeout(() => controller.abort(), 60000);

    (async () => {
      try {
        // Patient must exist for the prediction endpoint; ignore "already
        // exists" (409) so re-running the same patient still works.
        try {
          await createPatient({
            patient_id: data.patient_id,
            age: data.age,
            gender: data.gender,
            bmi: data.bmi,
            mallampati: String(data.mallampati_score),
            tmd: data.tmd,
            neck_circumference: data.neck_circumference,
          });
        } catch {
          /* patient may already exist — non-fatal */
        }
        const result = await runPrediction(data, controller.signal);
        setPredictionResult(result);
        setStatus('done');
      } catch (err) {
        if (controller.signal.aborted) {
          setError(
            'Time limit exceeded. The assessment took too long. Please try again.'
          );
        } else {
          setError(err instanceof Error ? err.message : 'Prediction failed. Please try again.');
        }
        setStatus('error');
      } finally {
        clearTimeout(timeout);
        runningRef.current = false;
        setStartedAt(null);
      }
    })();
  }, []);

  const elapsedSeconds =
    status === 'running' && startedAt
      ? Math.floor((Date.now() - startedAt) / 1000)
      : 0;

  return (
    <PredictionContext.Provider
      value={{
        status,
        lastSubmittedPatient,
        predictionResult,
        error,
        elapsedSeconds,
        startAssessment,
        clearAssessment,
        dismissError,
      }}
    >
      {children}
    </PredictionContext.Provider>
  );
}

export function usePrediction(): PredictionContextValue {
  const ctx = useContext(PredictionContext);
  if (!ctx) {
    throw new Error('usePrediction must be used within a PredictionProvider');
  }
  return ctx;
}
