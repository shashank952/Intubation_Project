'use client';

import type { ReactNode } from 'react';
import { PredictionProvider } from '@/lib/predictionStore';
import BackgroundTaskToast from '@/components/BackgroundTaskToast';
import SessionProvider from '@/components/SessionProvider';

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <PredictionProvider>
      {children}
      <BackgroundTaskToast />
      <SessionProvider />
    </PredictionProvider>
  );
}
