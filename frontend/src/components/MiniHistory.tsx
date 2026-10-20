'use client';

import { format, parseISO } from 'date-fns';
import { ChevronRight, Clock } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';
import type { PredictionHistory } from '@/types';

interface MiniHistoryProps {
  predictions: PredictionHistory[];
  selectedId?: string | null;
  onSelect?: (pred: PredictionHistory) => void;
}

function badgeClasses(prediction: string) {
  const lower = prediction.toLowerCase();
  if (lower === 'easy') return { text: 'text-success-600 dark:text-success-400', dot: 'bg-success-500' };
  if (lower === 'moderate') return { text: 'text-warning-600 dark:text-warning-400', dot: 'bg-warning-500' };
  return { text: 'text-danger-600 dark:text-danger-400', dot: 'bg-danger-500' };
}

export default function MiniHistory({ predictions, selectedId, onSelect }: MiniHistoryProps) {
  const recent = predictions.slice(0, 5);

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b-2 border-black dark:border-neutral-600 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-brand-500 dark:text-brand-400" />
          <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            Recent Records
          </span>
        </div>
        {predictions.length > 5 && (
          <Link
            href="/history"
            className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-smooth"
          >
            View all &rarr;
          </Link>
        )}
      </div>

      {recent.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Clock className="h-8 w-8 text-neutral-300 dark:text-neutral-600 mb-2" />
          <p className="text-xs text-neutral-400 dark:text-neutral-500 font-medium">
            No records yet
          </p>
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5">
            Assess a patient to see results here
          </p>
        </div>
      ) : (
        <div className="divide-y-2 divide-black/15 dark:divide-neutral-700">
          {recent.map((pred) => {
            const bc = badgeClasses(pred.prediction);
            const isSelected = selectedId === pred.id;
            let dateStr = pred.created_at;
            try { dateStr = format(parseISO(pred.created_at), 'MMM dd'); }
            catch {}
            return (
              <button
                key={pred.id}
                onClick={() => onSelect?.(pred)}
                className={clsx(
                  'w-full flex items-center justify-between px-4 py-2.5 text-left transition-smooth',
                  isSelected
                    ? 'bg-brand-100 dark:bg-brand-950/40'
                    : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'
                )}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200 truncate">
                    {pred.patient_id}
                  </span>
                  <span className={clsx('text-xs font-semibold', bc.text)}>
                    {pred.prediction}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[10px] text-neutral-400 dark:text-neutral-500">{dateStr}</span>
                  <ChevronRight className="h-3 w-3 text-neutral-300 dark:text-neutral-600" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
