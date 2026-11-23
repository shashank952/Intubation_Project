'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Camera, CheckCircle2, Trash2, UploadCloud, X } from 'lucide-react';
import clsx from 'clsx';
import NeoLoader from '@/components/NeoLoader';
import { analyzeNdms } from '@/lib/api';
import type { NdmsResult, NdmsViewKey } from '@/types';

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png'];

const VIEWS: { key: NdmsViewKey; label: string; hint: string }[] = [
  { key: 'frontal', label: 'Frontal', hint: 'Face looking straight ahead' },
  { key: 'teeth', label: 'Teeth & Lip-bite', hint: 'Show upper teeth (Mallampati view)' },
  { key: 'tongue', label: 'Tongue out', hint: 'Tongue protruded' },
  { key: 'jawline', label: 'Side & Jawline', hint: 'Profile of jaw and neck' },
];

const ISSUE_TEXT: Record<string, string> = {
  no_face: 'No face detected',
  multiple_faces: 'More than one face',
  face_too_small: 'Face too small',
  blurry: 'Blurry',
  bad_brightness: 'Bad lighting',
  redaction_incomplete: 'Redaction failed',
};

const METRIC_LABELS: Record<string, string> = {
  teeth_visibility: 'Teeth visibility',
  tongue_visibility: 'Tongue visibility',
  profile_aspect: 'Profile aspect',
  submental_brightness: 'Submental brightness',
};

interface SlotState {
  file: File | null;
  localUrl: string | null;
  error: string | null;
}

function emptySlots(): Record<NdmsViewKey, SlotState> {
  return {
    frontal: { file: null, localUrl: null, error: null },
    teeth: { file: null, localUrl: null, error: null },
    tongue: { file: null, localUrl: null, error: null },
    jawline: { file: null, localUrl: null, error: null },
  };
}

function prettify(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}

function bandFor(score: number) {
  if (score < 0.34) return { label: 'Favourable', className: 'bg-success-100 text-success-800' };
  if (score < 0.67) return { label: 'Moderate', className: 'bg-warning-100 text-warning-800' };
  return { label: 'Unfavourable', className: 'bg-danger-100 text-danger-800' };
}

export default function ImageAnalysisPanel({
  patientId,
  baseRisk,
}: {
  patientId?: string;
  baseRisk?: number | null;
}) {
  const [slots, setSlots] = useState<Record<NdmsViewKey, SlotState>>(emptySlots);
  const [dragging, setDragging] = useState<NdmsViewKey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NdmsResult | null>(null);
  const inputs = useRef<Partial<Record<NdmsViewKey, HTMLInputElement | null>>>({});
  const urls = useRef(new Map<NdmsViewKey, string>());

  useEffect(
    () => () => {
      urls.current.forEach((url) => URL.revokeObjectURL(url));
      urls.current.clear();
    },
    []
  );

  const assign = useCallback((key: NdmsViewKey, file: File | null) => {
    const previous = urls.current.get(key);
    if (previous) {
      URL.revokeObjectURL(previous);
      urls.current.delete(key);
    }
    if (!file) {
      setSlots((prev) => ({ ...prev, [key]: { file: null, localUrl: null, error: null } }));
      setResult(null);
      setError(null);
      return;
    }
    if (!ACCEPTED.includes(file.type)) {
      setSlots((prev) => ({
        ...prev,
        [key]: { file: null, localUrl: null, error: 'Only JPEG or PNG images are accepted.' },
      }));
      return;
    }
    if (file.size > MAX_BYTES) {
      setSlots((prev) => ({
        ...prev,
        [key]: { file: null, localUrl: null, error: 'Image is larger than 8 MB.' },
      }));
      return;
    }
    const localUrl = URL.createObjectURL(file);
    urls.current.set(key, localUrl);
    setSlots((prev) => ({ ...prev, [key]: { file, localUrl, error: null } }));
    setResult(null);
    setError(null);
  }, []);

  const filledCount = VIEWS.filter((view) => slots[view.key].file).length;

  const run = async () => {
    const files: Partial<Record<NdmsViewKey, File>> = {};
    VIEWS.forEach(({ key }) => {
      const file = slots[key].file;
      if (file) files[key] = file;
    });
    if (Object.keys(files).length === 0) {
      setError('Add at least one photo first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeNdms(files, { patientId, baseRisk }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'NDMS analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    urls.current.forEach((url) => URL.revokeObjectURL(url));
    urls.current.clear();
    setSlots(emptySlots());
    setResult(null);
    setError(null);
    Object.values(inputs.current).forEach((input) => {
      if (input) input.value = '';
    });
  };

  return (
    <div className="space-y-4">
      <div className="rounded-[4px] border-2 border-black bg-white shadow-card dark:border-neutral-600 dark:bg-neutral-900">
        <div className="flex items-center justify-between border-b-2 border-black px-4 py-3 dark:border-neutral-600">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-[4px] bg-brand-50 dark:bg-brand-950/30">
              <Camera className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
            </div>
            <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">Airway images</span>
            <span className="rounded-[2px] border-2 border-black bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-600 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
              4 views
            </span>
          </div>
          {(filledCount > 0 || result || error) && (
            <button
              type="button"
              onClick={reset}
              className="flex items-center gap-1 text-[10px] font-semibold text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
            >
              <Trash2 className="h-3 w-3" /> Clear
            </button>
          )}
        </div>

        <div className="p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {VIEWS.map(({ key, label, hint }) => {
              const slot = slots[key];
              const viewResult = result?.views[key] ?? null;
              const preview = viewResult?.preview_data_uri ?? slot.localUrl;
              return (
                <div key={key} className="rounded-[4px] border-2 border-black bg-white dark:border-neutral-600 dark:bg-neutral-900">
                  <div className="flex items-center justify-between border-b-2 border-black px-3 py-1.5 dark:border-neutral-600">
                    <span className="text-[11px] font-semibold text-neutral-800 dark:text-neutral-100">{label}</span>
                    {slot.file && (
                      <button
                        type="button"
                        onClick={() => assign(key, null)}
                        aria-label={`Remove ${label}`}
                        className="text-neutral-400 hover:text-danger-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => inputs.current[key]?.click()}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') inputs.current[key]?.click();
                    }}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(key);
                    }}
                    onDragLeave={() => setDragging(null)}
                    onDrop={(event) => {
                      event.preventDefault();
                      setDragging(null);
                      const file = event.dataTransfer.files?.[0];
                      if (file) assign(key, file);
                    }}
                    className={clsx(
                      'flex h-40 cursor-pointer items-center justify-center overflow-hidden transition-smooth',
                      dragging === key && 'ring-2 ring-inset ring-brand-500'
                    )}
                  >
                    {preview ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img src={preview} alt={`${label} preview`} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex flex-col items-center gap-1 px-3 text-center">
                        <UploadCloud className="h-5 w-5 text-neutral-400" />
                        <p className="text-[10px] text-neutral-500 dark:text-neutral-400">{hint}</p>
                        <p className="text-[9px] text-neutral-400">JPEG/PNG · 8 MB</p>
                      </div>
                    )}
                  </div>
                  <input
                    ref={(element) => {
                      inputs.current[key] = element;
                    }}
                    type="file"
                    accept="image/jpeg,image/png"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) assign(key, file);
                    }}
                  />
                  {slot.error && (
                    <p className="px-3 pb-2 text-[10px] text-danger-600 dark:text-danger-400">{slot.error}</p>
                  )}
                  {slot.file && viewResult && (
                    <div className="space-y-1 border-t-2 border-black px-3 py-2 dark:border-neutral-600">
                      <span
                        className={clsx(
                          'inline-flex items-center gap-1 rounded-[3px] border-2 border-black px-1.5 py-0.5 text-[9px] font-bold',
                          viewResult.usable ? 'bg-success-100 text-success-800' : 'bg-warning-100 text-warning-800'
                        )}
                      >
                        {viewResult.usable ? (
                          <CheckCircle2 className="h-2.5 w-2.5" />
                        ) : (
                          <AlertTriangle className="h-2.5 w-2.5" />
                        )}
                        {viewResult.usable ? 'Usable' : 'Needs attention'}
                      </span>
                      {viewResult.issues.length > 0 && (
                        <p className="text-[9px] text-warning-700 dark:text-warning-300">
                          {viewResult.issues.map((issue) => ISSUE_TEXT[issue] ?? issue).join(' · ')}
                        </p>
                      )}
                      {Object.entries(viewResult.view_metrics).some(([, value]) => value != null) && (
                        <p className="text-[9px] text-neutral-400">
                          {Object.entries(viewResult.view_metrics)
                            .filter(([, value]) => value != null)
                            .map(([name, value]) => `${METRIC_LABELS[name] ?? prettify(name)} ${value}`)
                            .join(' · ')}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={run}
              disabled={filledCount === 0 || loading}
              className="flex items-center gap-1.5 rounded-[4px] border-2 border-black bg-brand-500 px-3 py-1.5 text-xs font-bold text-black shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:bg-brand-400 hover:shadow-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Camera className="h-3.5 w-3.5" /> Analyze images
            </button>
            <span className="text-[10px] text-neutral-400">
              {filledCount}/4 added · NDMS needs at least 2 usable views
            </span>
            {loading && <NeoLoader variant="inline" label="Scoring images" />}
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-[4px] border-2 border-black bg-danger-50 p-2 dark:border-neutral-600 dark:bg-danger-900/20">
              <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0 text-danger-500" />
              <p className="text-[11px] text-danger-700 dark:text-danger-300">{error}</p>
            </div>
          )}

          <p className="mt-2 text-[10px] text-neutral-400">
            Eyes are redacted on the server before anything comes back. Images are never stored.
          </p>
        </div>
      </div>

      {result && (
        <div className="rounded-[4px] border-2 border-black bg-white shadow-card dark:border-neutral-600 dark:bg-neutral-900">
          <div className="border-b-2 border-black px-4 py-3 dark:border-neutral-600">
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">NDMS — image contribution</h2>
          </div>
          <div className="space-y-4 p-4">
            {result.score == null ? (
              <div className="rounded-[4px] border-2 border-dashed border-neutral-300 p-3 text-center dark:border-neutral-600">
                <p className="text-xs font-medium text-neutral-600 dark:text-neutral-300">Need at least 2 usable views</p>
                <p className="mt-0.5 text-[10px] text-neutral-400">
                  Add or fix photos so more than one view can be measured.
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <div className="flex h-16 w-16 flex-col items-center justify-center rounded-[4px] border-2 border-black bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-800">
                  <span className="text-xl font-bold text-neutral-800 dark:text-neutral-100">
                    {Math.round(result.score * 100)}
                  </span>
                  <span className="text-[9px] text-neutral-400">/100</span>
                </div>
                <div>
                  <span
                    className={clsx(
                      'inline-flex rounded-[3px] border-2 border-black px-2 py-0.5 text-[10px] font-bold',
                      bandFor(result.score).className
                    )}
                  >
                    {bandFor(result.score).label}
                  </span>
                  <p className="mt-1 text-[10px] text-neutral-400">
                    Confidence {Math.round(result.confidence * 100)}%
                  </p>
                </div>
              </div>
            )}

            {result.components.length > 0 && (
              <div className="space-y-2">
                {result.components.map((component) => (
                  <div key={component.name} title={component.note}>
                    <div className="mb-0.5 flex items-center justify-between text-[10px]">
                      <span className="font-medium text-neutral-600 dark:text-neutral-300">{prettify(component.name)}</span>
                      <span className="text-neutral-400">{Math.round(component.value * 100)}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-[2px] border border-black/20 bg-neutral-100 dark:bg-neutral-800">
                      <div className="h-full bg-brand-500" style={{ width: `${Math.round(component.value * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-[3px] border-2 border-black bg-white px-2 py-1.5 dark:border-neutral-600 dark:bg-neutral-800">
                <p className="text-[9px] uppercase tracking-wide text-neutral-400">Risk contribution</p>
                <p className="text-xs font-semibold text-neutral-800 dark:text-neutral-100">
                  {result.risk_contribution == null ? 'No adjustment' : `+${result.risk_contribution} pts`}
                </p>
                <p className="text-[9px] text-neutral-400">max +{result.max_contribution}</p>
              </div>
              <div className="rounded-[3px] border-2 border-black bg-white px-2 py-1.5 dark:border-neutral-600 dark:bg-neutral-800">
                <p className="text-[9px] uppercase tracking-wide text-neutral-400">Combined risk</p>
                <p className="text-xs font-semibold text-neutral-800 dark:text-neutral-100">
                  {result.blended_risk == null ? '—' : result.blended_risk}
                </p>
                <p className="text-[9px] text-neutral-400">tabular + image</p>
              </div>
            </div>

            <p className="rounded-[3px] bg-warning-100 px-2 py-1.5 text-[10px] leading-relaxed text-warning-800 dark:bg-warning-900/20 dark:text-warning-300">
              {result.note}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
