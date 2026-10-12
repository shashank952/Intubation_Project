'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Settings, User, Moon, Sun, Globe, Database, Cpu,
  ArrowLeft, Shield,
} from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import { getToken, getUser, logout } from '@/lib/api';
import { BASE_URL } from '@/lib/api';
import clsx from 'clsx';

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return; }
    const u = getUser();
    if (u) setUser(u);
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setDark(true);
    }
  }, [router]);

  const toggleDark = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#F5F1DC] dark:bg-[#121212]">
      <Sidebar />
      <div className="lg:pl-64 transition-all duration-300">
        <header className="bg-white dark:bg-neutral-900 border-b-2 border-black dark:border-neutral-600 shadow-soft">
          <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center gap-3">
              <div className="h-8 w-8 rounded-[4px] bg-gray-100 dark:bg-neutral-800 border-2 border-black dark:border-neutral-600 flex items-center justify-center">
                <Settings className="h-4 w-4 text-gray-500 dark:text-neutral-200" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-800 dark:text-neutral-50">Settings</h1>
              <p className="text-xs text-gray-400 dark:text-neutral-400 capitalize">{user.role} · {user.email}</p>
            </div>
          </div>
        </header>

        <main className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-2xl">
          {/* Profile */}
          <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card">
            <div className="px-5 py-4 border-b-2 border-black dark:border-neutral-600 flex items-center gap-3">
              <User className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-800 dark:text-neutral-50">Profile</h2>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300">Username</span>
                <span className="text-sm font-medium text-gray-800 dark:text-neutral-50">{user.email}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300">Role</span>
                <span className="text-sm font-medium capitalize text-gray-800 dark:text-neutral-50">{user.role}</span>
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card">
            <div className="px-5 py-4 border-b-2 border-black dark:border-neutral-600 flex items-center gap-3">
              {dark ? <Moon className="h-4 w-4 text-gray-400" /> : <Sun className="h-4 w-4 text-gray-400" />}
              <h2 className="text-sm font-semibold text-gray-800 dark:text-neutral-50">Appearance</h2>
            </div>
            <div className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-neutral-50">Dark Mode</p>
                  <p className="text-xs text-gray-400 dark:text-neutral-400">Toggle dark mode for the dashboard</p>
                </div>
                <button
                  onClick={toggleDark}
                  className={clsx(
                    'relative h-7 w-12 rounded-[4px] border-2 transition-smooth',
                    dark
                      ? 'bg-neutral-600 border-neutral-400'
                      : 'bg-white border-black'
                  )}
                >
                  <span className={clsx(
                    'absolute top-0 left-0 h-6 w-6 rounded-[3px] bg-white border-2 border-black transition-transform duration-200',
                    dark ? 'translate-x-5' : 'translate-x-0'
                  )} />
                </button>
              </div>
            </div>
          </div>

          {/* System Info */}
          <div className="bg-white dark:bg-neutral-900 rounded-[4px] border-2 border-black dark:border-neutral-600 shadow-card">
            <div className="px-5 py-4 border-b-2 border-black dark:border-neutral-600 flex items-center gap-3">
              <Cpu className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-800 dark:text-neutral-50">System</h2>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300 flex items-center gap-2">
                  <Globe className="h-3.5 w-3.5" /> API URL
                </span>
                <span className="text-xs font-mono text-gray-800 dark:text-neutral-50">{BASE_URL}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300 flex items-center gap-2">
                  <Database className="h-3.5 w-3.5" /> MongoDB
                </span>
                <span className="text-xs font-mono text-green-600 dark:text-green-400">Connected</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300 flex items-center gap-2">
                  <Cpu className="h-3.5 w-3.5" /> LLM Model
                </span>
                <span className="text-xs font-mono text-gray-800 dark:text-neutral-50">Qwen 2.5 72B (OpenRouter)</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-500 dark:text-neutral-300 flex items-center gap-2">
                  <Shield className="h-3.5 w-3.5" /> ML Model
                </span>
                <span className="text-xs font-mono text-gray-800 dark:text-neutral-50">TabTransformer (tabular_best.pt)</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
