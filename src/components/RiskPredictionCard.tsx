'use client';

import { useEffect, useState } from 'react';
import clsx from 'clsx';

interface RiskPredictionCardProps {
  riskScore: number;
  prediction: string;
  confidence: number;
  probabilities: Record<string, number>;
}

const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const ARC_LENGTH = CIRCUMFERENCE * 0.75; // 270° gauge arc

export default function RiskPredictionCard({
  riskScore,
  prediction,
  confidence,
  probabilities,
}: RiskPredictionCardProps) {
  const p = prediction?.toLowerCase() || '';
  const score = Math.min(100, Math.max(0, riskScore * 100));
  const progress = (score / 100) * ARC_LENGTH;

  // Sweep the gauge arc in on first mount
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  const colorClasses =
    p === 'easy'
      ? {
          strip: 'bg-success-500',
          label: 'Easy Airway',
          labelColor: 'text-success-700 dark:text-success-400',
          badgeBg: 'bg-success-50 dark:bg-success-900/20',
          badgeBorder: 'border-black dark:border-neutral-500',
          gauge: 'stroke-success-500',
          glow: 'bg-success-500/10',
        }
      : p === 'moderate'
      ? {
          strip: 'bg-warning-500',
          label: 'Moderate Airway',
          labelColor: 'text-warning-700 dark:text-warning-400',
          badgeBg: 'bg-warning-50 dark:bg-warning-900/20',
          badgeBorder: 'border-black dark:border-neutral-500',
          gauge: 'stroke-warning-500',
          glow: 'bg-warning-500/10',
        }
      : p === 'difficult'
      ? {
          strip: 'bg-danger-500',
          label: 'Difficult Airway',
          labelColor: 'text-danger-700 dark:text-danger-400',
          badgeBg: 'bg-danger-50 dark:bg-danger-900/20',
          badgeBorder: 'border-black dark:border-neutral-500',
          gauge: 'stroke-danger-500',
          glow: 'bg-danger-500/10',
        }
      : {
          strip: 'bg-neutral-400',
          label: 'Unknown',
          labelColor: 'text-neutral-500',
          badgeBg: 'bg-neutral-50 dark:bg-neutral-800',
          badgeBorder: 'border-black dark:border-neutral-500',
          gauge: 'stroke-neutral-400',
          glow: 'bg-neutral-500/10',
        };

  const order = ['Easy', 'Moderate', 'Difficult'];

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card overflow-hidden animate-scale-in h-full flex flex-col">
      <div className={clsx('h-1.5 w-full', colorClasses.strip)} />

      <div className="p-6 flex-1 flex flex-col justify-between gap-5">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-[0.15em]">
              Airway Risk Score
            </p>
            <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
              Predicted intubation difficulty
            </p>
          </div>
          <span className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider font-mono tabular-nums">
            {score.toFixed(0)} / 100
          </span>
        </div>

        {/* Radial gauge */}
        <div className="flex justify-center items-center flex-1 py-2">
          <div className="relative h-56 w-56 animate-gauge-pulse">
            <div className={clsx('absolute inset-8 rounded-sm blur-xl', colorClasses.glow)} />
            <svg viewBox="0 0 120 120" className="relative h-full w-full">
              {/* Track */}
              <circle
                cx="60"
                cy="60"
                r={RADIUS}
                fill="none"
                strokeWidth="11"
                className="stroke-neutral-100 dark:stroke-neutral-800"
                strokeDasharray={`${ARC_LENGTH} ${CIRCUMFERENCE}`}
                strokeLinecap="round"
                transform="rotate(135 60 60)"
              />
              {/* Progress arc */}
              <circle
                cx="60"
                cy="60"
                r={RADIUS}
                fill="none"
                strokeWidth="11"
                className={clsx(colorClasses.gauge, 'transition-all duration-1000')}
                strokeDasharray={`${mounted ? progress : 0} ${CIRCUMFERENCE}`}
                strokeLinecap="round"
                transform="rotate(135 60 60)"
                style={{ transitionTimingFunction: 'cubic-bezier(0.32, 0.72, 0, 1)' }}
              />
            </svg>
            {/* Center readout */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-6xl font-bold text-neutral-900 dark:text-neutral-50 leading-none tabular-nums tracking-tight">
                {score.toFixed(0)}
              </span>
              <span className="text-[11px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-[0.2em] mt-2">
                % Risk
              </span>
            </div>
          </div>
        </div>

        {/* Bottom section — badge + bars */}
        <div className="space-y-4">
          {/* Prediction label */}
          <div className={clsx('rounded-[4px] border-2 px-4 py-3 text-center', colorClasses.badgeBg, colorClasses.badgeBorder)}>
            <p className={clsx('text-base font-bold tracking-wide', colorClasses.labelColor)}>
              {colorClasses.label}
            </p>
          </div>

          {/* Confidence bar */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                Confidence
              </span>
              <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-200 tabular-nums font-mono">
                {(confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2.5 bg-neutral-100 dark:bg-neutral-800 rounded-sm overflow-hidden">
              <div
                className={clsx('h-full rounded-sm transition-all duration-700', colorClasses.strip)}
                style={{
                  width: `${Math.min(100, confidence * 100)}%`,
                  transitionTimingFunction: 'cubic-bezier(0.32, 0.72, 0, 1)',
                }}
              />
            </div>
          </div>

          {/* Stacked probability bar */}
          <div className="space-y-2.5">
            <p className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
              Probability Distribution
            </p>
            {/* Segmented bar */}
            <div className="h-3.5 bg-neutral-100 dark:bg-neutral-800 rounded-sm overflow-hidden flex">
              {order.map((key) => {
                const val = probabilities?.[key] ?? 0;
                const barColor =
                  key === 'Easy' ? 'bg-success-500' : key === 'Moderate' ? 'bg-warning-500' : 'bg-danger-500';
                const widthPct = Math.max(1, Math.min(100, val * 100));
                return (
                  <div
                    key={key}
                    className={clsx('h-full transition-all duration-700', barColor)}
                    style={{ width: `${widthPct}%`, transitionTimingFunction: 'cubic-bezier(0.32, 0.72, 0, 1)' }}
                  />
                );
              })}
            </div>
            {/* Legend */}
            <div className="flex justify-between">
              {order.map((key) => {
                const val = probabilities?.[key] ?? 0;
                const dotColor =
                  key === 'Easy' ? 'bg-success-500' : key === 'Moderate' ? 'bg-warning-500' : 'bg-danger-500';
                return (
                  <div key={key} className="flex items-center gap-1.5">
                    <span className={clsx('h-2 w-2 rounded-sm', dotColor)} />
                    <span className="text-[10px] font-medium text-neutral-500 dark:text-neutral-400">{key}</span>
                    <span className="text-[10px] font-semibold text-neutral-700 dark:text-neutral-200 tabular-nums font-mono">
                      {(val * 100).toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}