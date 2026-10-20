'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, CheckCircle2, X, ArrowRight } from 'lucide-react';
import clsx from 'clsx';
import { usePrediction } from '@/lib/predictionStore';

export default function BackgroundTaskToast() {
  const router = useRouter();
  const { status, lastSubmittedPatient, error, elapsedSeconds, clearAssessment } =
    usePrediction();

  // Reset local dismiss flags whenever the status changes.
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => {
    setDismissed(false);
  }, [status]);

  // Auto-dismiss the "done" toast after a few seconds.
  useEffect(() => {
    if (status !== 'done' || dismissed) return;
    const id = setTimeout(() => setDismissed(true), 7000);
    return () => clearTimeout(id);
  }, [status, dismissed]);

  if (status === 'idle') return null;

  const patientId = lastSubmittedPatient?.patient_id || 'patient';
  const dismiss = () => setDismissed(true);

  let content: React.ReactNode;
  let tone: 'running' | 'done' | 'error' = 'running';

  if (status === 'running') {
    tone = 'running';
    content = (
      <>
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin text-brand-600 dark:text-brand-400" />
          <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
            Assessing {patientId}…
          </span>
        </div>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-300">
          Running in the background ({elapsedSeconds}s) — you can keep browsing.
        </p>
      </>
    );
  } else if (status === 'done') {
    tone = 'done';
    content = (
      <>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success-600 dark:text-success-400" />
          <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
            Result ready for {patientId}
          </span>
        </div>
        <button
          onClick={() => router.push('/dashboard')}
          className="mt-2 inline-flex items-center gap-1.5 rounded-[3px] border-2 border-black bg-success-500 px-2.5 py-1 text-xs font-bold text-black shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none"
        >
          View result <ArrowRight className="h-3 w-3" />
        </button>
      </>
    );
  } else {
    tone = 'error';
    content = (
      <>
        <div className="flex items-center gap-2">
          <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-sm bg-danger-500 text-[10px] font-bold text-black">
            !
          </span>
          <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
            Assessment failed
          </span>
        </div>
        <p className="mt-1 line-clamp-2 text-xs text-danger-600 dark:text-danger-400">
          {error || 'Something went wrong. Please try again.'}
        </p>
        <button
          onClick={() => {
            dismiss();
            clearAssessment();
          }}
          className="mt-2 inline-flex items-center gap-1 rounded-[3px] border-2 border-black bg-white px-2.5 py-1 text-xs font-semibold text-neutral-700 shadow-[2px_2px_0_#111111] transition-smooth hover:bg-neutral-100 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200"
        >
          Dismiss
        </button>
      </>
    );
  }

  if (dismissed) return null;

  return (
    <div
      className={clsx(
        'fixed bottom-4 right-4 z-[60] w-72 animate-fade-in rounded-[4px] border-2 border-black bg-white p-4 shadow-card dark:border-neutral-600 dark:bg-neutral-900',
        tone === 'running' && 'border-black dark:border-neutral-600',
        tone === 'done' && 'border-black dark:border-neutral-600',
        tone === 'error' && 'border-danger-500 dark:border-danger-500'
      )}
    >
      {(tone === 'done' || tone === 'error') && (
        <button
          onClick={dismiss}
          aria-label="Dismiss"
          className="absolute right-2 top-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      {content}
    </div>
  );
}
