'use client';

import { useCallback, useRef, useState } from 'react';
import { AlertTriangle, Camera, CheckCircle2, ImageIcon, X } from 'lucide-react';
import clsx from 'clsx';
import NeoLoader from '@/components/NeoLoader';
import { analyzeImage } from '@/lib/api';
import type { ImageAnalysis } from '@/types';

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png'];

const ISSUE_TEXT: Record<string, string> = {
  no_face: 'No face detected in the photo',
  multiple_faces: 'More than one face in the frame',
  face_too_small: 'Face is too small in the frame',
  blurry: 'Photo is too blurry',
  bad_brightness: 'Photo is too dark or too bright',
  redaction_incomplete: 'Could not redact every face, so no preview was returned',
};

export default function ImageUploadCard({ patientId }: { patientId?: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImageAnalysis | null>(null);
  const [fileName, setFileName] = useState('');

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setResult(null);
      if (!ACCEPTED.includes(file.type)) {
        setError('Only JPEG or PNG images are accepted.');
        return;
      }
      if (file.size > MAX_BYTES) {
        setError('Image is larger than 8 MB.');
        return;
      }
      setFileName(file.name);
      setLoading(true);
      try {
        setResult(await analyzeImage(file, patientId));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis failed.');
      } finally {
        setLoading(false);
      }
    },
    [patientId]
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragging(false);
      const file = event.dataTransfer.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile]
  );

  const reset = () => {
    setResult(null);
    setError(null);
    setFileName('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const issues = result?.quality.issues ?? [];

  return (
    <div className="rounded-[4px] border-2 border-black bg-white shadow-card dark:border-neutral-600 dark:bg-neutral-900">
      <div className="flex items-center justify-between border-b-2 border-black px-4 py-3 dark:border-neutral-600">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-[4px] bg-brand-50 dark:bg-brand-950/30">
            <Camera className="h-3.5 w-3.5 text-brand-600 dark:text-brand-400" />
          </div>
          <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
            Photo check
          </span>
          <span className="rounded-[2px] border-2 border-black bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-600 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
            Optional
          </span>
        </div>
        {(result || error) && (
          <button
            type="button"
            onClick={reset}
            className="flex items-center gap-1 text-[10px] font-semibold text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
          >
            <X className="h-3 w-3" /> Clear
          </button>
        )}
      </div>

      <div className="p-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={clsx(
            'flex cursor-pointer flex-col items-center justify-center gap-1 rounded-[4px] border-2 border-dashed px-4 py-6 text-center transition-smooth',
            dragging
              ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/30'
              : 'border-neutral-300 hover:border-neutral-400 dark:border-neutral-600'
          )}
        >
          <ImageIcon className="h-5 w-5 text-neutral-400" />
          <p className="text-xs font-medium text-neutral-700 dark:text-neutral-200">
            Drop a photo here, or click to choose one
          </p>
          <p className="text-[10px] text-neutral-400">
            JPEG or PNG, up to 8 MB. Eyes are redacted on the server before anything is returned.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
        </div>

        {fileName && (
          <p className="mt-2 truncate text-[10px] text-neutral-400">Selected: {fileName}</p>
        )}

        {loading && (
          <div className="mt-3">
            <NeoLoader variant="inline" label="Checking photo" />
          </div>
        )}

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-[4px] border-2 border-black bg-danger-50 p-2 dark:border-neutral-600 dark:bg-danger-900/20">
            <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0 text-danger-500" />
            <p className="text-[11px] text-danger-700 dark:text-danger-300">{error}</p>
          </div>
        )}

        {result && (
          <div className="mt-3 space-y-3">
            {result.preview_data_uri && (
              <div className="overflow-hidden rounded-[4px] border-2 border-black dark:border-neutral-600">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={result.preview_data_uri}
                  alt="Redacted photo preview"
                  className="w-full object-contain"
                />
                <p className="border-t-2 border-black bg-neutral-50 px-2 py-1 text-[10px] text-neutral-500 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-400">
                  Redacted preview ({result.faces_redacted} face
                  {result.faces_redacted === 1 ? '' : 's'} covered)
                </p>
              </div>
            )}

            <div className="flex items-center gap-2">
              {result.quality.usable ? (
                <span className="flex items-center gap-1 rounded-[3px] border-2 border-black bg-success-100 px-2 py-0.5 text-[10px] font-bold text-success-800">
                  <CheckCircle2 className="h-3 w-3" /> Photo usable
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded-[3px] border-2 border-black bg-warning-100 px-2 py-0.5 text-[10px] font-bold text-warning-800">
                  <AlertTriangle className="h-3 w-3" /> Needs attention
                </span>
              )}
              <span className="text-[10px] text-neutral-400">
                {result.quality.width}×{result.quality.height} &middot; {result.quality.faces} face
                {result.quality.faces === 1 ? '' : 's'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <Metric label="Sharpness" value={result.quality.blur_score.toFixed(0)} />
              <Metric label="Brightness" value={result.quality.brightness_mean.toFixed(0)} />
              <Metric
                label="Face size"
                value={
                  result.quality.face_area_frac != null
                    ? `${(result.quality.face_area_frac * 100).toFixed(1)}%`
                    : '—'
                }
              />
            </div>

            {issues.length > 0 && (
              <ul className="space-y-1">
                {issues.map((issue) => (
                  <li
                    key={issue}
                    className="flex items-start gap-1.5 text-[11px] text-warning-700 dark:text-warning-300"
                  >
                    <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                    {ISSUE_TEXT[issue] ?? issue}
                  </li>
                ))}
              </ul>
            )}

            {result.warnings.map((warning) => (
              <p key={warning} className="text-[10px] text-neutral-500 dark:text-neutral-400">
                {warning}
              </p>
            ))}

            <p className="rounded-[3px] bg-neutral-50 px-2 py-1.5 text-[10px] leading-relaxed text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
              {result.auto_fill_note}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[3px] border-2 border-black bg-white px-2 py-1.5 text-center dark:border-neutral-600 dark:bg-neutral-800">
      <p className="text-[9px] uppercase tracking-wide text-neutral-400">{label}</p>
      <p className="text-xs font-semibold text-neutral-800 dark:text-neutral-100">{value}</p>
    </div>
  );
}
