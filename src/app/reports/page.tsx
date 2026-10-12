'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileText, AlertCircle, Clock, User, Brain, Activity,
  ChevronDown, ChevronUp, Sparkles, Stethoscope,
} from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import { getToken, getUser, getPredictions, getPredictionReport } from '@/lib/api';
import type { PredictionHistory, LLMReport } from '@/types';
import clsx from 'clsx';

export default function ReportsPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [predictions, setPredictions] = useState<PredictionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reports, setReports] = useState<Record<string, LLMReport>>({});
  const [loadingReport, setLoadingReport] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return; }
    const u = getUser();
    if (u) setUser(u);
  }, [router]);

  const fetchPredictions = useCallback(async () => {
    setLoading(true);
    try { const data = await getPredictions(); setPredictions(data); }
    catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (getToken()) fetchPredictions(); }, [fetchPredictions]);

  const toggleExpand = async (pred: PredictionHistory) => {
    if (expandedId === pred.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(pred.id);
    if (!reports[pred.id]) {
      setLoadingReport(pred.id);
      try { const report = await getPredictionReport(pred.id); setReports((r) => ({ ...r, [pred.id]: report })); }
      catch { /* silent */ }
      finally { setLoadingReport(null); }
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#F5F1DC] dark:bg-[#121212]">
      <Sidebar />
      <div className="lg:pl-64 transition-all duration-300">
        <header className="bg-white dark:bg-neutral-900 border-b-2 border-black dark:border-neutral-600 shadow-soft">
          <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center gap-3">
              <div className="h-8 w-8 rounded-[4px] bg-gray-100 dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 flex items-center justify-center">
                <FileText className="h-4 w-4 text-gray-500 dark:text-neutral-200" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-800 dark:text-neutral-50">Clinical Reports</h1>
              <p className="text-xs text-gray-400 dark:text-neutral-400 capitalize">{user.role} · {user.email}</p>
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin h-8 w-8 border-4 border-neutral-600 border-t-transparent rounded-sm" />
            </div>
          ) : predictions.length === 0 ? (
            <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card p-10 text-center">
              <FileText className="h-12 w-12 text-gray-300 dark:text-neutral-500 mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-500 dark:text-neutral-300">No reports yet</p>
              <p className="text-xs text-gray-400 dark:text-neutral-400 mt-1">Run an assessment to generate a clinical report</p>
            </div>
          ) : (
            predictions.map((pred) => {
              const isOpen = expandedId === pred.id;
              const report = reports[pred.id];
              const probEntries = Object.entries(pred.probabilities || {});
              return (
                <div key={pred.id} className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card overflow-hidden">
                  <button
                    onClick={() => toggleExpand(pred)}
                    className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-smooth text-left"
                  >
                    <div className="flex items-center gap-4">
                      <div className={clsx(
                        'h-10 w-10 rounded-[4px] border-2 border-black flex items-center justify-center',
                        pred.prediction === 'Easy' ? 'bg-green-50 dark:bg-green-900/30' :
                        pred.prediction === 'Moderate' ? 'bg-yellow-50 dark:bg-yellow-900/30' :
                        'bg-red-50 dark:bg-red-900/30'
                      )}>
                        <Stethoscope className={clsx(
                          'h-5 w-5',
                          pred.prediction === 'Easy' ? 'text-green-600 dark:text-green-400' :
                          pred.prediction === 'Moderate' ? 'text-yellow-600 dark:text-yellow-400' :
                          'text-red-600 dark:text-red-400'
                        )} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-gray-800 dark:text-neutral-50">{pred.patient_id}</span>
                          <span className={clsx(
                            'text-[10px] font-semibold px-2 py-0.5 rounded-[3px] border-2 border-black',
                            pred.prediction === 'Easy' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                            pred.prediction === 'Moderate' ? 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                            'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          )}>
                            {pred.prediction}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-gray-400 dark:text-neutral-400 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(pred.created_at).toLocaleDateString()}
                          </span>
                          <span className="text-xs text-gray-400 dark:text-neutral-400">
                            {(pred.confidence * 100).toFixed(0)}% confidence
                          </span>
                        </div>
                      </div>
                    </div>
                    {isOpen ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
                  </button>

                  {isOpen && (
                    <div className="border-t-2 border-black dark:border-neutral-600 px-5 py-4 space-y-4 animate-fade-in">
                      {/* Probabilities */}
                      <div>
                        <h4 className="text-xs font-semibold text-gray-500 dark:text-neutral-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                          <Activity className="h-3 w-3" /> Probabilities
                        </h4>
                        <div className="flex gap-3">
                          {probEntries.map(([key, val]) => (
                            <div key={key} className={clsx(
                              'flex-1 rounded-[4px] px-3 py-2 text-center border-2 border-black',
                              key === 'Easy' ? 'bg-green-50 dark:bg-green-900/20' :
                              key === 'Moderate' ? 'bg-yellow-50 dark:bg-yellow-900/20' :
                              'bg-red-50 dark:bg-red-900/20'
                            )}>
                              <p className={clsx(
                                'text-xs font-medium',
                                key === 'Easy' ? 'text-green-700 dark:text-green-400' :
                                key === 'Moderate' ? 'text-yellow-700 dark:text-yellow-400' :
                                'text-red-700 dark:text-red-400'
                              )}>{key}</p>
                              <p className={clsx(
                                'text-lg font-bold',
                                key === 'Easy' ? 'text-green-800 dark:text-green-300' :
                                key === 'Moderate' ? 'text-yellow-800 dark:text-yellow-300' :
                                'text-red-800 dark:text-red-300'
                              )}>{(val * 100).toFixed(1)}%</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* LLM Report */}
                      {loadingReport === pred.id ? (
                        <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
                          <div className="animate-spin h-4 w-4 border-2 border-neutral-600 border-t-transparent rounded-sm" />
                          Loading AI report...
                        </div>
                      ) : report ? (
                        <>
                          <div>
                              <h4 className="text-xs font-semibold text-gray-500 dark:text-neutral-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <Brain className="h-3 w-3" /> Clinical Summary
                            </h4>
                            <div className="bg-brand-50 dark:bg-brand-950/20 border-2 border-black dark:border-neutral-600 rounded-[4px] p-4">
                              <div className="text-sm text-gray-700 dark:text-neutral-200 space-y-1">
                                {report.summary ? (
                                  report.summary.split('\n').filter((l) => l.trim()).map((line, i) => (
                                    <p key={i}>{line}</p>
                                  ))
                                ) : (
                                  <p className="text-gray-400 italic">No summary available</p>
                                )}
                              </div>
                            </div>
                          </div>
                          <div>
                              <h4 className="text-xs font-semibold text-gray-500 dark:text-neutral-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                              <Sparkles className="h-3 w-3" /> Recommendations
                            </h4>
                            <div className="bg-gray-100 dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 rounded-[4px] p-4">
                              <div className="text-sm text-gray-700 dark:text-neutral-200 space-y-1">
                                {report.recommendations ? (
                                  report.recommendations.split('\n').filter((l) => l.trim()).map((line, i) => (
                                    <p key={i}>{line}</p>
                                  ))
                                ) : (
                                  <p className="text-gray-400 italic">No recommendations available</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </>
                      ) : (
                        <p className="text-sm text-gray-400 italic py-2">No AI report found for this assessment</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </main>
      </div>
    </div>
  );
}
