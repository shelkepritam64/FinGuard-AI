import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import type { ModelRegistryEntry, SinglePredictionResponse, DatasetId } from '../types';
import { DATASET_LABELS } from '../types';
import { Loading, ErrorBox } from '../components/StateDisplays';

const DEFAULT_SAMPLES: Record<DatasetId, { lowRisk: Record<string, any>; highRisk: Record<string, any> }> = {
  credit_card_dataset_1: {
    lowRisk: {
      distance_from_home: 4.5,
      distance_from_last_transaction: 0.8,
      ratio_to_median_purchase_price: 1.02,
      repeat_retailer: 1,
      used_chip: 1,
      used_pin_number: 1,
      online_order: 0,
    },
    highRisk: {
      distance_from_home: 120.5,
      distance_from_last_transaction: 45.2,
      ratio_to_median_purchase_price: 8.75,
      repeat_retailer: 0,
      used_chip: 0,
      used_pin_number: 0,
      online_order: 1,
    },
  },
  paysim_dataset_2: {
    lowRisk: {
      step: 1,
      amount: 1864.28,
      type: 'PAYMENT',
    },
    highRisk: {
      step: 25,
      amount: 850000.0,
      type: 'TRANSFER',
    },
  },
};

export function SingleTransactionPage() {
  const [searchParams] = useSearchParams();
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedDataset, setSelectedDataset] = useState<DatasetId>('credit_card_dataset_1');
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<SinglePredictionResponse | null>(null);

  // Initialize models and URL query parameters
  useEffect(() => {
    api
      .getModels()
      .then((res) => {
        setModels(res.models);
        setLoadingModels(false);

        const urlDataset = searchParams.get('dataset') as DatasetId | null;
        const urlModel = searchParams.get('model');

        const initialDataset: DatasetId =
          urlDataset === 'credit_card_dataset_1' || urlDataset === 'paysim_dataset_2'
            ? urlDataset
            : 'credit_card_dataset_1';
        setSelectedDataset(initialDataset);

        const availableForDs = res.models.filter(
          (m) => m.dataset_id === initialDataset && m.is_available
        );

        let initialModelId = '';
        if (urlModel && availableForDs.some((m) => m.model_id === urlModel)) {
          initialModelId = urlModel;
        } else if (availableForDs.length > 0) {
          initialModelId = availableForDs[0].model_id;
        }

        setSelectedModelId(initialModelId);
        setFormValues(DEFAULT_SAMPLES[initialDataset].lowRisk);
      })
      .catch((err) => {
        setLoadError(err.message);
        setLoadingModels(false);
      });
  }, [searchParams]);

  const selectedModel = useMemo(
    () => models.find((m) => m.model_id === selectedModelId),
    [models, selectedModelId]
  );

  const availableModels = useMemo(
    () => models.filter((m) => m.dataset_id === selectedDataset && m.is_available),
    [models, selectedDataset]
  );

  const handleDatasetChange = (newDs: DatasetId) => {
    setSelectedDataset(newDs);
    setResult(null);
    setApiError(null);
    setFieldErrors({});

    const available = models.filter((m) => m.dataset_id === newDs && m.is_available);
    if (available.length > 0) {
      setSelectedModelId(available[0].model_id);
    } else {
      setSelectedModelId('');
    }

    setFormValues(DEFAULT_SAMPLES[newDs].lowRisk);
  };

  const handleInputChange = (field: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => {
      const copy = { ...prev };
      delete copy[field];
      return copy;
    });
  };

  const loadPreset = (type: 'low' | 'high') => {
    const preset =
      type === 'low'
        ? DEFAULT_SAMPLES[selectedDataset].lowRisk
        : DEFAULT_SAMPLES[selectedDataset].highRisk;
    setFormValues(preset);
    setFieldErrors({});
    setResult(null);
    setApiError(null);
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!selectedModel) {
      errors._general = 'No available model selected.';
      setFieldErrors(errors);
      return false;
    }

    if (selectedDataset === 'credit_card_dataset_1') {
      const numericFields = [
        'distance_from_home',
        'distance_from_last_transaction',
        'ratio_to_median_purchase_price',
      ];
      numericFields.forEach((f) => {
        const val = formValues[f];
        if (val === undefined || val === '' || isNaN(Number(val)) || Number(val) < 0) {
          errors[f] = 'Must be a non-negative number';
        }
      });

      const binaryFields = ['repeat_retailer', 'used_chip', 'used_pin_number', 'online_order'];
      binaryFields.forEach((f) => {
        const val = Number(formValues[f]);
        if (val !== 0 && val !== 1) {
          errors[f] = 'Must be 0 (No) or 1 (Yes)';
        }
      });
    } else if (selectedDataset === 'paysim_dataset_2') {
      const stepVal = Number(formValues.step);
      if (isNaN(stepVal) || stepVal < 1) {
        errors.step = 'Step must be an integer >= 1';
      }

      const amountVal = Number(formValues.amount);
      if (isNaN(amountVal) || amountVal <= 0) {
        errors.amount = 'Amount must be greater than 0';
      }

      const validTypes = ['CASH_IN', 'CASH_OUT', 'DEBIT', 'PAYMENT', 'TRANSFER'];
      if (!validTypes.includes(formValues.type)) {
        errors.type = 'Select a valid transaction type';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    setApiError(null);
    setResult(null);

    // Prepare strictly typed features
    const parsedFeatures: Record<string, number | string> = {};
    if (selectedDataset === 'credit_card_dataset_1') {
      [
        'distance_from_home',
        'distance_from_last_transaction',
        'ratio_to_median_purchase_price',
        'repeat_retailer',
        'used_chip',
        'used_pin_number',
        'online_order',
      ].forEach((key) => {
        parsedFeatures[key] = Number(formValues[key]);
      });
    } else {
      parsedFeatures.step = Number(formValues.step);
      parsedFeatures.amount = Number(formValues.amount);
      parsedFeatures.type = String(formValues.type);
    }

    try {
      const response = await api.predictSingle({
        dataset_id: selectedDataset,
        model_id: selectedModelId,
        features: parsedFeatures,
      });
      setResult(response);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Inference request failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const isAutoencoder = result?.score_type === 'mean_squared_reconstruction_error';

  return (
    <div className="page">
      <header className="page-header">
        <h1>Individual Transaction Screening</h1>
        <p>
          Evaluate an individual financial transaction in real-time. Form inputs adapt strictly to the
          target dataset schema and feed the exact preprocessing pipeline of the selected model.
        </p>
      </header>

      {loadingModels && <Loading message="Loading model registry…" />}
      {loadError && <ErrorBox message={loadError} />}

      {!loadingModels && !loadError && (
        <div className="grid-2">
          {/* Form Column */}
          <div>
            <div className="card mb-2">
              <div className="card-body">
                <form onSubmit={handleSubmit}>
                  {/* Dataset Selector */}
                  <div className="form-group">
                    <label className="form-label" htmlFor="single-dataset">
                      Target Dataset
                    </label>
                    <select
                      id="single-dataset"
                      className="form-select"
                      value={selectedDataset}
                      onChange={(e) => handleDatasetChange(e.target.value as DatasetId)}
                      disabled={submitting}
                    >
                      <option value="credit_card_dataset_1">Credit Card Fraud Detection</option>
                      <option value="paysim_dataset_2">PaySim Synthetic Mobile Money</option>
                    </select>
                  </div>

                  {/* Model Selector */}
                  <div className="form-group">
                    <label className="form-label" htmlFor="single-model">
                      Screening Model
                    </label>
                    <select
                      id="single-model"
                      className="form-select"
                      value={selectedModelId}
                      onChange={(e) => {
                        setSelectedModelId(e.target.value);
                        setResult(null);
                      }}
                      disabled={submitting || availableModels.length === 0}
                    >
                      {availableModels.map((m) => (
                        <option key={m.model_id} value={m.model_id}>
                          {m.model_name} ({m.model_family})
                        </option>
                      ))}
                    </select>
                    {selectedModel && (
                      <span className="form-hint">
                        Threshold: <code>{selectedModel.threshold?.toFixed(6) ?? 'N/A'}</code> ·{' '}
                        {selectedModel.score_type === 'fraud_probability'
                          ? 'Fraud Probability'
                          : 'Reconstruction Error (Anomaly)'}
                      </span>
                    )}
                  </div>

                  {/* Sample Preload Helpers */}
                  <div className="flex items-center gap-1 mb-2">
                    <span className="text-xs text-muted">Test Presets:</span>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => loadPreset('low')}
                      disabled={submitting}
                    >
                      <ShieldCheck size={14} color="var(--green-600)" /> Typical Low-Risk
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => loadPreset('high')}
                      disabled={submitting}
                    >
                      <ShieldAlert size={14} color="var(--red-600)" /> Typical High-Risk
                    </button>
                  </div>

                  <hr style={{ border: 'none', borderTop: 'var(--border)', margin: '1rem 0' }} />

                  {/* Dataset 1: Credit Card Fields */}
                  {selectedDataset === 'credit_card_dataset_1' && (
                    <>
                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-dfh">
                          Distance from Home (km)
                        </label>
                        <input
                          id="inp-dfh"
                          type="number"
                          step="0.01"
                          className="form-input"
                          value={formValues.distance_from_home ?? ''}
                          onChange={(e) => handleInputChange('distance_from_home', e.target.value)}
                        />
                        {fieldErrors.distance_from_home && (
                          <span className="form-error-text">{fieldErrors.distance_from_home}</span>
                        )}
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-dflt">
                          Distance from Last Transaction (km)
                        </label>
                        <input
                          id="inp-dflt"
                          type="number"
                          step="0.01"
                          className="form-input"
                          value={formValues.distance_from_last_transaction ?? ''}
                          onChange={(e) =>
                            handleInputChange('distance_from_last_transaction', e.target.value)
                          }
                        />
                        {fieldErrors.distance_from_last_transaction && (
                          <span className="form-error-text">
                            {fieldErrors.distance_from_last_transaction}
                          </span>
                        )}
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-rpmpp">
                          Ratio to Median Purchase Price
                        </label>
                        <input
                          id="inp-rpmpp"
                          type="number"
                          step="0.01"
                          className="form-input"
                          value={formValues.ratio_to_median_purchase_price ?? ''}
                          onChange={(e) =>
                            handleInputChange('ratio_to_median_purchase_price', e.target.value)
                          }
                        />
                        {fieldErrors.ratio_to_median_purchase_price && (
                          <span className="form-error-text">
                            {fieldErrors.ratio_to_median_purchase_price}
                          </span>
                        )}
                      </div>

                      <div className="grid-2">
                        <div className="form-group">
                          <label className="form-label" htmlFor="inp-rr">
                            Repeat Retailer?
                          </label>
                          <select
                            id="inp-rr"
                            className="form-select"
                            value={formValues.repeat_retailer ?? 1}
                            onChange={(e) => handleInputChange('repeat_retailer', Number(e.target.value))}
                          >
                            <option value={1}>1 (Yes)</option>
                            <option value={0}>0 (No)</option>
                          </select>
                        </div>

                        <div className="form-group">
                          <label className="form-label" htmlFor="inp-chip">
                            Used Chip?
                          </label>
                          <select
                            id="inp-chip"
                            className="form-select"
                            value={formValues.used_chip ?? 1}
                            onChange={(e) => handleInputChange('used_chip', Number(e.target.value))}
                          >
                            <option value={1}>1 (Yes)</option>
                            <option value={0}>0 (No)</option>
                          </select>
                        </div>
                      </div>

                      <div className="grid-2">
                        <div className="form-group">
                          <label className="form-label" htmlFor="inp-pin">
                            Used PIN Number?
                          </label>
                          <select
                            id="inp-pin"
                            className="form-select"
                            value={formValues.used_pin_number ?? 1}
                            onChange={(e) => handleInputChange('used_pin_number', Number(e.target.value))}
                          >
                            <option value={1}>1 (Yes)</option>
                            <option value={0}>0 (No)</option>
                          </select>
                        </div>

                        <div className="form-group">
                          <label className="form-label" htmlFor="inp-online">
                            Online Order?
                          </label>
                          <select
                            id="inp-online"
                            className="form-select"
                            value={formValues.online_order ?? 0}
                            onChange={(e) => handleInputChange('online_order', Number(e.target.value))}
                          >
                            <option value={1}>1 (Yes)</option>
                            <option value={0}>0 (No)</option>
                          </select>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Dataset 2: PaySim Fields */}
                  {selectedDataset === 'paysim_dataset_2' && (
                    <>
                      <div className="alert alert-warn mb-2" style={{ padding: '0.5rem 0.75rem' }}>
                        <span className="text-xs">
                          PaySim is synthetic mobile-money simulation data, not real Indian UPI data.
                        </span>
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-step">
                          Simulation Step (Hour of month, min 1)
                        </label>
                        <input
                          id="inp-step"
                          type="number"
                          step="1"
                          min="1"
                          className="form-input"
                          value={formValues.step ?? 1}
                          onChange={(e) => handleInputChange('step', e.target.value)}
                        />
                        {fieldErrors.step && (
                          <span className="form-error-text">{fieldErrors.step}</span>
                        )}
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-amount">
                          Transaction Amount
                        </label>
                        <input
                          id="inp-amount"
                          type="number"
                          step="0.01"
                          min="0.01"
                          className="form-input"
                          value={formValues.amount ?? ''}
                          onChange={(e) => handleInputChange('amount', e.target.value)}
                        />
                        {fieldErrors.amount && (
                          <span className="form-error-text">{fieldErrors.amount}</span>
                        )}
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="inp-type">
                          Transaction Type
                        </label>
                        <select
                          id="inp-type"
                          className="form-select"
                          value={formValues.type ?? 'TRANSFER'}
                          onChange={(e) => handleInputChange('type', e.target.value)}
                        >
                          <option value="CASH_IN">CASH_IN</option>
                          <option value="CASH_OUT">CASH_OUT</option>
                          <option value="DEBIT">DEBIT</option>
                          <option value="PAYMENT">PAYMENT</option>
                          <option value="TRANSFER">TRANSFER</option>
                        </select>
                        {fieldErrors.type && (
                          <span className="form-error-text">{fieldErrors.type}</span>
                        )}
                      </div>
                    </>
                  )}

                  {apiError && (
                    <div className="alert alert-error mb-2">
                      <AlertTriangle size={16} />
                      <span>{apiError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    className="btn btn-primary w-full"
                    disabled={submitting || !selectedModelId}
                  >
                    {submitting ? (
                      <>
                        <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                        Screening Transaction…
                      </>
                    ) : (
                      'Screen Transaction'
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Results Column */}
          <div>
            {result ? (
              <div className="card">
                <div className="card-body">
                  <div className="flex items-center justify-between mb-2">
                    <span className="section-label" style={{ marginBottom: 0 }}>
                      Screening Assessment
                    </span>
                    <span
                      className={`badge ${
                        result.risk_label === 'High Risk' ? 'badge-red' : 'badge-green'
                      }`}
                      style={{ fontSize: '0.867rem', padding: '0.35rem 0.75rem' }}
                    >
                      {result.risk_label}
                    </span>
                  </div>

                  {/* Primary Score Callout */}
                  <div
                    className="result-panel mb-2"
                    style={{
                      backgroundColor:
                        result.risk_label === 'High Risk' ? 'var(--red-50)' : 'var(--green-50)',
                      borderColor:
                        result.risk_label === 'High Risk' ? 'var(--red-100)' : 'var(--green-100)',
                    }}
                  >
                    <p className="stat-label">
                      {isAutoencoder ? 'Reconstruction Error (Anomaly Score)' : 'Fraud Probability Score'}
                    </p>
                    <p
                      className="stat-value"
                      style={{
                        color:
                          result.risk_label === 'High Risk' ? 'var(--red-700)' : 'var(--green-700)',
                        fontSize: '1.8rem',
                      }}
                    >
                      {result.prediction_score.toFixed(6)}
                    </p>
                    <p className="text-xs text-muted mt-1">
                      Decision Threshold: <code>{result.threshold.toFixed(6)}</code>
                    </p>
                  </div>

                  {/* Explanation Banner */}
                  <div className="alert alert-info mb-2">
                    <div>
                      <strong>Rule Triggered: </strong>
                      <span>{result.explanation}</span>
                    </div>
                  </div>

                  {/* Metadata Rows */}
                  <div className="result-panel mb-2">
                    <div className="result-row">
                      <span className="result-label">Dataset</span>
                      <span className="result-value">
                        {DATASET_LABELS[result.dataset_id as DatasetId] ?? result.dataset_id}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-label">Model ID</span>
                      <span className="result-value">{result.model_id}</span>
                    </div>
                    <div className="result-row">
                      <span className="result-label">Score Metric Type</span>
                      <span className="result-value">
                        {isAutoencoder ? 'Reconstruction Error (MSE)' : 'Fraud Probability'}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-label">Risk Flag</span>
                      <span className="result-value">{result.risk_label}</span>
                    </div>
                  </div>

                  {/* Preprocessed Vector Inspection */}
                  {result.preprocessed_vector && result.preprocessed_vector.length > 0 && (
                    <div>
                      <p className="text-xs text-muted mb-1" style={{ fontWeight: 600 }}>
                        Engineered Input Vector to Model ({result.preprocessed_vector.length} dimensions):
                      </p>
                      <div
                        className="mono text-xs"
                        style={{
                          background: 'var(--fg-50)',
                          padding: '0.5rem 0.75rem',
                          borderRadius: 'var(--radius-md)',
                          border: 'var(--border)',
                          wordBreak: 'break-all',
                        }}
                      >
                        [{result.preprocessed_vector.map((v) => v.toFixed(4)).join(', ')}]
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="card">
                <div className="card-body text-center" style={{ padding: '3.5rem 1.5rem' }}>
                  <Info
                    size={32}
                    color="var(--blue-600)"
                    style={{ margin: '0 auto 1rem', opacity: 0.8 }}
                  />
                  <h3 className="card-title">Awaiting Transaction Input</h3>
                  <p className="card-text" style={{ maxWidth: 360, margin: '0 auto' }}>
                    Adjust feature values in the form or load one of the test presets, then click
                    &quot;Screen Transaction&quot; to execute real backend model inference.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
