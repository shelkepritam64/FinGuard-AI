import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { ScreeningHistoryItem, ScreeningHistoryResponse } from '../types';
import {
  Shield,
  FileSpreadsheet,
  Activity,
  CheckCircle,
  Trash2,
  LogOut,
  ArrowRight,
  Lock,
  Info,
  Search,
  RefreshCw,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  XCircle,
  KeyRound
} from 'lucide-react';

export const UserDashboardPage: React.FC = () => {
  const { user, logout, deleteAccount } = useAuth();
  const navigate = useNavigate();

  // History state
  const [historyItems, setHistoryItems] = useState<ScreeningHistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);
  const [historyError, setHistoryError] = useState<string | null>(null);

  // Filters and Pagination
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [datasetFilter, setDatasetFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;

  // Account deletion modal state
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Clear history state
  const [clearingHistory, setClearingHistory] = useState<boolean>(false);
  const [showClearConfirm, setShowClearConfirm] = useState<boolean>(false);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Reset page when filters change
  const handleTypeChange = (val: string) => {
    setTypeFilter(val);
    setPage(1);
  };

  const handleRiskChange = (val: string) => {
    setRiskFilter(val);
    setPage(1);
  };

  const handleDatasetChange = (val: string) => {
    setDatasetFilter(val);
    setPage(1);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setDebouncedSearch('');
    setTypeFilter('all');
    setRiskFilter('all');
    setDatasetFilter('all');
    setPage(1);
  };

  // Fetch history from backend (strictly scoped to server-verified user identity)
  const fetchHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      setHistoryError(null);
      const offset = (page - 1) * pageSize;
      const res: ScreeningHistoryResponse = await api.getUserHistory({
        search: debouncedSearch.trim() || undefined,
        screening_type: typeFilter !== 'all' ? typeFilter : undefined,
        risk_classification: riskFilter !== 'all' ? riskFilter : undefined,
        dataset_id: datasetFilter !== 'all' ? datasetFilter : undefined,
        offset,
        limit: pageSize,
      });
      setHistoryItems(res.items);
      setTotalCount(res.total);
    } catch (err: any) {
      setHistoryError(err?.message || 'Failed to load screening history.');
    } finally {
      setLoadingHistory(false);
    }
  }, [page, debouncedSearch, typeFilter, riskFilter, datasetFilter]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  if (!user) return null;

  const handleDelete = async () => {
    try {
      setDeleting(true);
      setDeleteError(null);
      await deleteAccount();
      navigate('/', { replace: true });
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to delete account.');
      setDeleting(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      setClearingHistory(true);
      await api.clearUserHistory();
      setShowClearConfirm(false);
      await fetchHistory();
    } catch (err: any) {
      setHistoryError(err?.message || 'Failed to clear screening history.');
    } finally {
      setClearingHistory(false);
    }
  };

  const formattedDate = user.created_at
    ? new Date(user.created_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Active';

  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const startItem = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalCount);

  const hasActiveFilters =
    debouncedSearch.trim() !== '' ||
    typeFilter !== 'all' ||
    riskFilter !== 'all' ||
    datasetFilter !== 'all';

  return (
    <div className="dash-container">
      {/* ── 1. Header ── */}
      <div className="dash-header">
        <div className="dash-identity">
          <div className="dash-avatar">
            {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="dash-user-info">
            <h1>
              <span>{user.full_name}</span>
              <span className="badge badge-blue">{user.role}</span>
              <span className="badge badge-green">
                <CheckCircle size={11} />
                <span>{user.status}</span>
              </span>
            </h1>
            <p>{user.email}</p>
          </div>
        </div>

        <div className="dash-actions">
          {user.role === 'admin' && (
            <Link to="/admin" className="btn btn-sm btn-primary">
              <Shield size={14} />
              <span>Admin Console</span>
            </Link>
          )}
          <button
            onClick={() => {
              logout();
              navigate('/');
            }}
            className="btn btn-sm"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* ── 2. Metric Overview ── */}
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Single Screenings</div>
          <div className="metric-value">{user.screening_count || 0}</div>
          <div className="metric-note">Individual transactions scored</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">CSV Batch Runs</div>
          <div className="metric-value">{user.csv_count || 0}</div>
          <div className="metric-note">Batch files evaluated</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total History Records</div>
          <div className="metric-value">{totalCount}</div>
          <div className="metric-note">Audited executions</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Account Created</div>
          <div className="metric-value" style={{ fontSize: '1.15rem' }}>{formattedDate}</div>
          <div className="metric-note">Verified member identity</div>
        </div>
      </div>

      {/* ── 3. Quick Actions ── */}
      <div className="quick-actions">
        <Link to="/transaction" className="quick-action-card">
          <div className="quick-action-icon blue">
            <Activity size={20} />
          </div>
          <div>
            <h3>Screen Individual Transaction</h3>
            <p>Score real-time feature vectors against XGBoost, MLP, or Autoencoder</p>
          </div>
          <ArrowRight size={16} style={{ marginLeft: 'auto', color: 'var(--blue-600)' }} />
        </Link>

        <Link to="/csv" className="quick-action-card">
          <div className="quick-action-icon green">
            <FileSpreadsheet size={20} />
          </div>
          <div>
            <h3>Batch CSV Screening</h3>
            <p>Upload dataset batches, inspect flagged rows, and export predictions</p>
          </div>
          <ArrowRight size={16} style={{ marginLeft: 'auto', color: 'var(--green-600)' }} />
        </Link>
      </div>

      {/* ── 4. History Section ── */}
      <div className="history-section">
        <div className="history-header">
          <div>
            <h2>Screening Activity History</h2>
          </div>
          <div className="history-header-actions">
            <button
              onClick={fetchHistory}
              disabled={loadingHistory}
              className="btn btn-sm"
              title="Refresh screening history"
            >
              <RefreshCw size={13} className={loadingHistory ? 'spinner-inline' : ''} />
              <span>Refresh</span>
            </button>

            {historyItems.length > 0 && !showClearConfirm && (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="btn btn-sm"
                title="Clear screening history"
              >
                <Trash2 size={13} />
                <span>Clear History</span>
              </button>
            )}

            {showClearConfirm && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: 'var(--red-50)', padding: '0.2rem 0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--red-100)' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--red-700)' }}>Clear all?</span>
                <button
                  onClick={handleClearHistory}
                  disabled={clearingHistory}
                  className="btn-danger"
                  style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                >
                  {clearingHistory ? 'Clearing…' : 'Confirm'}
                </button>
                <button
                  onClick={() => setShowClearConfirm(false)}
                  className="btn btn-sm"
                  style={{ padding: '0.2rem 0.5rem' }}
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Filter Bar */}
        <div className="filter-bar">
          <div style={{ position: 'relative', flex: '1 1 200px' }}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search model, dataset…"
              className="form-input"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-400)' }}
              >
                <XCircle size={14} />
              </button>
            )}
          </div>

          <select
            value={typeFilter}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="form-select"
          >
            <option value="all">All Screening Types</option>
            <option value="single_screening">Single Transaction</option>
            <option value="csv_batch">CSV Batch Run</option>
          </select>

          <select
            value={riskFilter}
            onChange={(e) => handleRiskChange(e.target.value)}
            className="form-select"
          >
            <option value="all">All Risk Labels</option>
            <option value="High Risk">High Risk</option>
            <option value="Low Risk">Low Risk</option>
          </select>

          <select
            value={datasetFilter}
            onChange={(e) => handleDatasetChange(e.target.value)}
            className="form-select"
          >
            <option value="all">All Datasets</option>
            <option value="credit_card_dataset_1">Credit Card Fraud</option>
            <option value="paysim_dataset_2">PaySim Mobile Money</option>
          </select>
        </div>

        {/* Active Filters */}
        {hasActiveFilters && (
          <div className="active-filters">
            <span>Active filters:</span>
            {debouncedSearch && <span className="filter-pill">"{debouncedSearch}"</span>}
            {typeFilter !== 'all' && (
              <span className="filter-pill">
                {typeFilter === 'single_screening' ? 'Single' : 'CSV Batch'}
              </span>
            )}
            {riskFilter !== 'all' && <span className="filter-pill">{riskFilter}</span>}
            {datasetFilter !== 'all' && (
              <span className="filter-pill">
                {datasetFilter === 'credit_card_dataset_1' ? 'Credit Card' : 'PaySim'}
              </span>
            )}
            <button
              onClick={resetFilters}
              className="btn-ghost"
              style={{ fontSize: '0.733rem', padding: '0.1rem 0.35rem' }}
            >
              Reset all
            </button>
          </div>
        )}

        {/* History Error */}
        {historyError && (
          <div className="alert alert-error" style={{ margin: '1rem' }}>
            <AlertCircle size={16} />
            <span style={{ flex: 1 }}>{historyError}</span>
            <button onClick={fetchHistory} className="btn btn-sm">Try Again</button>
          </div>
        )}

        {/* History Content */}
        {loadingHistory ? (
          <div className="state-box">
            <div className="spinner" />
            <p>Loading your verified screening history…</p>
          </div>
        ) : historyItems.length === 0 ? (
          <div className="state-box">
            {hasActiveFilters ? (
              <div>
                <Search size={28} />
                <h3 style={{ fontWeight: 600, color: 'var(--fg-900)', marginBottom: '0.25rem' }}>No matching records</h3>
                <p style={{ maxWidth: 360, margin: '0 auto 1rem', fontSize: '0.867rem' }}>
                  No screening records match your current filters.
                </p>
                <button onClick={resetFilters} className="btn btn-sm">Clear All Filters</button>
              </div>
            ) : (
              <div>
                <Sparkles size={28} />
                <h3 style={{ fontWeight: 600, color: 'var(--fg-900)', marginBottom: '0.25rem' }}>No Screening History Yet</h3>
                <p style={{ maxWidth: 420, margin: '0 auto 1.25rem', fontSize: '0.867rem' }}>
                  Run an individual transaction screening or batch CSV evaluation to begin building your verified audit history.
                </p>
                <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                  <Link to="/transaction" className="btn btn-primary btn-sm">Screen Single Transaction</Link>
                  <Link to="/csv" className="btn btn-sm">Upload Batch CSV</Link>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="history-table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Type</th>
                  <th>Model</th>
                  <th>Dataset</th>
                  <th>Score / Threshold</th>
                  <th>Risk Classification</th>
                  <th style={{ textAlign: 'right' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {historyItems.map((item) => {
                  const isHighRisk = item.risk_classification === 'High Risk';
                  const isCsv = item.screening_type === 'csv_batch';
                  const dateStr = item.timestamp
                    ? new Date(item.timestamp).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })
                    : 'N/A';

                  return (
                    <tr key={item.id}>
                      <td className="table-mono" style={{ whiteSpace: 'nowrap' }}>{dateStr}</td>
                      <td>
                        {isCsv ? (
                          <span className="badge badge-gray" style={{ background: '#f3e8ff', color: '#6b21a8' }}>
                            <FileSpreadsheet size={11} />
                            <span>CSV ({item.row_count} rows)</span>
                          </span>
                        ) : (
                          <span className="badge badge-blue">
                            <Activity size={11} />
                            <span>Single</span>
                          </span>
                        )}
                      </td>
                      <td>
                        <code className="table-mono" style={{ fontWeight: 600, color: 'var(--fg-800)' }}>
                          {item.model_id}
                        </code>
                      </td>
                      <td>
                        {item.dataset_id === 'credit_card_dataset_1'
                          ? 'Credit Card'
                          : item.dataset_id === 'paysim_dataset_2'
                          ? 'PaySim'
                          : item.dataset_id}
                      </td>
                      <td className="table-mono">
                        {isCsv ? (
                          <span style={{ color: 'var(--fg-600)' }}>
                            {item.flagged_count} of {item.row_count} flagged
                          </span>
                        ) : item.prediction_score !== null && item.prediction_score !== undefined ? (
                          <span>
                            <strong style={{ color: isHighRisk ? 'var(--red-600)' : 'var(--green-700)' }}>
                              {item.prediction_score.toFixed(4)}
                            </strong>
                            {item.threshold !== null && item.threshold !== undefined && (
                              <span style={{ color: 'var(--fg-400)', fontSize: '0.733rem', marginLeft: 4 }}>
                                (thr: {item.threshold.toFixed(2)})
                              </span>
                            )}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {item.risk_classification ? (
                          <span className={`badge ${isHighRisk ? 'badge-red' : 'badge-green'}`}>
                            {item.risk_classification}
                          </span>
                        ) : (
                          <span className="badge badge-gray">Evaluated</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <span className="badge badge-green" style={{ background: 'transparent', padding: 0 }}>
                          <CheckCircle size={12} />
                          <span style={{ textTransform: 'capitalize' }}>{item.request_status || 'completed'}</span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loadingHistory && historyItems.length > 0 && (
          <div className="pagination">
            <div>
              Showing <strong>{startItem}</strong> to <strong>{endItem}</strong> of{' '}
              <strong>{totalCount}</strong> entries
            </div>
            <div className="pagination-controls">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="btn btn-sm"
              >
                <ChevronLeft size={13} />
                <span>Previous</span>
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="btn btn-sm"
              >
                <span>Next</span>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── 5. Bottom Two-Column: Account Details + Security/Danger Zone ── */}
      <div className="dash-bottom-grid">
        {/* Left Column: Account Details & Privacy */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="account-info-card">
            <h2>Account Details</h2>
            <div className="account-detail">
              <span className="account-detail-label">Full Name</span>
              <span style={{ color: 'var(--fg-900)', fontWeight: 500 }}>{user.full_name}</span>
            </div>
            <div className="account-detail">
              <span className="account-detail-label">Email Address</span>
              <span className="account-detail-value">{user.email}</span>
            </div>
            <div className="account-detail">
              <span className="account-detail-label">Account Role</span>
              <span className="badge badge-blue">{user.role}</span>
            </div>
            <div className="account-detail">
              <span className="account-detail-label">Account Status</span>
              <span className="badge badge-green">{user.status}</span>
            </div>
            <div className="account-detail">
              <span className="account-detail-label">Server-Verified User ID</span>
              <span className="account-detail-value">{user.id}</span>
            </div>
          </div>

          <div className="info-box">
            <Info size={18} />
            <div>
              <strong>Zero-Storage Privacy Policy:</strong> FinGuard AI never stores raw transaction feature vectors, credit card numbers, or uploaded CSV files. Only verified model audit metadata (model ID, timestamp, risk score, and risk label) is persisted in your user history.
            </div>
          </div>
        </div>

        {/* Right Column: Security & Danger Zone */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="account-info-card">
            <h2>Security & Session</h2>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem', fontSize: '0.867rem', color: 'var(--fg-600)' }}>
              <KeyRound size={16} style={{ color: 'var(--blue-600)', flexShrink: 0, marginTop: 2 }} />
              <div>
                Cryptographic JWT token authentication. User identity is strictly validated on each backend request.
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', fontSize: '0.867rem', color: 'var(--fg-600)' }}>
              <Lock size={16} style={{ color: 'var(--blue-600)', flexShrink: 0, marginTop: 2 }} />
              <div>
                Role-based access control protects all admin and user screening endpoints.
              </div>
            </div>
          </div>

          <div className="danger-section">
            <h3>Danger Zone</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--fg-500)', marginBottom: '0.75rem' }}>
              Permanently delete your account, session credentials, and all screening history records.
            </p>
            {deleteError && (
              <p style={{ fontSize: '0.8rem', color: 'var(--red-600)', marginBottom: '0.5rem' }}>{deleteError}</p>
            )}

            {!confirmDelete ? (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="btn-danger-outline"
              >
                <Trash2 size={14} />
                <span>Request Account Deletion</span>
              </button>
            ) : (
              <div className="confirm-box">
                <p>
                  Are you sure? This action is permanent and will remove all your account data.
                </p>
                <div className="confirm-actions">
                  <button
                    type="button"
                    disabled={deleting}
                    onClick={handleDelete}
                    className="btn-danger"
                  >
                    {deleting ? 'Deleting…' : 'Yes, Delete Account'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(false)}
                    className="btn btn-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
