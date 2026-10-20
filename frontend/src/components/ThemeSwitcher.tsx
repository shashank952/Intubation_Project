'use client';

import { useEffect, useRef, useState } from 'react';
import { Palette, Check } from 'lucide-react';

export const NEO_THEMES = [
  { id: 'yellow', label: 'Yellow', color: '#FFD900' },
  { id: 'teal', label: 'Teal', color: '#16C2C8' },
  { id: 'magenta', label: 'Magenta', color: '#FF00D9' },
  { id: 'coral', label: 'Coral', color: '#FF6B35' },
  { id: 'lime', label: 'Lime', color: '#84CC16' },
  { id: 'violet', label: 'Violet', color: '#8B5CF6' },
  { id: 'sky', label: 'Sky', color: '#3B82F6' },
];

export function applyNeoTheme(id: string): void {
  document.documentElement.setAttribute('data-theme', id);
  window.localStorage.setItem('neo-theme', id);
}

export default function ThemeSwitcher() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState('yellow');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTheme(window.localStorage.getItem('neo-theme') || 'yellow');
  }, []);

  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, []);

  const pick = (id: string) => {
    setTheme(id);
    applyNeoTheme(id);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Choose theme"
        title="Theme"
        className="flex h-9 w-9 items-center justify-center rounded-[4px] border-2 border-black bg-white text-neutral-600 shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:bg-neutral-100 hover:shadow-none dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:shadow-[2px_2px_0_#3F3F46] dark:hover:bg-neutral-700"
      >
        <Palette className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-30 w-44 rounded-[4px] border-2 border-black bg-white p-1.5 shadow-elevated animate-fade-in dark:border-neutral-600 dark:bg-neutral-900">
          {NEO_THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => pick(t.id)}
              aria-label={t.label}
              className="flex w-full items-center gap-2.5 rounded-[3px] px-2 py-1.5 text-left text-sm font-medium text-neutral-700 transition-smooth hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-800"
            >
              <span className="h-4 w-4 flex-shrink-0 rounded-[2px] border-2 border-black" style={{ background: t.color }} />
              <span className="flex-1">{t.label}</span>
              {theme === t.id && <Check className="h-3.5 w-3.5 text-neutral-500 dark:text-neutral-300" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
