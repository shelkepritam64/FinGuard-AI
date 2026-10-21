/**
 * FinGuard AI — API Client Service
 * Typed fetch wrappers for the FastAPI backend.
 */
import type {
  HealthStatus,
  ModelListResponse,
  ModelRegistryEntry,
  MetricsResponse,
  SinglePredictionRequest,
  SinglePredictionResponse,
  CSVPredictionResponse,
} from '../types';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const msg = body?.detail ?? `Request failed: ${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return res.json();
}

export const api = {
  getHealth: () => request<HealthStatus>('/health'),

  getModels: (datasetId?: string) => {
    const q = datasetId ? `?dataset_id=${datasetId}` : '';
    return request<ModelListResponse>(`/models${q}`);
  },

  getModel: (modelId: string) =>
    request<ModelRegistryEntry>(`/models/${modelId}`),

  getMetrics: () => request<MetricsResponse>('/metrics'),

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
    const res = await fetch(`${BASE}/predict/csv?download=true`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Download failed: ${res.status}`);
    }
    return res.blob();
  },

  getBaseUrl: () => BASE,
};
