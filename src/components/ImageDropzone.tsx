'use client';

import { useCallback, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, ImageIcon, Trash2, UploadCloud } from 'lucide-react';
import clsx from 'clsx';
import { analyzeImage } from '@/lib/api';
import type { ImageAnalysis } from '@/types';

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png'];

const ISSUE_TEXT: Record<string, string> = {
  no_face: 'No face detected',
  multiple_faces: 'More than one face',
  face_too_small: 'Face too small',
  blurry: 'Blurry',
  bad_brightness: 'Bad lighting',
  redaction_incomplete: 'Redaction failed',
};

interface Item {
  id: string;
  name: string;
  status: 'uploading' | 'done' | 'error';
  result?: ImageAnalysis;
  error?: string;
}

export default function ImageDropzone({ patientId }: { patientId?: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<Item[]>([]);

  const upload = useCallback(
    async (file: File) => {
      const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setItems((prev) => [...prev, { id, name: file.name, status: 'uploading' }]);
      try {
        const result = await analyzeImage(file, patientId);
        setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status: 'done', result } : item)));
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Analysis failed.';
        setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status: 'error', error: message } : item)));
      }
    },
    [patientId]
  );

  const accept = useCallback(
    (files: File[]) => {
      for (const file of files) {
        if (!ACCEPTED.includes(file.type)) {
          setItems((prev) => [
            ...prev,
            { id: `${file.name}-type`, name: file.name, status: 'error', error: 'Only JPEG or PNG.' },
          ]);
          continue;
        }
        if (file.size > MAX_BYTES) {
          setItems((prev) => [
            ...prev,
            { id: `${file.name}-size`, name: file.name, status: 'error', error: 'Larger than 8 MB.' },
          ]);
          continue;
        }
        queue.current = queue.current.then(() => upload(file));
      }
    },
    [upload]
  );

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    accept(Array.from(event.dataTransfer.files ?? []));
  };

  const done = items.filter((item) => item.status === 'done').length;
  const failed = items.filter((item) => item.status === 'error').length;
  const busy = items.some((item) => item.status === 'uploading');

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={clsx(
          'flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-2 rounded-[4px] border-2 border-dashed px-6 py-10 text-center transition-smooth',
          dragging
            ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/30'
            : 'border-neutral-300 bg-white hover:border-neutral-400 dark:border-neutral-600 dark:bg-neutral-900'
        )}
      >
        <UploadCloud className={clsx('h-8 w-8', dragging ? 'text-brand-600' : 'text-neutral-400')} />
        <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">
          Drag and drop photos here
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          or click to choose files &middot; JPEG or PNG &middot; up to 8 MB each
        </p>
        <p className="mt-1 text-[10px] text-neutral-400">
          Eyes are redacted on the server. Uploads are checked and discarded, never stored.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          multiple
          className="hidden"
          onChange={(event) => {
            accept(Array.from(event.target.files ?? []));
            event.target.value = '';
          }}
        />
      </div>

      {items.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <span>
            {items.length} file{items.length === 1 ? '' : 's'} &middot; {done} checked
            {failed > 0 ? ` &middot; ${failed} failed` : ''}
          </span>
          {busy && <span className="text-brand-600 dark:text-brand-400">working…</span>}
          <button
            type="button"
            onClick={() => setItems([])}
            className="ml-auto flex items-center gap-1 rounded-[3px] border-2 border-black bg-white px-2 py-1 text-[10px] font-semibold text-neutral-600 shadow-[2px_2px_0_#111111] transition-smooth hover:bg-neutral-100 dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-200 dark:shadow-[2px_2px_0_#3F3F46]"
          >
            <Trash2 className="h-3 w-3" /> Clear
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.id}
              className="overflow-hidden rounded-[4px] border-2 border-black bg-white shadow-card dark:border-neutral-600 dark:bg-neutral-900"
            >
              {item.result?.preview_data_uri ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={item.result.preview_data_uri} alt={item.name} className="h-44 w-full object-cover" />
              ) : (
                <div className="flex h-44 w-full items-center justify-center bg-neutral-50 dark:bg-neutral-800">
                  {item.status === 'uploading' ? (
                    <span className="text-[11px] text-neutral-400">checking…</span>
                  ) : (
                    <ImageIcon className="h-6 w-6 text-neutral-300" />
                  )}
                </div>
              )}

              <div className="space-y-1.5 p-2.5">
                <p className="truncate text-[11px] font-medium text-neutral-700 dark:text-neutral-200" title={item.name}>
                  {item.name}
                </p>

                {item.status === 'done' && item.result && (
                  <>
                    <span
                      className={clsx(
                        'inline-flex items-center gap-1 rounded-[3px] border-2 border-black px-1.5 py-0.5 text-[9px] font-bold',
                        item.result.quality.usable
                          ? 'bg-success-100 text-success-800'
                          : 'bg-warning-100 text-warning-800'
                      )}
                    >
                      {item.result.quality.usable ? (
                        <CheckCircle2 className="h-2.5 w-2.5" />
                      ) : (
                        <AlertTriangle className="h-2.5 w-2.5" />
                      )}
                      {item.result.quality.usable ? 'Usable' : 'Needs attention'}
                    </span>
                    <p className="text-[9px] text-neutral-400">
                      {item.result.quality.width}×{item.result.quality.height} &middot;{' '}
                      {item.result.faces_redacted} face{item.result.faces_redacted === 1 ? '' : 's'}
                    </p>
                    {item.result.quality.issues.length > 0 && (
                      <p className="text-[9px] text-warning-700 dark:text-warning-300">
                        {item.result.quality.issues.map((issue) => ISSUE_TEXT[issue] ?? issue).join(' · ')}
                      </p>
                    )}
                  </>
                )}

                {item.status === 'uploading' && (
                  <p className="text-[9px] text-neutral-400">Analyzing…</p>
                )}

                {item.status === 'error' && (
                  <p className="text-[9px] text-danger-600 dark:text-danger-400">{item.error}</p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
