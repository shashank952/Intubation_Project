'use client';

import { useEffect, useRef, useState } from 'react';
import { UploadCloud, X } from 'lucide-react';
import clsx from 'clsx';
import type { NdmsViewKey, PatientImages } from '@/types';

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png'];

const VIEWS: { key: NdmsViewKey; label: string; hint: string }[] = [
  { key: 'frontal', label: 'Frontal', hint: 'Face looking straight ahead' },
  { key: 'teeth', label: 'Teeth & Lip-bite', hint: 'Show upper teeth (Mallampati view)' },
  { key: 'tongue', label: 'Tongue out', hint: 'Tongue protruded' },
  { key: 'jawline', label: 'Side & Jawline', hint: 'Profile of jaw and neck' },
];

export default function PatientImagesField({
  value,
  onChange,
}: {
  value: PatientImages;
  onChange: (images: PatientImages) => void;
}) {
  const [dragging, setDragging] = useState<NdmsViewKey | null>(null);
  const [errors, setErrors] = useState<Partial<Record<NdmsViewKey, string>>>({});
  const inputs = useRef<Partial<Record<NdmsViewKey, HTMLInputElement | null>>>({});
  const urls = useRef(new Map<File, string>());

  useEffect(
    () => () => {
      urls.current.forEach((url) => URL.revokeObjectURL(url));
      urls.current.clear();
    },
    []
  );

  const urlFor = (file: File): string => {
    let url = urls.current.get(file);
    if (!url) {
      url = URL.createObjectURL(file);
      urls.current.set(file, url);
    }
    return url;
  };

  const pick = (key: NdmsViewKey, file: File | null) => {
    if (!file) {
      const next = { ...value };
      delete next[key];
      onChange(next);
      return;
    }
    if (!ACCEPTED.includes(file.type)) {
      setErrors((prev) => ({ ...prev, [key]: 'Only JPEG or PNG images are accepted.' }));
      return;
    }
    if (file.size > MAX_BYTES) {
      setErrors((prev) => ({ ...prev, [key]: 'Image is larger than 8 MB.' }));
      return;
    }
    setErrors((prev) => ({ ...prev, [key]: undefined }));
    onChange({ ...value, [key]: file });
  };

  const filled = VIEWS.filter((view) => value[view.key]).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
          Add up to four views. Images are scored together with the patient data when you press Assess Patient.
        </p>
        {filled > 0 && (
          <button
            type="button"
            onClick={() => {
              onChange({});
              setErrors({});
            }}
            className="flex-shrink-0 text-[10px] font-semibold text-neutral-500 hover:text-danger-600"
          >
            Clear images
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {VIEWS.map(({ key, label, hint }) => {
          const file = value[key];
          return (
            <div key={key} className="rounded-[4px] border-2 border-black bg-white dark:border-neutral-600 dark:bg-neutral-900">
              <div className="flex items-center justify-between border-b-2 border-black px-3 py-1.5 dark:border-neutral-600">
                <span className="text-[11px] font-semibold text-neutral-800 dark:text-neutral-100">{label}</span>
                {file && (
                  <button
                    type="button"
                    onClick={() => pick(key, null)}
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
                  const dropped = event.dataTransfer.files?.[0];
                  if (dropped) pick(key, dropped);
                }}
                className={clsx(
                  'flex h-32 cursor-pointer items-center justify-center overflow-hidden transition-smooth',
                  dragging === key && 'ring-2 ring-inset ring-brand-500'
                )}
              >
                {file ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={urlFor(file)} alt={`${label} preview`} className="h-full w-full object-cover" />
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
                  const chosen = event.target.files?.[0];
                  if (chosen) pick(key, chosen);
                }}
              />
              {errors[key] && (
                <p className="px-3 pb-2 text-[10px] text-danger-600 dark:text-danger-400">{errors[key]}</p>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-[10px] text-neutral-400">
        {filled}/4 views added · optional · eyes are redacted on the server and images are never stored
      </p>
    </div>
  );
}
