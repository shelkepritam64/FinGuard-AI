import { describe, it, expect } from 'vitest';
import { DATASET_LABELS, MODEL_FAMILY_LABELS } from '../types';

describe('Domain Models & Labels', () => {
  it('maps dataset IDs to human-readable academic labels', () => {
    expect(DATASET_LABELS.credit_card_dataset_1).toBe('Credit Card Fraud Detection');
    expect(DATASET_LABELS.paysim_dataset_2).toBe('PaySim Synthetic Mobile Money');
  });

  it('correctly labels model families', () => {
    expect(MODEL_FAMILY_LABELS.XGBoost).toBe('XGBoost Gradient Boosted Trees');
    expect(MODEL_FAMILY_LABELS.MLP).toBe('Multilayer Perceptron (MLP)');
    expect(MODEL_FAMILY_LABELS.Autoencoder).toBe('Autoencoder Anomaly Detection');
    expect(MODEL_FAMILY_LABELS.LSTM).toBe('LSTM Sequence Model');
  });

  it('differentiates score types between probability and reconstruction error', () => {
    const isAnomalyScore = (scoreType: string) =>
      scoreType === 'mean_squared_reconstruction_error';

    expect(isAnomalyScore('mean_squared_reconstruction_error')).toBe(true);
    expect(isAnomalyScore('fraud_probability')).toBe(false);
  });
});
