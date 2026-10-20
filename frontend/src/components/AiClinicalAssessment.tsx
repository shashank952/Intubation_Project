'use client';

import { Sparkles, Stethoscope, Lightbulb, AlertTriangle, Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface AiClinicalAssessmentProps {
  summary: string;
  recommendations: string;
  loading: boolean;
  prediction?: string;
  slow?: boolean;
  sources?: { summary?: string; recommendations?: string };
}

function parseBullets(text: string): string[] {
  if (!text) return [];
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .map((l) => (l.startsWith('-') ? l.slice(1).trim() : l));
}

export default function AiClinicalAssessment({
  summary,
  recommendations,
  loading,
  prediction,
  slow = false,
  sources,
}: AiClinicalAssessmentProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card p-5 animate-fade-in">
        {slow && (
          <div className="flex items-center gap-2 p-2.5 mb-4 bg-warning-50 dark:bg-warning-900/20 border-2 border-black rounded-[4px]">
            <Loader2 className="h-4 w-4 animate-spin text-warning-600 flex-shrink-0" />
            <p className="text-xs font-medium text-warning-800 dark:text-warning-300">
              The LLM response is taking longer than usual. Please wait…
            </p>
          </div>
        )}
        <div className="flex items-center gap-3 mb-5">
          <div className="skeleton h-9 w-9 rounded-[4px]" />
          <div className="space-y-1.5 flex-1">
            <div className="skeleton h-4 w-44" />
            <div className="skeleton h-3 w-28" />
          </div>
          <div className="skeleton h-6 w-24 rounded-sm" />
        </div>
        <div className="space-y-4">
          <div className="p-4 rounded-[4px] border-2 border-black dark:border-neutral-600">
            <div className="flex items-center gap-2 mb-3">
              <div className="skeleton h-6 w-6 rounded-[4px]" />
              <div className="skeleton h-4 w-24" />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-3.5 w-full mb-2" />
            ))}
          </div>
          <div className="p-4 rounded-[4px] border-2 border-black dark:border-neutral-600">
            <div className="flex items-center gap-2 mb-3">
              <div className="skeleton h-6 w-6 rounded-[4px]" />
              <div className="skeleton h-4 w-32" />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-3.5 w-full mb-2" />
            ))}
          </div>
          <div className="skeleton h-12 w-full rounded-[4px]" />
        </div>
      </div>
    );
  }

  if (!summary && !recommendations) {
    return (
      <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card p-5 card-gradient animate-fade-in">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-9 w-9 rounded-[4px] bg-brand-50 dark:bg-brand-950/30 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">AI Clinical Assessment</h3>
            <p className="text-xs text-neutral-400 dark:text-neutral-400">Clinical analysis &mdash; real-time</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Stethoscope className="h-10 w-10 text-neutral-300 dark:text-neutral-500 mb-3" />
          <p className="text-sm text-neutral-400 dark:text-neutral-400">
            Assess a patient to see the AI-generated clinical analysis.
          </p>
        </div>
      </div>
    );
  }

  const summaryBullets = parseBullets(summary);
  const recBullets = parseBullets(recommendations);

  const urgencyLevel = prediction?.toLowerCase() === 'difficult' ? 'High' : prediction?.toLowerCase() === 'moderate' ? 'Moderate' : 'Low';
  const urgencyColor =
    urgencyLevel === 'High' ? 'bg-danger-500' : urgencyLevel === 'Moderate' ? 'bg-warning-500' : 'bg-success-500';

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card card-gradient animate-fade-in overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b-2 border-black dark:border-neutral-600 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-[4px] bg-black flex items-center justify-center shadow-soft">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
              AI Clinical Assessment
            </h3>
            <p className="text-xs text-neutral-400 dark:text-neutral-400">
              Clinical analysis &mdash; real-time
            </p>
          </div>
        </div>
        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[3px] text-[10px] font-bold text-black border-2 border-black shadow-[3px_3px_0_#111]', urgencyColor)}>
          <span className="h-1.5 w-1.5 rounded-sm bg-black/80 animate-pulse" />
          {urgencyLevel} Urgency
        </span>
      </div>

      {(sources?.summary === 'fallback' || sources?.recommendations === 'fallback') && (
        <div className="flex items-center gap-2 px-5 py-2.5 bg-danger-50 dark:bg-danger-900/20 border-b-2 border-black">
          <AlertTriangle className="h-4 w-4 text-danger-500 flex-shrink-0" />
          <p className="text-xs font-medium text-danger-700 dark:text-danger-300">
            AI assistant unavailable — showing standard guidance.
          </p>
        </div>
      )}

      <div className="p-5 space-y-4">
        {/* Clinical Summary */}
        <section className="p-4 rounded-[4px] bg-brand-50/60 dark:bg-brand-900/15 border-2 border-black dark:border-neutral-600">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="h-7 w-7 rounded-[4px] bg-brand-100 dark:bg-brand-800/60 flex items-center justify-center">
              <Stethoscope className="h-3.5 w-3.5 text-brand-600 dark:text-brand-300" />
            </div>
            <span className="text-sm font-semibold text-brand-800 dark:text-brand-200">
              Assessment
            </span>
          </div>
          {summaryBullets.length > 0 ? (
            <ul className="space-y-2.5">
              {summaryBullets.map((bullet, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-neutral-700 dark:text-neutral-200 leading-relaxed">
                  <span className="mt-[7px] h-1.5 w-1.5 rounded-sm bg-brand-400 flex-shrink-0" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-700 dark:text-neutral-200 whitespace-pre-wrap">{summary}</p>
          )}
        </section>

        {/* Recommendations */}
        <section className="p-4 rounded-[4px] bg-success-50/60 dark:bg-success-900/10 border-2 border-black dark:border-neutral-600">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="h-7 w-7 rounded-[4px] bg-success-100 dark:bg-success-800/40 flex items-center justify-center">
              <Lightbulb className="h-3.5 w-3.5 text-success-600 dark:text-success-300" />
            </div>
            <span className="text-sm font-semibold text-success-800 dark:text-success-200">
              Recommendations
            </span>
          </div>
          {recBullets.length > 0 ? (
            <ul className="space-y-2.5">
              {recBullets.map((bullet, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-neutral-700 dark:text-neutral-200 leading-relaxed">
                  <span className="mt-[7px] h-1.5 w-1.5 rounded-sm bg-success-400 dark:bg-success-400 flex-shrink-0" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-700 dark:text-neutral-200 whitespace-pre-wrap">{recommendations}</p>
          )}
        </section>

        {/* Risk Factors Banner */}
        <div className="flex items-start gap-3 p-3.5 rounded-[4px] bg-amber-50 dark:bg-amber-900/15 border-2 border-black dark:border-neutral-600">
          <div className="h-8 w-8 rounded-[4px] bg-amber-100 dark:bg-amber-800/40 flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="text-xs text-amber-800 dark:text-amber-200 font-medium leading-relaxed pt-1">
            {prediction?.toLowerCase() === 'difficult'
              ? 'Difficult airway anticipated — ensure difficult airway cart and experienced clinician available.'
              : prediction?.toLowerCase() === 'moderate'
              ? 'Moderate risk — prepare alternative airway devices and have backup plan ready.'
              : 'Low risk — standard intubation protocol is likely sufficient.'}
          </p>
        </div>
      </div>
    </div>
  );
}