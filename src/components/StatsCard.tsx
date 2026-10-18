'use client';

import { Activity, TrendingUp } from 'lucide-react';
import clsx from 'clsx';

interface StatsCardProps {
  easy: number;
  moderate: number;
  difficult: number;
  total: number;
}

export default function StatsCard({ easy, moderate, difficult, total }: StatsCardProps) {
  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card overflow-hidden">
      <div className="px-4 py-3 border-b-2 border-black dark:border-neutral-600 flex items-center gap-2">
        <Activity className="h-4 w-4 text-brand-500 dark:text-brand-400" />
        <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
          Overview
        </span>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center">
            <div className="text-2xl font-bold text-success-600 dark:text-success-400 font-display tabular-nums">
              {easy}
            </div>
            <div className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mt-0.5">
              Easy
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-warning-600 dark:text-warning-400 font-display tabular-nums">
              {moderate}
            </div>
            <div className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mt-0.5">
              Moderate
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-danger-600 dark:text-danger-400 font-display tabular-nums">
              {difficult}
            </div>
            <div className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mt-0.5">
              Difficult
            </div>
          </div>
        </div>
        {total > 0 && (
          <div className="mt-3 pt-3 border-t-2 border-black dark:border-neutral-600 flex items-center justify-between">
            <span className="text-xs text-neutral-400 dark:text-neutral-500">Total assessments</span>
            <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-200 tabular-nums">{total}</span>
          </div>
        )}
      </div>
    </div>
  );
}
