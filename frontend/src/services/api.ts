/**
 * FinGuard AI — API Client Service
 * Typed fetch wrappers for the FastAPI backend with JWT authorization.
 */
import type {
  HealthStatus,
  ModelListResponse,
  ModelRegistryEntry,
  MetricsResponse,
  SinglePredictionRequest,
  SinglePredictionResponse,
  CSVPredictionResponse,
  UserProfile,
  TokenResponse,
  AdminAnalytics,
  AuditLogEntry,
  UserRole,
  UserStatus,
  ScreeningHistoryResponse,
} from '../types';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const TOKEN_STORAGE_KEY = 'finguard_auth_token';

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors in private browsing
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const rawHeaders = (init?.headers as Record<string, string>) || {};
  const headers: Record<string, string> = { ...rawHeaders };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const hasHeaders = Object.keys(headers).length > 0;
  const options: RequestInit | undefined =
    init || hasHeaders
      ? {
          ...init,
          ...(hasHeaders ? { headers } : {}),
        }
      : undefined;

  const res = await fetch(`${BASE}${path}`, options);

  if (!res.ok) {
    if (res.status === 401) {
      // If token expired or invalid, clear stored token
      setStoredToken(null);
    }
    const body = await res.json().catch(() => null);
    const msg = body?.detail ?? `Request failed with status: ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return res.json();
}

export const api = {
  /* ── Core System & Models ── */
  getHealth: () => request<HealthStatus>('/health'),

  getModels: (datasetId?: string) => {
    const q = datasetId ? `?dataset_id=${datasetId}` : '';
    return request<ModelListResponse>(`/models${q}`);
  },

  getModel: (modelId: string) =>
    request<ModelRegistryEntry>(`/models/${modelId}`),

  getMetrics: () => request<MetricsResponse>('/metrics'),

  /* ── Prediction Services ── */
  predictSingle: (payload: SinglePredictionRequest) =>
    request<SinglePredictionResponse>('/predict/single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  predictCSV: async (
    datasetId: string,
    modelId: string,
    file: File,
  ): Promise<CSVPredictionResponse> => {
    const fd = new FormData();
    fd.append('dataset_id', datasetId);
    fd.append('model_id', modelId);
    fd.append('file', file);
    return request<CSVPredictionResponse>('/predict/csv', {
      method: 'POST',
      body: fd,
    });
  },

  downloadCSV: async (
    datasetId: string,
    modelId: string,
    file: File,
  ): Promise<Blob> => {
    const fd = new FormData();
    fd.append('dataset_id', datasetId);
    fd.append('model_id', modelId);
    fd.append('file', file);
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE}/predict/csv?download=true`, {
      method: 'POST',
      headers,
      body: fd,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Download failed: ${res.status}`);
    }
    return res.blob();
  },

  /* ── Authentication ── */
  register: (payload: { email: string; password: string; full_name: string }) =>
    request<TokenResponse>('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  getMe: () => request<UserProfile>('/auth/me'),

  logout: () =>
    request<{ status: string; message: string }>('/auth/logout', {
      method: 'POST',
    }),

  deleteMyAccount: () =>
    request<{ status: string; message: string }>('/auth/me', {
      method: 'DELETE',
    }),

  /* ── User Screening History ── */
  getUserHistory: (params?: {
    search?: string;
    screening_type?: string;
    risk_classification?: string;
    dataset_id?: string;
    offset?: number;
    limit?: number;
  }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set('search', params.search);
    if (params?.screening_type && params.screening_type !== 'all') sp.set('screening_type', params.screening_type);
    if (params?.risk_classification && params.risk_classification !== 'all') sp.set('risk_classification', params.risk_classification);
    if (params?.dataset_id && params.dataset_id !== 'all') sp.set('dataset_id', params.dataset_id);
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString() ? `?${sp.toString()}` : '';
    return request<ScreeningHistoryResponse>(`/auth/history${qs}`);
  },

  clearUserHistory: () =>
    request<{ status: string; message: string }>('/auth/history', {
      method: 'DELETE',
    }),

  /* ── Admin Management ── */
  getAdminUsers: (params?: { search?: string; offset?: number; limit?: number }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set('search', params.search);
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.limit !== undefined) sp.set('limit', String(params.limit));
    const qs = sp.toString() ? `?${sp.toString()}` : '';
    return request<{ total: number; offset: number; limit: number; users: UserProfile[] }>(
      `/admin/users${qs}`,
    );
  },

  createAdminUser: (payload: {
    email: string;
    password: string;
    full_name: string;
    role: UserRole;
    status: UserStatus;
  }) =>
    request<UserProfile>('/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  updateAdminUser: (
    userId: string,
    payload: { role?: UserRole; status?: UserStatus },
  ) =>
    request<UserProfile>(`/admin/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  deleteAdminUser: (userId: string) =>
    request<{ status: string; message: string }>(`/admin/users/${userId}`, {
      method: 'DELETE',
    }),

  getAdminAnalytics: (days?: number) => {
    const q = days ? `?days=${days}` : '';
    return request<AdminAnalytics>(`/admin/analytics${q}`);
  },

  getAdminAuditLogs: (params?: { limit?: number; offset?: number; search?: string } | number) => {
    if (typeof params === 'number') {
      return request<AuditLogEntry[]>(`/admin/audit-logs?limit=${params}`);
    }
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset !== undefined) sp.set('offset', String(params.offset));
    if (params?.search) sp.set('search', params.search);
    const qs = sp.toString() ? `?${sp.toString()}` : '';
    return request<AuditLogEntry[]>(`/admin/audit-logs${qs}`);
  },

  getAdminModelsStatus: () =>
    request<{
      total_models: number;
      models: ModelRegistryEntry[];
      metrics_note: string;
    }>('/admin/models-status'),

  getBaseUrl: () => BASE,
};
