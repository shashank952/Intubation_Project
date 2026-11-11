'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import ImageDropzone from '@/components/ImageDropzone';
import { getToken, getUser } from '@/lib/api';

export default function ImagesPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [patientId, setPatientId] = useState('');

  useEffect(() => {
    if (!getToken()) {
      router.replace('/login');
      return;
    }
    const current = getUser();
    if (current) setUser(current);
  }, [router]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-paper dark:bg-[#121212]">
      <Sidebar />

      <div className="pl-0 transition-[padding-left] duration-300 ease-smooth lg:pl-[var(--sidebar-w,16rem)]">
        <header className="border-b-2 border-black bg-white shadow-soft dark:border-neutral-600 dark:bg-neutral-900">
          <div className="flex items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
            <div className="flex items-center gap-4">
              <div className="w-10 lg:hidden" />
              <div className="flex items-center gap-3">
                <Link
                  href="/dashboard"
                  className="flex h-8 w-8 items-center justify-center rounded-[4px] border-2 border-black bg-white text-neutral-600 shadow-[2px_2px_0_#111111] transition-smooth hover:translate-x-[1px] hover:translate-y-[1px] hover:bg-neutral-100 hover:shadow-none dark:border-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 dark:shadow-[2px_2px_0_#3F3F46] dark:hover:bg-neutral-700"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Link>
                <div>
                  <h1 className="text-lg font-semibold text-gray-800 dark:text-neutral-50">Images</h1>
                  <p className="text-xs text-gray-400 dark:text-neutral-400">
                    Drop airway photos to check framing, lighting and face detection
                  </p>
                </div>
              </div>
            </div>
            <div className="flex h-8 w-8 items-center justify-center rounded-[3px] bg-black text-sm font-semibold text-white shadow-soft">
              {user.email.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-[1400px] space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <div className="space-y-4 lg:col-span-8">
                <div className="rounded-[4px] border-2 border-black bg-white p-4 shadow-card dark:border-neutral-600 dark:bg-neutral-900">
                  <label
                    htmlFor="images-patient"
                    className="mb-1.5 block text-xs font-medium text-neutral-600 dark:text-neutral-300"
                  >
                    Patient ID (optional)
                  </label>
                  <input
                    id="images-patient"
                    type="text"
                    value={patientId}
                    onChange={(event) => setPatientId(event.target.value)}
                    placeholder="e.g. P-0001"
                    className="w-full rounded-[4px] border-2 border-black bg-white px-3 py-2 text-sm transition-smooth focus:outline-none focus:ring-2 focus:ring-brand-300 dark:border-neutral-600 dark:bg-neutral-800"
                  />
                  <p className="mt-1 text-[10px] text-neutral-400">
                    Applied to every photo in this batch, for the audit log only.
                  </p>
                </div>

                <ImageDropzone patientId={patientId.trim() || undefined} />
              </div>

              <aside className="space-y-4 lg:col-span-4">
                <div className="rounded-[4px] border-2 border-black bg-white p-4 shadow-card dark:border-neutral-600 dark:bg-neutral-900">
                  <div className="mb-2 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                    <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-50">
                      What the check reports
                    </h2>
                  </div>
                  <ul className="space-y-1.5 text-xs text-neutral-600 dark:text-neutral-300">
                    <li>Whether a face was found, and how large it is in frame.</li>
                    <li>Sharpness and brightness, so blurry or dark photos are caught.</li>
                    <li>Mouth and face ratios, measured on the redacted image.</li>
                    <li>A redacted preview, produced on the server.</li>
                  </ul>
                </div>

                <div className="rounded-[4px] border-2 border-black bg-white p-4 shadow-card dark:border-neutral-600 dark:bg-neutral-900">
                  <h2 className="mb-2 text-sm font-semibold text-neutral-800 dark:text-neutral-50">
                    Limits
                  </h2>
                  <ul className="space-y-1.5 text-xs text-neutral-600 dark:text-neutral-300">
                    <li>JPEG or PNG, 8 MB per file.</li>
                    <li>20 checks per minute per user.</li>
                    <li>No clinical field is filled automatically.</li>
                    <li>Photos are not stored; nothing is attached to a patient record.</li>
                  </ul>
                </div>
              </aside>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
