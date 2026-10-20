'use client';

import type { ReactNode } from 'react';
import { PredictionProvider } from '@/lib/predictionStore';
import BackgroundTaskToast from '@/components/BackgroundTaskToast';

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <PredictionProvider>
      {children}
      <BackgroundTaskToast />
    </PredictionProvider>
  );
}
