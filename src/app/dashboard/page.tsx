'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, User, Edit3, Plus, Activity, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import Sidebar from '@/components/Sidebar';
import ThemeSwitcher from '@/components/ThemeSwitcher';
import RiskPredictionCard from '@/components/RiskPredictionCard';
import AiClinicalAssessment from '@/components/AiClinicalAssessment';
import PatientForm from '@/components/PatientForm';
import PatientHistory from '@/components/PatientHistory';
import StatsCard from '@/components/StatsCard';
import MiniHistory from '@/components/MiniHistory';

import {
  getPredictions, runPrediction, createPatient, deletePrediction,
  getPredictionReport, logout, getToken, getUser, checkLlmStatus,
} from '@/lib/api';
import type { PredictionInput, PredictionResponse, PredictionHistory as PredictionHistoryType, LLMReport } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const formRef = useRef<HTMLDivElement>(null);
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null);
  const [predictions, setPredictions] = useState<PredictionHistoryType[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState('');
  const [selectedPrediction, setSelectedPrediction] = useState<PredictionHistoryType | null>(null);
  const [selectedReport, setSelectedReport] = useState<LLMReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [llmStatus, setLlmStatus] = useState<'checking' | 'connected' | 'offline' | null>(null);
  const [predictingSlow, setPredictingSlow] = useState(false);
  const [historyFilter, setHistoryFilter] = useState<'all' | 'easy' | 'moderate' | 'difficult'>('all');
  const [showForm, setShowForm] = useState(true);
  const [lastSubmittedPatient, setLastSubmittedPatient] = useState<PredictionInput | null>(null);

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return; }
    const u = getUser();
    if (u) setUser(u);
    if (window.location.hash === '#assess-form') {
      setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
    }
  }, [router]);

  const fetchPredictions = useCallback(async () => {
    setLoadingHistory(true);
    try { const data = await getPredictions(); setPredictions(data); }
    catch { /* silent */ }
    finally { setLoadingHistory(false); }
  }, []);

  useEffect(() => {
    if (getToken()) fetchPredictions();
  }, [fetchPredictions]);

  const handleSelectPrediction = useCallback(async (pred: PredictionHistoryType) => {
    setSelectedPrediction(pred);
    setLoadingReport(true);
    try { const report = await getPredictionReport(pred.id); setSelectedReport(report); }
    catch { setSelectedReport(null); }
    finally { setLoadingReport(false); }
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedPrediction(null);
    setSelectedReport(null);
  }, []);

  const handleLogout = () => { logout(); router.push('/login'); };

  const handleSubmit = async (data: PredictionInput) => {
    setPredicting(true);
    setPredictingSlow(false);
    setError('');
    checkLlmStatus()
      .then((s) => setLlmStatus(s.connected ? 'connected' : 'offline'))
      .catch(() => setLlmStatus('offline'));
    const controller = new AbortController();
    const slowTimer = setTimeout(() => setPredictingSlow(true), 5000);
    const failTimer = setTimeout(() => controller.abort(), 35000);
    try {
      await createPatient({
        patient_id: data.patient_id, age: data.age, gender: data.gender, bmi: data.bmi,
        mallampati: String(data.mallampati_score), tmd: data.tmd, neck_circumference: data.neck_circumference,
      });
      const result: PredictionResponse = await runPrediction(data, controller.signal);
      setPredictionResult(result);
      setLastSubmittedPatient(data);
      handleClearSelection();
      fetchPredictions();
    } catch (err) {
      if (controller.signal.aborted) {
        setError('Time limit exceeded. There has been an error with the LLM response. Please wait for a while and try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Prediction failed. Please try again.');
      }
    } finally {
      clearTimeout(slowTimer);
      clearTimeout(failTimer);
      setPredicting(false);
      setPredictingSlow(false);
    }
  };

  const handleNewAssessment = useCallback(() => {
    setPredictionResult(null);
    setSelectedPrediction(null);
    setSelectedReport(null);
    setLastSubmittedPatient(null);
    setShowForm(true);
  }, []);

  function FormStatusBar({ patient, onEdit, onNew }: { patient: PredictionInput; onEdit: () => void; onNew: () => void }) {
    return (
      <div className="rounded-[4px] border-2 border-black bg-white shadow-card animate-fade-in dark:border-neutral-600 dark:bg-neutral-900">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-[4px] bg-black shadow-soft">
              <User className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">{patient.patient_id}</span>
                <span className="rounded-[2px] border-2 border-black bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-700 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200">{patient.gender}</span>
              </div>
              <div className="mt-0.5 flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-300">
                <span>{patient.age}y</span>
                <span className="h-1 w-1 rounded-sm bg-neutral-300 dark:bg-neutral-600" />
                <span>BMI {patient.bmi}</span>
                <span className="h-1 w-1 rounded-sm bg-neutral-300 dark:bg-neutral-600" />
                <span>Mallampati {patient.mallampati_score}</span>
                <span className="h-1 w-1 rounded-sm bg-neutral-300 dark:bg-neutral-600" />
                <span>TMD {patient.tmd}cm</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onNew}
              className="flex items-center gap-1.5 rounded-[4px] border-2 border-black bg-brand-500 px-3 py-1.5 text-xs font-bold text-black shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:bg-brand-400 hover:shadow-none">
              <Plus className="h-3.5 w-3.5" /> New
            </button>
            <button onClick={onEdit}
              className="flex items-center gap-1.5 rounded-[4px] border-2 border-black bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:bg-neutral-100 hover:shadow-none dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:shadow-[2px_2px_0_#3F3F46] dark:hover:bg-neutral-700">
              <Edit3 className="h-3.5 w-3.5" /> Edit
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!user) return null;

  const activePrediction = selectedPrediction || predictionResult?.prediction || null;
  const activeRiskScore = selectedPrediction ? selectedPrediction.risk_score : predictionResult?.prediction.risk_score ?? null;
  const activeConfidence = selectedPrediction ? selectedPrediction.confidence : predictionResult?.prediction.confidence ?? null;
  const activeProbabilities = selectedPrediction ? selectedPrediction.probabilities : predictionResult?.prediction.probabilities ?? null;
  const activePredictionLabel = selectedPrediction ? selectedPrediction.prediction : predictionResult?.prediction.prediction ?? null;

  const easyCount = predictions.filter((p) => p.prediction.toLowerCase() === 'easy').length;
  const moderateCount = predictions.filter((p) => p.prediction.toLowerCase() === 'moderate').length;
  const difficultCount = predictions.filter((p) => p.prediction.toLowerCase() === 'difficult').length;

  const reportSources = selectedPrediction
    ? { summary: selectedReport?.summary_source, recommendations: selectedReport?.recommendations_source }
    : predictionResult?.report_sources;

  return (
    <div className="min-h-screen bg-paper dark:bg-[#121212]">
      <Sidebar />

      <div className="pl-0 transition-[padding-left] duration-300 ease-smooth lg:pl-[var(--sidebar-w,16rem)]">
        {/* Top Bar */}
        <header className="sticky top-0 z-20 border-b-2 border-black bg-white shadow-soft dark:border-neutral-600 dark:bg-neutral-900">
          <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <div className="w-10 lg:hidden" />
              <div className="flex min-w-0 items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-[4px] bg-black shadow-soft">
                  <Activity className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-neutral-800 dark:text-neutral-50">
                    Airway Assessment
                  </h1>
                  <p className="max-w-[52vw] truncate text-xs capitalize text-neutral-400 dark:text-neutral-400 sm:max-w-none">
                    {user.role} · {user.email}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex flex-shrink-0 items-center gap-3">
              {llmStatus !== null && (
              <span
                className={clsx(
                  'hidden items-center gap-1.5 rounded-[3px] border-2 border-black px-2.5 py-1 text-[10px] font-bold sm:inline-flex',
                  llmStatus === 'connected'
                    ? 'bg-success-100 text-success-800'
                    : 'bg-danger-100 text-danger-800'
                )}
              >
                <span
                  className={clsx(
                    'h-1.5 w-1.5 rounded-sm',
                    llmStatus === 'connected' ? 'bg-success-500' : 'bg-danger-500'
                  )}
                />
                {llmStatus === 'connected' ? 'AI Connected' : 'AI Offline'}
              </span>
              )}
              <ThemeSwitcher />
              <button onClick={handleLogout}
                className="hidden items-center gap-2 rounded-[4px] border-2 border-black bg-white px-3 py-1.5 text-sm font-semibold text-neutral-700 transition-smooth hover:bg-danger-50 hover:text-danger-700 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:hover:bg-danger-900/20 dark:hover:text-danger-400 sm:flex">
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
              <div className="flex h-8 w-8 items-center justify-center rounded-[3px] bg-black text-sm font-semibold text-white shadow-soft">
                {user.email.charAt(0).toUpperCase()}
              </div>
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-[1400px] space-y-6">
          {error && (
            <div className="flex items-start gap-2.5 rounded-[4px] border-2 border-black bg-danger-50 p-3 animate-fade-in dark:border-neutral-600 dark:bg-danger-900/20">
              <div className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm bg-danger-500 text-black">
                <span className="text-[10px] font-bold">!</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-danger-800 dark:text-danger-300">Assessment Error</p>
                <p className="mt-0.5 text-xs text-danger-600 dark:text-danger-400">{error}</p>
              </div>
              <button onClick={() => setError('')} className="text-danger-400 hover:text-danger-600">&times;</button>
            </div>
          )}

          {predicting && predictingSlow && (
            <div className="flex items-center gap-2.5 rounded-[4px] border-2 border-black bg-warning-50 p-3 animate-fade-in dark:border-neutral-600 dark:bg-warning-900/20">
              <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-warning-600" />
              <p className="text-sm font-medium text-warning-800 dark:text-warning-300">
                The LLM response is taking longer than usual. Please wait…
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
            <div className="space-y-4 animate-rise stagger-1 lg:col-span-7">
              {showForm ? (
                <div ref={formRef} id="assess-form">
                  <PatientForm onSubmit={handleSubmit} loading={predicting} initialData={lastSubmittedPatient} />
                </div>
              ) : lastSubmittedPatient ? (
                <FormStatusBar patient={lastSubmittedPatient} onEdit={() => setShowForm(true)} onNew={handleNewAssessment} />
              ) : null}

              <AiClinicalAssessment
                summary={selectedReport ? selectedReport.summary : predictionResult?.clinical_summary || ''}
                recommendations={selectedReport ? selectedReport.recommendations : predictionResult?.recommendations || ''}
                loading={predicting || loadingReport}
                prediction={activePredictionLabel || undefined}
                slow={predictingSlow}
                sources={reportSources}
              />
            </div>

            <div className="space-y-4 animate-rise stagger-2 lg:col-span-5">
              {selectedPrediction && (
                <div className="flex items-center gap-2 rounded-[4px] border-2 border-black bg-brand-100 px-3 py-2 animate-fade-in dark:border-neutral-600 dark:bg-brand-900/30">
                  <span className="text-xs font-medium text-brand-700 dark:text-brand-300">
                    Viewing record for <strong>{selectedPrediction.patient_id}</strong>
                  </span>
                  <div className="ml-auto flex items-center gap-3">
                    <button onClick={handleNewAssessment}
                      className="text-xs font-semibold text-brand-600 underline hover:text-brand-800 dark:text-brand-400">+ New</button>
                    <button onClick={handleClearSelection}
                      className="text-xs font-semibold text-brand-600 underline hover:text-brand-800 dark:text-brand-400">Clear</button>
                  </div>
                </div>
              )}
              {activeRiskScore !== null ? (
                <RiskPredictionCard
                  riskScore={activeRiskScore}
                  prediction={activePredictionLabel || ''}
                  confidence={activeConfidence || 0}
                  probabilities={activeProbabilities || {}}
                />
              ) : (
                <div className="flex items-center justify-center rounded-[4px] border-2 border-black bg-white py-10 shadow-card dark:border-neutral-600 dark:bg-neutral-900">
                  <div className="text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-[4px] border-2 border-dashed border-black bg-neutral-50 dark:border-neutral-500 dark:bg-neutral-800">
                      <span className="text-2xl font-bold text-neutral-300 dark:text-neutral-500">?</span>
                    </div>
                    <p className="text-sm font-medium text-neutral-400 dark:text-neutral-300">No risk score yet</p>
                    <p className="mt-1 text-xs text-neutral-400 dark:text-neutral-400">Submit the form to see prediction</p>
                  </div>
                </div>
              )}

              <MiniHistory
                predictions={predictions}
                selectedId={selectedPrediction?.id}
                onSelect={handleSelectPrediction}
              />
            </div>
          </div>

          {/* Overview */}
          <div className="animate-rise">
            <StatsCard
              easy={easyCount}
              moderate={moderateCount}
              difficult={difficultCount}
              total={predictions.length}
            />
          </div>

          {/* Full width — patient history */}
          <div className="animate-rise">
            <PatientHistory
              predictions={predictions}
              loading={loadingHistory}
              selectedId={selectedPrediction?.id}
              onSelect={handleSelectPrediction}
              filter={historyFilter}
              onFilterChange={setHistoryFilter}
              onDelete={async (id) => {
                try { await deletePrediction(id); } catch { /* 404 ok */ }
                setPredictions((prev) => prev.filter((p) => p.id !== id));
                if (selectedPrediction?.id === id) handleClearSelection();
              }}
            />
          </div>
          </div>
        </main>
      </div>
    </div>
  );
}
