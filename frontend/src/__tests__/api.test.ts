import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../services/api';

describe('API Client Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('exposes the configured base URL', () => {
    const url = api.getBaseUrl();
    expect(url).toBeDefined();
    expect(typeof url).toBe('string');
  });

  it('getHealth sends GET /health', async () => {
    const mockHealth = {
      status: 'healthy',
      app: 'FinGuard AI',
      environment: 'development',
      models_dir_configured: 'models',
      models_dir_exists: true,
      datasets_dir_configured: 'dataset',
      datasets_dir_exists: true,
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockHealth,
    } as Response);

    const res = await api.getHealth();
    expect(res).toEqual(mockHealth);
  });

  it('getModels queries models endpoint without params or with dataset_id', async () => {
    const mockModels = {
      total_models: 1,
      models: [],
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockModels,
    } as Response);

    await api.getModels();
    expect(fetchSpy).toHaveBeenLastCalledWith(expect.stringMatching(/\/models$/), undefined);

    await api.getModels('credit_card_dataset_1');
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/models\?dataset_id=credit_card_dataset_1$/),
      undefined
    );
  });

  it('handles backend error details with HTTP failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Model unavailable or artifact missing' }),
    } as Response);

    await expect(api.getModel('non_existent')).rejects.toThrow(
      'Model unavailable or artifact missing'
    );
  });

  it('predictSingle posts payload to /predict/single with json header', async () => {
    const mockResponse = {
      dataset_id: 'credit_card_dataset_1',
      model_id: 'xgb_credit_card_1',
      prediction_score: 0.85,
      score_type: 'fraud_probability',
      threshold: 0.5,
      risk_label: 'High Risk',
      explanation: 'Score 0.8500 exceeds threshold 0.5000',
      preprocessed_vector: [1, 2, 3],
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const req = {
      dataset_id: 'credit_card_dataset_1',
      model_id: 'xgb_credit_card_1',
      features: { distance_from_home: 10 },
    };

    const res = await api.predictSingle(req);
    expect(res).toEqual(mockResponse);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringMatching(/\/predict\/single$/),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      })
    );
  });

  it('predictCSV sends FormData to /predict/csv', async () => {
    const mockResponse = {
      dataset_id: 'credit_card_dataset_1',
      model_id: 'xgb_credit_card_1',
      total_rows: 10,
      high_risk_count: 2,
      low_risk_count: 8,
      threshold_used: 0.5,
      score_type: 'fraud_probability',
      predictions: [],
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const file = new File(['header\n1'], 'test.csv', { type: 'text/csv' });
    const res = await api.predictCSV('credit_card_dataset_1', 'xgb_credit_card_1', file);
    expect(res).toEqual(mockResponse);
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringMatching(/\/predict\/csv$/),
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
  });
});
