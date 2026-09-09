import Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system/legacy';
import { format } from 'date-fns';
import type {
  AuthResponse,
  Patient,
  PredictionInput,
  PredictionResponse,
  PredictionHistory,
  LLMReport,
  LlmStatus,
  User,
} from '@/types';
import { getToken, setToken, getUser, setUser, clearToken, clearUser, getApiBaseUrl } from '@/lib/storage';

// ---- Base URL resolution (priority order) ----
// 1. runtime override (Settings screen) stored in AsyncStorage
// 2. EXPO_PUBLIC_API_URL env var
// 3. app.json extra.apiBaseUrl
// 4. default LAN dev URL

function defaultBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv;
  const fromAppConfig = (Constants.expoConfig?.extra as Record<string, string> | undefined)?.apiBaseUrl;
  if (fromAppConfig) return fromAppConfig;
  return 'https://intubation-project.onrender.com';
}

let baseUrlOverride: string | null = null;

function normalizeUrl(raw: string): string {
  let url = raw.trim().replace(/\/+$/, '');
  if (url && !/^https?:\/\//i.test(url)) {
    url = `http://${url}`;
  }
  return url;
}

export function setBaseUrlOverride(url: string | null): void {
  baseUrlOverride = url ? normalizeUrl(url) : null;
}

export function getBaseUrl(): string {
  return baseUrlOverride || defaultBaseUrl();
}

export function currentBaseUrlLabel(): string {
  return baseUrlOverride ? `${getBaseUrl()} (saved)` : `${getBaseUrl()} (default)`;
}

// ---- Auth-expired event (401 interceptor notifies AuthContext) ----

type AuthExpiredListener = () => void;
const authExpiredListeners = new Set<AuthExpiredListener>();

export function onAuthExpired(listener: AuthExpiredListener): () => void {
  authExpiredListeners.add(listener);
  return () => authExpiredListeners.delete(listener);
}

function emitAuthExpired(): void {
  authExpiredListeners.forEach((l) => l());
}

// ---- Core fetch wrapper (port of web apiFetch) ----

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// FastAPI returns validation errors (422) as { detail: [{ msg, ... }] }; flatten to readable text.
function formatApiError(body: any): string {
  const d = body?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e: any) => e?.msg).filter(Boolean).join(', ');
  return '';
}

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}${endpoint}`, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError('Cannot reach server. Check your connection or API URL.', 0);
  }

  if (!response.ok) {
    if (response.status === 401) {
      await clearToken();
      await clearUser();
      emitAuthExpired();
    }
    let errorMessage = `API Error: ${response.status} ${response.statusText}`;
    try {
      const errorBody = await response.json();
      errorMessage = formatApiError(errorBody) || errorBody?.message || errorMessage;
    } catch {
      // ignore parse error
    }
    throw new ApiError(errorMessage, response.status);
  }

  // 204 No Content (e.g. DELETE) has an empty body — never parse it
  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    const text = await response.text();
    try {
      return (text ? JSON.parse(text) : undefined) as T;
    } catch {
      return undefined as T;
    }
  }

  return (await response.text()) as unknown as T;
}

// ---- Auth ----

const LOGIN_TIMEOUT_MS = 10000;

export async function login(email: string, password: string): Promise<AuthResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LOGIN_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(
      `Cannot reach server at ${getBaseUrl()}. Check the server address and that the backend is running.`,
      0,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let errorMessage = 'Login failed';
    try {
      const errorBody = await response.json();
      errorMessage = formatApiError(errorBody) || errorMessage;
    } catch {
      errorMessage = `Login failed: ${response.statusText}`;
    }
    if (response.status === 401) errorMessage = 'Invalid credentials';
    throw new ApiError(errorMessage, response.status);
  }

  const data: AuthResponse = await response.json();
  await setToken(data.access_token);
  await setUser(data.user);
  return data;
}

export async function register(email: string, password: string): Promise<{ message: string; email: string }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LOGIN_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(
      `Cannot reach server at ${getBaseUrl()}. Check the server address and that the backend is running.`,
      0,
    );
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    let errorMessage = 'Registration failed';
    try {
      const errorBody = await response.json();
      errorMessage = formatApiError(errorBody) || errorMessage;
    } catch {
      errorMessage = `Registration failed: ${response.statusText}`;
    }
    throw new ApiError(errorMessage, response.status);
  }

  return response.json();
}

export async function logout(): Promise<void> {
  await clearToken();
  await clearUser();
}

// ---- Patients ----

export async function getPatients(): Promise<Patient[]> {
  return apiFetch<Patient[]>('/api/patients');
}

export async function createPatient(data: Partial<Patient>): Promise<Patient> {
  return apiFetch<Patient>('/api/patients', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPatient(id: string): Promise<Patient> {
  return apiFetch<Patient>(`/api/patients/${encodeURIComponent(id)}`);
}

// ---- Predictions ----

export async function runPrediction(
  data: PredictionInput,
  signal?: AbortSignal,
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

export async function getPredictions(patientId?: string): Promise<PredictionHistory[]> {
  const query = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
  return apiFetch<PredictionHistory[]>(`/api/predictions${query}`);
}

export async function getPredictionReport(predictionId: string): Promise<LLMReport> {
  return apiFetch<LLMReport>(
    `/api/predictions/${encodeURIComponent(predictionId)}/report`,
  );
}

export async function deletePrediction(predictionId: string): Promise<void> {
  await apiFetch<void>(`/api/predictions/${encodeURIComponent(predictionId)}`, {
    method: 'DELETE',
  });
}

// ---- CSV export (mobile: writes file to cache, returns path for sharing) ----

export async function exportCsv(): Promise<string> {
  const token = await getToken();
  const response = await fetch(`${getBaseUrl()}/api/predictions/export/csv`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    throw new ApiError('Failed to export CSV', response.status);
  }

  const blob = await response.blob();
  const base64 = await blobToBase64(blob);
  const filename = `airway_predictions_${format(new Date(), 'yyyy-MM-dd')}.csv`;
  const fileUri = `${FileSystem.cacheDirectory}${filename}`;
  await FileSystem.writeAsStringAsync(fileUri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });
  return fileUri;
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1] ?? result;
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

// ---- Health ----

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const response = await fetch(`${getBaseUrl()}/health`);
  if (!response.ok) throw new ApiError('Health check failed', response.status);
  return (await response.json()) as { status: string; version: string };
}

// ---- Exports (parity with web api.ts) ----

export { getToken, getUser, setToken, setUser, clearToken };

export async function getCurrentUser(): Promise<User | null> {
  return getUser();
}