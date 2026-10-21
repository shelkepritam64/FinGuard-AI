import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Upload,
  Download,
  FileSpreadsheet,
  AlertTriangle,
  Filter,
  Search,
  ArrowUpDown,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';
import type { ModelRegistryEntry, CSVPredictionResponse, DatasetId } from '../types';
import { Loading, ErrorBox } from '../components/StateDisplays';

const TEMPLATES: Record<DatasetId, { filename: string; content: string }> = {
  credit_card_dataset_1: {
    filename: 'credit_card_template.csv',
    content:
      'distance_from_home,distance_from_last_transaction,ratio_to_median_purchase_price,repeat_retailer,used_chip,used_pin_number,online_order\n5.2,1.1,0.85,1.0,1.0,0.0,0.0\n85.4,32.0,5.60,1.0,0.0,0.0,1.0\n12.0,0.4,1.05,1.0,1.0,1.0,0.0',
  },
  paysim_dataset_2: {
    filename: 'paysim_template.csv',
    content:
      'step,amount,type\n1,9839.64,PAYMENT\n1,1864.28,PAYMENT\n1,181.00,TRANSFER\n1,181.00,CASH_OUT\n2,11668.14,PAYMENT',
  },
};

export function CSVAnalysisPage() {
  const [searchParams] = useSearchParams();
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Form selections
  const [selectedDataset, setSelectedDataset] = useState<DatasetId>('credit_card_dataset_1');
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Execution state
  const [processing, setProcessing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<CSVPredictionResponse | null>(null);

  // Table filtering & pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState<'all' | 'High Risk' | 'Low Risk'>('all');
  const [sortField, setSortField] = useState<'row_index' | 'prediction_score'>('prediction_score');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Initialize models and URL query params
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

        const availableForDataset = res.models.filter(
          (m) => m.dataset_id === initialDataset && m.is_available
        );

        if (urlModel && availableForDataset.some((m) => m.model_id === urlModel)) {
          setSelectedModelId(urlModel);
        } else if (availableForDataset.length > 0) {
          setSelectedModelId(availableForDataset[0].model_id);
        }
      })
      .catch((err) => {
        setLoadError(err.message);
        setLoadingModels(false);
      });
  }, [searchParams]);

  // Update selected model when dataset changes
  const handleDatasetChange = (newDs: DatasetId) => {
    setSelectedDataset(newDs);
    setSelectedFile(null);
    setValidationError(null);
    setResult(null);

    const available = models.filter((m) => m.dataset_id === newDs && m.is_available);
    if (available.length > 0) {
      setSelectedModelId(available[0].model_id);
    } else {
      setSelectedModelId('');
    }
  };

  const selectedModel = useMemo(
    () => models.find((m) => m.model_id === selectedModelId),
    [models, selectedModelId]
  );

  const availableModels = useMemo(
    () => models.filter((m) => m.dataset_id === selectedDataset && m.is_available),
    [models, selectedDataset]
  );

  // Template download handler
  const handleDownloadTemplate = () => {
    const tmpl = TEMPLATES[selectedDataset];
    const blob = new Blob([tmpl.content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', tmpl.filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // File selection & basic client-side pre-validation
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setValidationError('Please select a valid .csv file.');
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setValidationError('The selected CSV file is empty (0 bytes).');
      setSelectedFile(null);
      return;
    }

    setValidationError(null);
    setSelectedFile(file);
    setResult(null);
  };

  // Submit batch analysis to real backend
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setValidationError('Please select a CSV file to analyze.');
      return;
    }
    if (!selectedModelId) {
      setValidationError('Please select an available model.');
      return;
    }

    setProcessing(true);
    setApiError(null);
    setValidationError(null);
    setResult(null);

    try {
      const response = await api.predictCSV(selectedDataset, selectedModelId, selectedFile);
      setResult(response);
      setPage(1);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : 'Batch prediction request failed.');
    } finally {
      setProcessing(false);
    }
  };

  // Download prediction CSV from real backend
  const handleDownloadResults = async () => {
    if (!selectedFile || !selectedModelId) return;
    setDownloading(true);
    try {
      const blob = await api.downloadCSV(selectedDataset, selectedModelId, selectedFile);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `finguard_predictions_${selectedModelId}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to download prediction CSV.');
    } finally {
      setDownloading(false);
    }
  };

  // Computed score statistics from real results
  const scoreStats = useMemo(() => {
    if (!result || result.predictions.length === 0) return null;
    const scores = result.predictions.map((p) => p.prediction_score);
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    const sum = scores.reduce((a, b) => a + b, 0);
    const mean = sum / scores.length;

    const sorted = [...scores].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const median = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;

    return { min, max, mean, median };
  }, [result]);

  // Highest-scoring or highest-anomaly transactions
  const topFlagged = useMemo(() => {
    if (!result) return [];
    return [...result.predictions]
      .sort((a, b) => b.prediction_score - a.prediction_score)
      .slice(0, 5);
  }, [result]);

  // Filtered & sorted table rows
  const filteredPredictions = useMemo(() => {
    if (!result) return [];
    let list = result.predictions;

    if (riskFilter !== 'all') {
      list = list.filter((r) => r.risk_label === riskFilter);
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter((r) => {
        if (r.row_index.toString().includes(q)) return true;
        return Object.entries(r.input_features).some(([k, v]) =>
          `${k}:${v}`.toLowerCase().includes(q)
        );
      });
    }

    list = [...list].sort((a, b) => {
      let cmp = 0;
      if (sortField === 'row_index') {
        cmp = a.row_index - b.row_index;
      } else {
        cmp = a.prediction_score - b.prediction_score;
      }
      return sortAsc ? cmp : -cmp;
    });

    return list;
  }, [result, riskFilter, searchTerm, sortField, sortAsc]);

  const totalPages = Math.ceil(filteredPredictions.length / pageSize) || 1;
  const paginatedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredPredictions.slice(start, start + pageSize);
  }, [filteredPredictions, page, pageSize]);

  const isAutoencoder = result?.score_type === 'mean_squared_reconstruction_error';

  return (
    <div className="page">
      <header className="page-header">
        <h1>Batch CSV Transaction Screening</h1>
        <p>
          Screen batches of financial transactions against pre-trained machine learning models.
          Upload a structured CSV matching the dataset schema to compute screening scores and flag anomalies.
        </p>
      </header>

      {loadingModels && <Loading message="Loading model registry…" />}
      {loadError && <ErrorBox message={loadError} />}

      {!loadingModels && !loadError && (
        <>
          {/* Configuration & Upload Form */}
          <section className="mb-3">
            <div className="card">
              <div className="card-body">
                <form onSubmit={handleSubmit}>
                  <div className="grid-2 mb-2">
                    {/* Step 1: Select Dataset */}
                    <div className="form-group">
                      <label className="form-label" htmlFor="dataset-select">
                        1. Select Dataset Target
                      </label>
                      <select
                        id="dataset-select"
                        className="form-select"
                        value={selectedDataset}
                        onChange={(e) => handleDatasetChange(e.target.value as DatasetId)}
                        disabled={processing}
                      >
                        <option value="credit_card_dataset_1">Credit Card Fraud Detection</option>
                        <option value="paysim_dataset_2">PaySim Synthetic Mobile Money</option>
                      </select>
                      <span className="form-hint">
                        {selectedDataset === 'paysim_dataset_2'
                          ? 'Note: PaySim is synthetic mobile-money simulation data, not real Indian UPI data.'
                          : 'Standard credit card fraud benchmark features.'}
                      </span>
                    </div>

                    {/* Step 2: Select Model */}
                    <div className="form-group">
                      <label className="form-label" htmlFor="model-select">
                        2. Select Available Model
                      </label>
                      <select
                        id="model-select"
                        className="form-select"
                        value={selectedModelId}
                        onChange={(e) => setSelectedModelId(e.target.value)}
                        disabled={processing || availableModels.length === 0}
                      >
                        {availableModels.map((m) => (
                          <option key={m.model_id} value={m.model_id}>
                            {m.model_name} ({m.model_family})
                          </option>
                        ))}
                      </select>
                      <span className="form-hint">
                        {selectedModel
                          ? `Score Type: ${
                              selectedModel.score_type === 'fraud_probability'
                                ? 'Fraud Probability'
                                : 'Reconstruction Error (Anomaly Score)'
                            } · Threshold: ${selectedModel.threshold?.toFixed(6) ?? 'N/A'}`
                          : 'No available model for this dataset'}
                      </span>
                    </div>
                  </div>

                  {/* Step 3: Required Columns & Template Download */}
                  {selectedModel && (
                    <div className="alert alert-info mb-2 flex items-center justify-between flex-wrap gap-1">
                      <div>
                        <div className="flex items-center gap-1 mb-1">
                          <FileText size={16} />
                          <strong>Required CSV Columns ({selectedModel.required_raw_features.length}):</strong>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {selectedModel.required_raw_features.map((feat) => (
                            <span key={feat} className="badge badge-gray mono text-xs">
                              {feat}
                            </span>
                          ))}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={handleDownloadTemplate}
                        title="Download sample template CSV"
                      >
                        <Download size={14} /> Download CSV Template
                      </button>
                    </div>
                  )}

                  {/* Step 4: Upload CSV */}
                  <div className="form-group mb-2">
                    <label className="form-label" htmlFor="csv-file-input">
                      3. Upload CSV File
                    </label>
                    <label
                      htmlFor="csv-file-input"
                      className={`upload-zone ${selectedFile ? 'dragging' : ''}`}
                      style={{ display: 'block', textAlign: 'center' }}
                    >
                      <Upload size={24} style={{ margin: '0 auto 0.5rem', color: 'var(--blue-600)' }} />
                      <p style={{ fontWeight: 600, color: 'var(--fg-800)' }}>
                        {selectedFile ? selectedFile.name : 'Click to select or drop a CSV file'}
                      </p>
                      <p className="text-xs text-muted mt-1">
                        {selectedFile
                          ? `${(selectedFile.size / 1024).toFixed(1)} KB selected`
                          : 'Must contain headers matching the required schema above. Max 10MB.'}
                      </p>
                      <input
                        id="csv-file-input"
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                        disabled={processing}
                      />
                    </label>
                  </div>

                  {/* Validation and API Error Displays */}
                  {validationError && (
                    <div className="alert alert-warn mb-2">
                      <AlertTriangle size={16} />
                      <span>{validationError}</span>
                    </div>
                  )}

                  {apiError && (
                    <div className="alert alert-error mb-2">
                      <AlertCircle size={16} />
                      <span>{apiError}</span>
                    </div>
                  )}

                  {/* Submit Action */}
                  <div className="flex items-center gap-1">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={processing || !selectedFile || !selectedModelId}
                    >
                      {processing ? (
                        <>
                          <div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                          Running Real Inference…
                        </>
                      ) : (
                        <>
                          <FileSpreadsheet size={16} /> Submit for Screening
                        </>
                      )}
                    </button>
                    {selectedFile && !processing && (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => {
                          setSelectedFile(null);
                          setResult(null);
                          setValidationError(null);
                        }}
                      >
                        Clear File
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
          </section>

          {/* Results Dashboard */}
          {result && (
            <section className="mb-3">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-1">
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--fg-900)' }}>
                    Screening Results & Dashboard
                  </h2>
                  <p className="text-xs text-muted">
                    Model: <strong>{result.model_id}</strong> · Score Type:{' '}
                    <strong>
                      {isAutoencoder
                        ? 'Reconstruction Error (Anomaly Score)'
                        : 'Fraud Probability'}
                    </strong>{' '}
                    · Threshold: <code>{result.threshold_used.toFixed(6)}</code>
                  </p>
                </div>

                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleDownloadResults}
                  disabled={downloading}
                >
                  <Download size={14} />
                  {downloading ? 'Preparing Download…' : 'Download Prediction CSV'}
                </button>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid-3 mb-2">
                <div className="card">
                  <div className="stat">
                    <p className="stat-label">Total Transactions</p>
                    <p className="stat-value">{result.total_rows.toLocaleString()}</p>
                    <p className="stat-note">Parsed and scored rows</p>
                  </div>
                </div>

                <div className="card">
                  <div className="stat">
                    <p className="stat-label">Flagged for Review (High Risk)</p>
                    <p className="stat-value" style={{ color: 'var(--red-600)' }}>
                      {result.high_risk_count.toLocaleString()}
                    </p>
                    <p className="stat-note">
                      {((result.high_risk_count / result.total_rows) * 100).toFixed(2)}% of batch
                    </p>
                  </div>
                </div>

                <div className="card">
                  <div className="stat">
                    <p className="stat-label">Normal / Low Risk</p>
                    <p className="stat-value" style={{ color: 'var(--green-700)' }}>
                      {result.low_risk_count.toLocaleString()}
                    </p>
                    <p className="stat-note">
                      {((result.low_risk_count / result.total_rows) * 100).toFixed(2)}% of batch
                    </p>
                  </div>
                </div>
              </div>

              {/* Risk Distribution Visual Bar */}
              <div className="card mb-2">
                <div className="card-body">
                  <div className="flex items-center justify-between mb-1">
                    <span className="section-label" style={{ marginBottom: 0 }}>
                      Risk Distribution
                    </span>
                    <span className="text-xs text-muted">
                      Low: {result.low_risk_count} | High: {result.high_risk_count}
                    </span>
                  </div>

                  <div className="distribution-bar mb-1">
                    <div
                      className="distribution-segment-low"
                      style={{
                        width: `${(result.low_risk_count / result.total_rows) * 100}%`,
                      }}
                      title={`Low Risk: ${result.low_risk_count}`}
                    />
                    <div
                      className="distribution-segment-high"
                      style={{
                        width: `${(result.high_risk_count / result.total_rows) * 100}%`,
                      }}
                      title={`High Risk: ${result.high_risk_count}`}
                    />
                  </div>

                  <div className="flex items-center gap-2 text-xs text-muted">
                    <span className="flex items-center gap-1">
                      <span
                        style={{
                          display: 'inline-block',
                          width: 8,
                          height: 8,
                          backgroundColor: 'var(--green-600)',
                          borderRadius: 2,
                        }}
                      />
                      Low Risk ({((result.low_risk_count / result.total_rows) * 100).toFixed(1)}%)
                    </span>
                    <span className="flex items-center gap-1">
                      <span
                        style={{
                          display: 'inline-block',
                          width: 8,
                          height: 8,
                          backgroundColor: 'var(--red-600)',
                          borderRadius: 2,
                        }}
                      />
                      High Risk ({((result.high_risk_count / result.total_rows) * 100).toFixed(1)}%)
                    </span>
                  </div>
                </div>
              </div>

              {/* Score Distribution Metrics */}
              {scoreStats && (
                <div className="card mb-2">
                  <div className="card-body">
                    <p className="section-label">Score Statistics ({isAutoencoder ? 'Anomaly MSE' : 'Probability'})</p>
                    <div className="grid-2">
                      <div className="result-row">
                        <span className="result-label">Minimum Score</span>
                        <span className="result-value">{scoreStats.min.toFixed(6)}</span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Maximum Score</span>
                        <span className="result-value">{scoreStats.max.toFixed(6)}</span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Mean Score</span>
                        <span className="result-value">{scoreStats.mean.toFixed(6)}</span>
                      </div>
                      <div className="result-row">
                        <span className="result-label">Median Score</span>
                        <span className="result-value">{scoreStats.median.toFixed(6)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Top Flagged Transactions */}
              {topFlagged.length > 0 && (
                <div className="card mb-2">
                  <div className="card-body">
                    <p className="section-label">
                      Highest-{isAutoencoder ? 'Anomaly' : 'Risk'} Transactions (Top {topFlagged.length})
                    </p>
                    <div className="table-wrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Row #</th>
                            <th>Score ({isAutoencoder ? 'Reconstruction Error' : 'Fraud Prob'})</th>
                            <th>Threshold</th>
                            <th>Risk Assessment</th>
                            <th>Key Features</th>
                          </tr>
                        </thead>
                        <tbody>
                          {topFlagged.map((row) => (
                            <tr key={row.row_index}>
                              <td className="table-mono">#{row.row_index}</td>
                              <td className="table-mono" style={{ fontWeight: 600 }}>
                                {row.prediction_score.toFixed(6)}
                              </td>
                              <td className="table-mono text-xs">{row.threshold.toFixed(6)}</td>
                              <td>
                                <span
                                  className={`badge ${
                                    row.risk_label === 'High Risk' ? 'badge-red' : 'badge-green'
                                  }`}
                                >
                                  {row.risk_label}
                                </span>
                              </td>
                              <td className="text-xs mono">
                                {Object.entries(row.input_features)
                                  .slice(0, 3)
                                  .map(([k, v]) => `${k}: ${v}`)
                                  .join(' · ')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Comprehensive Transaction Table with Filtering, Sorting, and Search */}
              <div className="card">
                <div className="card-body">
                  <div className="flex items-center justify-between mb-2 flex-wrap gap-1">
                    <h3 className="card-title" style={{ marginBottom: 0 }}>
                      All Batch Transactions ({filteredPredictions.length})
                    </h3>
                  </div>

                  {/* Toolbar */}
                  <div className="toolbar">
                    <div className="flex items-center gap-1">
                      <Search size={16} color="var(--fg-500)" />
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Search row or feature value…"
                        value={searchTerm}
                        onChange={(e) => {
                          setSearchTerm(e.target.value);
                          setPage(1);
                        }}
                      />
                    </div>

                    <div className="flex items-center gap-1">
                      <Filter size={16} color="var(--fg-500)" />
                      <select
                        className="form-select"
                        style={{ maxWidth: 160 }}
                        value={riskFilter}
                        onChange={(e) => {
                          setRiskFilter(e.target.value as 'all' | 'High Risk' | 'Low Risk');
                          setPage(1);
                        }}
                      >
                        <option value="all">All Risks</option>
                        <option value="High Risk">High Risk Only</option>
                        <option value="Low Risk">Low Risk Only</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-1">
                      <ArrowUpDown size={16} color="var(--fg-500)" />
                      <select
                        className="form-select"
                        style={{ maxWidth: 180 }}
                        value={`${sortField}-${sortAsc ? 'asc' : 'desc'}`}
                        onChange={(e) => {
                          const [field, dir] = e.target.value.split('-');
                          setSortField(field as 'row_index' | 'prediction_score');
                          setSortAsc(dir === 'asc');
                          setPage(1);
                        }}
                      >
                        <option value="prediction_score-desc">Score: High to Low</option>
                        <option value="prediction_score-asc">Score: Low to High</option>
                        <option value="row_index-asc">Row: Ascending</option>
                        <option value="row_index-desc">Row: Descending</option>
                      </select>
                    </div>
                  </div>

                  {/* Table */}
                  <div className="table-wrap mb-2">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Row #</th>
                          <th>Score ({isAutoencoder ? 'Reconstruction Error' : 'Probability'})</th>
                          <th>Threshold</th>
                          <th>Risk Label</th>
                          <th>Rule Explanation</th>
                          <th>Features</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedRows.map((row) => (
                          <tr key={row.row_index}>
                            <td className="table-mono">#{row.row_index}</td>
                            <td className="table-mono" style={{ fontWeight: 600 }}>
                              {row.prediction_score.toFixed(6)}
                            </td>
                            <td className="table-mono text-xs">{row.threshold.toFixed(6)}</td>
                            <td>
                              <span
                                className={`badge ${
                                  row.risk_label === 'High Risk' ? 'badge-red' : 'badge-green'
                                }`}
                              >
                                {row.risk_label}
                              </span>
                            </td>
                            <td className="text-xs text-muted">{row.decision_rule}</td>
                            <td className="text-xs mono">
                              {Object.entries(row.input_features)
                                .map(([k, v]) => `${k}=${v}`)
                                .join(', ')}
                            </td>
                          </tr>
                        ))}
                        {paginatedRows.length === 0 && (
                          <tr>
                            <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                              No transactions match the search/filter criteria.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted">
                        Page {page} of {totalPages} ({filteredPredictions.length} records)
                      </span>
                      <div className="flex gap-1">
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={page <= 1}
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                        >
                          Previous
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={page >= totalPages}
                          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
