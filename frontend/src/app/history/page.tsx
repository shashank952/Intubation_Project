'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import Sidebar from '@/components/Sidebar';
import PatientHistory from '@/components/PatientHistory';
import { getToken, getUser } from '@/lib/api';
import { getPredictions } from '@/lib/api';
import type { PredictionHistory as PredictionHistoryType } from '@/types';

export default function HistoryPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(
    null
  );
  const [predictions, setPredictions] = useState<PredictionHistoryType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    const u = getUser();
    if (u) setUser(u);
  }, [router]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await getPredictions();
        setPredictions(data);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    };
    if (getToken()) {
      fetchData();
    }
  }, []);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-paper dark:bg-[#121212]">
      <Sidebar />

      <div className="pl-0 transition-[padding-left] duration-300 ease-smooth lg:pl-[var(--sidebar-w,16rem)]">
        {/* Header */}
        <header className="bg-white dark:bg-neutral-900 border-b-2 border-black dark:border-neutral-600 shadow-soft">
          <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="lg:hidden w-10" />
              <div>
                <div className="flex items-center gap-3">
                  <Link
                    href="/dashboard"
                      className="h-8 w-8 rounded-[4px] bg-white dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 flex items-center justify-center text-neutral-600 dark:text-neutral-300 shadow-[2px_2px_0_#111111] dark:shadow-[2px_2px_0_#3F3F46] hover:bg-neutral-100 dark:hover:bg-neutral-700 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none transition-smooth"
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                  <div>
                    <h1 className="text-lg font-semibold text-gray-800 dark:text-neutral-50">
                      Prediction History
                    </h1>
                    <p className="text-xs text-gray-400 dark:text-neutral-400">
                      View all previous airway assessments
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="h-8 w-8 rounded-[3px] bg-black flex items-center justify-center text-white text-sm font-semibold shadow-soft">
              {user.email.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <PatientHistory predictions={predictions} loading={loading} />
        </main>
      </div>
    </div>
  );
}
