import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { fetchRuns } from '../api';
import StatusBadge from '../components/StatusBadge';
import { ExternalLink } from 'lucide-react';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

export default function PipelineRuns({ refreshKey }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [page, setPage]       = useState(1);
  const [search, setSearch]   = useState('');
  const [status, setStatus]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: 20 };
      if (search) params.repo   = search;
      if (status) params.status = status;
      const result = await fetchRuns(params);
      setData(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [page, search, status, refreshKey]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Pipeline Runs</h2>
        <p className="page-subtitle">All CI/CD pipeline executions triggered by GitHub events</p>
      </div>

      {error && <div className="error-box">⚠ {error}</div>}

      <div className="input-group">
        <input
          id="run-search"
          className="search-input"
          placeholder="Search repository…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <select
          id="run-status-filter"
          className="select-input"
          value={status}
          onChange={e => { setStatus(e.target.value); setPage(1); }}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {loading ? (
        <div className="spinner-wrap"><div className="spinner" /></div>
      ) : (
        <>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Run ID</th>
                  <th>Branch</th>
                  <th>Workflow</th>
                  <th>Status</th>
                  <th>Error Type</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data?.items?.length === 0 && (
                  <tr>
                    <td colSpan={8}>
                      <div className="empty-state">
                        <div className="empty-icon">🔍</div>
                        <div className="empty-text">No pipeline runs found</div>
                      </div>
                    </td>
                  </tr>
                )}
                {data?.items?.map(run => (
                  <tr key={run.run_id}>
                    <td>
                      <Link className="row-link" to={`/runs/${run.run_id}`}>
                        {run.repo_name}
                      </Link>
                    </td>
                    <td className="mono">#{run.run_id}</td>
                    <td style={{ color: 'var(--clr-accent-2)', fontSize: '0.8rem' }}>
                      {run.branch || '—'}
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{run.workflow_name || '—'}</td>
                    <td><StatusBadge status={run.status} /></td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--clr-danger)' }}>
                      {run.error_type || '—'}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>{formatDate(run.created_at)}</td>
                    <td>
                      {run.run_url && (
                        <a href={run.run_url} target="_blank" rel="noreferrer" className="ext-link">
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="pagination">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                ← Prev
              </button>
              {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                .filter(p => Math.abs(p - page) <= 2)
                .map(p => (
                  <button
                    key={p}
                    className={`page-btn${p === page ? ' active' : ''}`}
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                ))}
              <button className="page-btn" disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>
                Next →
              </button>
            </div>
          )}

          <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--clr-muted-2)', marginTop: 8 }}>
            {data?.total ?? 0} total runs
          </p>
        </>
      )}
    </div>
  );
}
