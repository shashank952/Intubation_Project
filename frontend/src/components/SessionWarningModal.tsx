'use client';

import { Clock, LogOut } from 'lucide-react';

interface SessionWarningModalProps {
  open: boolean;
  secondsLeft: number;
  onStay: () => void;
  onLogout: () => void;
}

function formatCountdown(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60).toString().padStart(2, '0');
  const seconds = (safe % 60).toString().padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export default function SessionWarningModal({
  open,
  secondsLeft,
  onStay,
  onLogout,
}: SessionWarningModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-warning-title"
    >
      <div className="w-full max-w-sm bg-white rounded-[4px] border-2 border-black shadow-[6px_6px_0_#111111] p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="h-10 w-10 rounded-[4px] bg-black flex items-center justify-center flex-shrink-0">
            <Clock className="h-5 w-5 text-white" />
          </div>
          <h2 id="session-warning-title" className="text-lg font-bold text-gray-800">
            Still there?
          </h2>
        </div>

        <p className="text-sm text-gray-600">
          To protect patient data you&apos;ll be signed out in
          <span className="font-bold text-gray-900"> {formatCountdown(secondsLeft)}</span>.
        </p>

        <div className="flex gap-3 mt-6">
          <button
            type="button"
            onClick={onStay}
            autoFocus
            className="flex-1 px-4 py-2.5 text-sm font-bold text-black bg-brand-500 border-2 border-black rounded-[4px] shadow-[4px_4px_0_#111111] hover:bg-brand-400 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_#111111] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-smooth"
          >
            Stay signed in
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-bold text-gray-700 bg-white border-2 border-black rounded-[4px] shadow-[4px_4px_0_#111111] hover:bg-neutral-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_#111111] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-smooth"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      </div>
    </div>
  );
}
