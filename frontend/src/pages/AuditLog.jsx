import React, { useState, useEffect, useCallback } from 'react';
import { fetchAudit } from '../api';

function formatDate(iso) {
  return iso ? new Date(iso).toLocaleString() : '—';
}

const eventColors = {
  'webhook.ping':                    'var(--clr-info)',
  'webhook.workflow_run.completed':  'var(--clr-warning)',
  'worker.task.completed':           'var(--clr-success)',
  'worker.task.failed':              'var(--clr-danger)',
  'worker.task.started':             'var(--clr-muted)',
  'worker.task.error':               'var(--clr-danger)',
};

export default function AuditLog({ refreshKey }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [page, setPage]       = useState(1);
  const [filter, setFilter]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: 50 };
      if (filter) params.event_type = filter;
      setData(await fetchAudit(params));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [page, filter, refreshKey]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Audit Log</h2>
        <p className="page-subtitle">Chronological record of all system events</p>
      </div>

      {error && <div className="error-box">⚠ {error}</div>}

      <div className="input-group">
        <input
          id="audit-filter"
          className="search-input"
          placeholder="Filter by event type (e.g. worker.task.failed)…"
          value={filter}
          onChange={e => { setFilter(e.target.value); setPage(1); }}
        />
      </div>

      {loading ? (
        <div className="spinner-wrap"><div className="spinner" /></div>
      ) : (
        <>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {data?.items?.length === 0 && (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-state">
                        <div className="empty-icon">📋</div>
                        <div className="empty-text">No audit events yet</div>
                      </div>
                    </td>
                  </tr>
                )}
                {data?.items?.map(ev => (
                  <tr key={ev.id}>
                    <td style={{ fontSize: '0.78rem', whiteSpace: 'nowrap' }}>{formatDate(ev.created_at)}</td>
                    <td>
                      <span style={{
                        fontFamily: 'monospace',
                        fontSize: '0.78rem',
                        color: eventColors[ev.event_type] || 'var(--clr-accent)',
                        padding: '2px 8px',
                        background: 'rgba(255,255,255,0.04)',
                        borderRadius: 4,
                      }}>
                        {ev.event_type}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>{ev.actor}</td>
                    <td className="mono">{ev.resource_id || '—'}</td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--clr-muted)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {ev.detail || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.total_pages > 1 && (
            <div className="pagination">
              <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span style={{ color: 'var(--clr-muted)', fontSize: '0.8rem' }}>Page {page} of {data.total_pages}</span>
              <button className="page-btn" disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          )}

          <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--clr-muted-2)', marginTop: 8 }}>
            {data?.total ?? 0} total events
          </p>
        </>
      )}
    </div>
  );
}
