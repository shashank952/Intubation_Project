'use client';

import { useState, FormEvent, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Stethoscope, Eye, EyeOff, AlertCircle, LogIn } from 'lucide-react';
import clsx from 'clsx';
import { login, getToken, clearToken } from '@/lib/api';
import { BASE_URL } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect only if token is valid; clear stale tokens
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          router.replace('/dashboard');
        } else {
          clearToken();
        }
      } catch {
        clearToken();
      }
    })();
  }, [router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address');
      return;
    }
    if (!password.trim()) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Login failed. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F1DC] p-4">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-lg bg-brand-300" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-lg bg-[#FF00D9]/25" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center h-16 w-16 rounded-[4px] bg-black shadow-[5px_5px_0_#111111] mb-4">
            <Stethoscope className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Airway MD</h1>
          <p className="text-sm text-gray-500 mt-1">
            Clinical Assessment — Multimodal Airway Prediction
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-[4px] border-2 border-black shadow-[6px_6px_0_#111111] p-8">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-800">
              Welcome Back
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Sign in to access the assessment dashboard
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-600 mb-1.5"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError('');
                }}
                className={clsx(
                  'w-full px-4 py-2.5 text-sm border-2 rounded-[4px] shadow-[5px_5px_0_#111111] transition-smooth focus:outline-none focus:ring-2',
                  error
                    ? 'border-danger-500 focus:ring-danger-300'
                    : 'border-black focus:ring-brand-300 focus:border-brand-400 hover:border-neutral-300'
                )}
                autoComplete="email"
              />
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-600 mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError('');
                  }}
                  className={clsx(
                    'w-full px-4 py-2.5 pr-11 text-sm border-2 rounded-[4px] shadow-[5px_5px_0_#111111] transition-smooth focus:outline-none focus:ring-2',
                    error
                      ? 'border-danger-500 focus:ring-danger-300'
                    : 'border-black focus:ring-brand-300 focus:border-brand-400 hover:border-neutral-300'
                  )}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-smooth"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className="p-3 bg-danger-50 border-2 border-black rounded-[4px] flex items-start gap-2.5">
                <AlertCircle className="h-4 w-4 text-danger-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-danger-700">{error}</p>
              </div>
            )}

            {/* Sign In Button */}
            <button
              type="submit"
              disabled={loading}
              className={clsx(
                'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-[4px] text-sm font-bold text-black border-2 border-black transition-smooth shadow-[4px_4px_0_#111111]',
                loading
                  ? 'bg-neutral-200 cursor-not-allowed'
                  : 'bg-brand-500 hover:bg-brand-400 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_#111111] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none'
              )}
            >
              {loading && (
                <svg
                  className="animate-spin h-4 w-4 text-black"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              )}
              {loading ? 'Signing In...' : 'Sign In'}
              {!loading && <LogIn className="h-4 w-4" />}
            </button>

            {/* Sign Up Button */}
            <Link
              href="/signup"
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-[4px] text-sm font-bold text-black bg-white border-2 border-black transition-smooth shadow-[4px_4px_0_#111111] hover:bg-neutral-100 hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-[2px_2px_0_#111111] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none"
            >
              Sign Up
            </Link>
          </form>

          <div className="mt-6 pt-6 border-t-2 border-black text-center">
            <p className="text-xs text-gray-400">
              Secure clinical assessment platform
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
