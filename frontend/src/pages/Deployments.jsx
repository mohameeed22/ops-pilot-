import React, { useState, useEffect, useCallback } from 'react';
import { fetchDeployments } from '../api';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

const statusColors = {
  pending: 'var(--clr-warning)',
  running: 'var(--clr-info)',
  success: 'var(--clr-success)',
  failed: 'var(--clr-danger)',
  rolled_back: 'var(--clr-muted)',
};

export default function Deployments({ refreshKey }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [envFilter, setEnvFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: 30 };
      if (envFilter) params.environment = envFilter;
      setData(await fetchDeployments(params));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [page, envFilter, refreshKey]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Deployments</h2>
        <p className="page-subtitle">Track deployments correlated with CI pipeline runs</p>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="input-group">
        <select className="select-input" value={envFilter} onChange={e => { setEnvFilter(e.target.value); setPage(1); }}>
          <option value="">All Environments</option>
          <option value="production">Production</option>
          <option value="staging">Staging</option>
          <option value="development">Development</option>
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
                  <th>Environment</th>
                  <th>Version</th>
                  <th>Branch</th>
                  <th>Status</th>
                  <th>Deployed By</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {data?.items?.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">
                        <div className="empty-icon">📦</div>
                        <div className="empty-text">No deployments recorded yet</div>
                      </div>
                    </td>
                  </tr>
                )}
                {data?.items?.map(dep => (
                  <tr key={dep.id}>
                    <td><span className="mono">{dep.repo_name}</span></td>
                    <td>
                      <span style={{
                        textTransform: 'uppercase',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        letterSpacing: '0.5px',
                        color: 'var(--clr-accent-2)',
                      }}>
                        {dep.environment}
                      </span>
                    </td>
                    <td className="mono">{dep.version || '—'}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--clr-accent-2)' }}>{dep.branch || '—'}</td>
                    <td>
                      <span style={{
                        color: statusColors[dep.status] || 'var(--clr-muted)',
                        fontWeight: 600,
                        fontSize: '0.8rem',
                      }}>
                        {dep.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{dep.deployed_by || '—'}</td>
                    <td style={{ fontSize: '0.78rem' }}>{formatDate(dep.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.total > 30 && (
            <div className="pagination">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
              <span style={{ color: 'var(--clr-muted)', fontSize: '0.8rem' }}>Page {page}</span>
              <button className="page-btn" disabled={data.items.length < 30} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
