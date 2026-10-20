import type {
  AuthResponse,
  Patient,
  PredictionInput,
  PredictionResponse,
  PredictionHistory,
  LLMReport,
  LlmStatus,
} from '@/types';
import { ensureLocalSession, isLocalHost } from '@/lib/localDemo';
import { DEMO_HISTORY, DEMO_REPORT } from '@/lib/demoData';

ensureLocalSession();

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export const DEFAULT_IDLE_SECONDS = 30 * 60;
export const DEFAULT_WARNING_SECONDS = 120;
const IDLE_KEY = 'session_idle_seconds';
const WARNING_KEY = 'session_warning_seconds';
const EXPIRES_KEY = 'session_expires_at';

function readSeconds(key: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback;
  const value = Number(localStorage.getItem(key));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

export function getIdleTimeoutSeconds(): number {
  return readSeconds(IDLE_KEY, DEFAULT_IDLE_SECONDS);
}

export function getWarningSeconds(): number {
  return readSeconds(WARNING_KEY, DEFAULT_WARNING_SECONDS);
}

function setSessionMeta(res: AuthResponse): void {
  if (typeof window === 'undefined') return;
  if (res.idle_timeout_seconds) localStorage.setItem(IDLE_KEY, String(res.idle_timeout_seconds));
  if (res.warning_seconds) localStorage.setItem(WARNING_KEY, String(res.warning_seconds));
  if (res.expires_at) localStorage.setItem(EXPIRES_KEY, res.expires_at);
}

function clearSessionMeta(): void {
  localStorage.removeItem(IDLE_KEY);
  localStorage.removeItem(WARNING_KEY);
  localStorage.removeItem(EXPIRES_KEY);
}

function formatApiError(body: any): string {
  const d = body?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e: any) => e?.msg).filter(Boolean).join(', ');
  if (d && typeof d === 'object' && typeof d.message === 'string') return d.message;
  return '';
}

function setToken(token: string): void {
  localStorage.setItem('access_token', token);
}

function clearToken(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  clearSessionMeta();
}

const SESSION_ERROR_CODES = ['session_expired', 'session_revoked', 'relogin_required'];

export function handleSessionEnded(): void {
  clearToken();
  if (typeof window === 'undefined') return;
  if (window.location.pathname.startsWith('/login')) return;
  window.location.assign('/login?reason=idle');
}

function getUser(): { email: string; role: string } | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem('user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setUser(user: { email: string; role: string }): void {
  localStorage.setItem('user', JSON.stringify(user));
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    let code: string | undefined;
    try {
      const errorBody = await response.json();
      const detail = errorBody?.detail;
      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        code = detail.code;
      }
      errorMessage = formatApiError(errorBody) || errorBody?.message || errorMessage;
    } catch {
      // ignore parse error
    }
    if (response.status === 401 && code && SESSION_ERROR_CODES.includes(code)) {
      handleSessionEnded();
    }
    throw new Error(errorMessage);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }

  return response.text() as unknown as T;
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let errorMessage = 'Login failed';
    try {
      const errorBody = await response.json();
      errorMessage = formatApiError(errorBody) || errorMessage;
    } catch {
      errorMessage = `Login failed: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token);
  setUser(data.user);
  setSessionMeta(data);
  return data;
}

export async function register(
  email: string,
  password: string
): Promise<{ message: string; email: string }> {
  const response = await fetch(`${BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let errorMessage = 'Registration failed';
    try {
      const errorBody = await response.json();
      errorMessage = formatApiError(errorBody) || errorMessage;
    } catch {
      errorMessage = `Registration failed: ${response.statusText}`;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export async function logout(): Promise<void> {
  const token = getToken();
  clearToken();
  if (!token || isLocalHost()) return;
  await fetch(`${BASE_URL}/api/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    keepalive: true,
  }).catch(() => undefined);
}

export interface HeartbeatResponse {
  server_time: string;
  expires_at: string;
  idle_timeout_seconds: number;
  warning_seconds: number;
}

export async function heartbeat(): Promise<HeartbeatResponse> {
  if (isLocalHost()) {
    return {
      server_time: new Date().toISOString(),
      expires_at: new Date(Date.now() + getIdleTimeoutSeconds() * 1000).toISOString(),
      idle_timeout_seconds: getIdleTimeoutSeconds(),
      warning_seconds: getWarningSeconds(),
    };
  }
  return apiFetch<HeartbeatResponse>('/api/auth/heartbeat', { method: 'POST' });
}

export async function getPatients(): Promise<Patient[]> {
  return apiFetch<Patient[]>('/api/patients');
}

export async function createPatient(
  data: Partial<Patient>
): Promise<Patient> {
  return apiFetch<Patient>('/api/patients', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPatient(id: string): Promise<Patient> {
  return apiFetch<Patient>(`/api/patients/${id}`);
}

export async function runPrediction(
  data: PredictionInput,
  signal?: AbortSignal
): Promise<PredictionResponse> {
  return apiFetch<PredictionResponse>('/api/predictions', {
    method: 'POST',
    body: JSON.stringify(data),
    signal,
  });
}

export async function checkLlmStatus(): Promise<LlmStatus> {
  return apiFetch<LlmStatus>('/api/llm/status');
}

export async function getPredictions(
  patientId?: string
): Promise<PredictionHistory[]> {
  if (isLocalHost()) return DEMO_HISTORY;
  const query = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
  return apiFetch<PredictionHistory[]>(`/api/predictions${query}`);
}

export async function getPredictionReport(
  predictionId: string
): Promise<LLMReport> {
  if (isLocalHost()) return DEMO_REPORT;
  return apiFetch<LLMReport>(
    `/api/predictions/${encodeURIComponent(predictionId)}/report`
  );
}

export async function deletePrediction(predictionId: string): Promise<void> {
  await apiFetch<void>(`/api/predictions/${encodeURIComponent(predictionId)}`, {
    method: 'DELETE',
  });
}

export async function exportCsv(): Promise<Blob> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/api/predictions/export/csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new Error('Failed to export CSV');
  }

  return response.blob();
}

export { getToken, setToken, clearToken, getUser, setUser };
export { BASE_URL };
