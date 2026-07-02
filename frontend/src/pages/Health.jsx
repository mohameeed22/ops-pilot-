import React, { useState, useEffect, useCallback } from 'react';
import { fetchHealth, fetchReady } from '../api';
import { CheckCircle, XCircle, Loader } from 'lucide-react';

const checks = [
  {
    id: 'api',
    name: 'API Service',
    description: 'FastAPI application reachable',
    emoji: '🚀',
    fn: fetchHealth,
    ok: () => true,
  },
  {
    id: 'ready',
    name: 'Database & Redis',
    description: 'Readiness probe (DB + Redis connectivity)',
    emoji: '🗄️',
    fn: fetchReady,
    ok: d => d?.status === 'ready',
  },
];

function HealthTile({ check, result, status }) {
  const tileClass =
    status === 'loading' ? 'health-tile loading' :
    status === 'ok'      ? 'health-tile ok' :
                           'health-tile error';

  return (
    <div id={`health-${check.id}`} className={tileClass}>
      <div className="health-icon">{check.emoji}</div>
      <div>
        <div className="health-name">{check.name}</div>
        <div className="health-status">{check.description}</div>
        {status === 'loading' && (
          <div style={{ marginTop: 6, color: 'var(--clr-warning)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> Checking…
          </div>
        )}
        {status === 'ok' && (
          <div style={{ marginTop: 6, color: 'var(--clr-success)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle size={12} /> Healthy
          </div>
        )}
        {status === 'error' && (
          <div style={{ marginTop: 6, color: 'var(--clr-danger)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4 }}>
            <XCircle size={12} /> {result?.error || 'Unreachable'}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Health({ refreshKey }) {
  const [results, setResults] = useState({});
  const [statuses, setStatuses] = useState({});

  const load = useCallback(async () => {
    const initStatuses = Object.fromEntries(checks.map(c => [c.id, 'loading']));
    setStatuses(initStatuses);

    for (const check of checks) {
      try {
        const data = await check.fn();
        setResults(prev  => ({ ...prev, [check.id]: data }));
        setStatuses(prev => ({ ...prev, [check.id]: check.ok(data) ? 'ok' : 'error' }));
      } catch (err) {
        setResults(prev  => ({ ...prev, [check.id]: { error: err.response?.data?.detail || err.message } }));
        setStatuses(prev => ({ ...prev, [check.id]: 'error' }));
      }
    }
  }, [refreshKey]);

  useEffect(() => { load(); }, [load]);

  const allOk = Object.values(statuses).every(s => s === 'ok');

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">System Health</h2>
        <p className="page-subtitle">Live service reachability checks</p>
      </div>

      {/* Overall status banner */}
      <div style={{
        padding: '14px 20px',
        borderRadius: 'var(--radius-md)',
        marginBottom: 28,
        background: allOk ? 'var(--clr-success-bg)' : 'var(--clr-danger-bg)',
        border: `1px solid ${allOk ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}`,
        color: allOk ? 'var(--clr-success)' : 'var(--clr-danger)',
        fontWeight: 600,
        fontSize: '0.9rem',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        {allOk ? <CheckCircle size={16} /> : <XCircle size={16} />}
        {allOk ? 'All systems operational' : 'One or more systems need attention'}
      </div>

      <div className="health-grid">
        {checks.map(check => (
          <HealthTile
            key={check.id}
            check={check}
            result={results[check.id]}
            status={statuses[check.id] || 'loading'}
          />
        ))}
      </div>

      {/* Raw response */}
      {results.api && (
        <div className="card" style={{ marginTop: 28 }}>
          <div className="card-title">API Health Response</div>
          <div className="code-block">{JSON.stringify(results.api, null, 2)}</div>
        </div>
      )}
    </div>
  );
}
