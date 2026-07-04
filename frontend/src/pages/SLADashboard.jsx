import React, { useState, useEffect, useCallback } from 'react';
import { fetchSLA } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react';

const COLORS = ['#34d399', '#f87171', '#fbbf24', '#60a5fa'];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(13,18,36,0.97)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: '0.78rem',
    }}>
      <p style={{ color: '#94a3b8', marginBottom: 6, fontWeight: 600 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></p>
      ))}
    </div>
  );
};

export default function SLADashboard({ refreshKey }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchSLA({ days });
      setData(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [days, refreshKey]);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="spinner-wrap"><div className="spinner" /><span>Loading SLA data…</span></div>
  );

  const pieData = data ? [
    { name: 'Passed', value: data.passed },
    { name: 'Failed', value: data.failed },
    { name: 'Flaky', value: data.flaky },
    { name: 'Pending', value: data.pending },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">SLA / MTTR</h2>
        <p className="page-subtitle">CI/CD health metrics and mean-time-to-recovery</p>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="input-group">
        <select className="select-input" value={days} onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card completed" style={{ borderTop: 'none' }}>
          <div className="stat-label"><CheckCircle size={14} /> Success Rate</div>
          <div className="stat-value">{data?.success_rate ?? 0}%</div>
          <div className="stat-sub">{data?.passed ?? 0} / {data?.total_runs ?? 0} runs passed</div>
        </div>
        <div className="stat-card failed" style={{ borderTop: 'none' }}>
          <div className="stat-label"><XCircle size={14} /> Failed</div>
          <div className="stat-value">{data?.failed ?? 0}</div>
          <div className="stat-sub">total failures</div>
        </div>
        <div className="stat-card" style={{ borderTop: '3px solid #a78bfa' }}>
          <div className="stat-label"><AlertTriangle size={14} /> Flaky</div>
          <div className="stat-value" style={{ color: '#a78bfa' }}>{data?.flaky ?? 0}</div>
          <div className="stat-sub">identified flaky tests</div>
        </div>
        <div className="stat-card" style={{ borderTop: '3px solid #63d3ff' }}>
          <div className="stat-label"><Clock size={14} /> Avg MTTR</div>
          <div className="stat-value" style={{ color: '#63d3ff' }}>{data?.avg_mttr_minutes ?? '—'}</div>
          <div className="stat-sub">minutes to recovery</div>
        </div>
      </div>

      <div className="chart-row">
        {/* Pie Chart */}
        <div className="chart-container" style={{ marginBottom: 0 }}>
          <div className="chart-title">Run Distribution</div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {pieData.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Per-repo breakdown */}
        {data?.repo_breakdown?.length > 0 && (
          <div className="chart-container" style={{ marginBottom: 0 }}>
            <div className="chart-title">Repo Success Rates</div>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.repo_breakdown} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="repo" tick={{ fill: '#94a3b8', fontSize: 10 }} tickLine={false} axisLine={false} width={120} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="success_rate" name="Success Rate" fill="#34d399" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Repo breakdown table */}
      {data?.repo_breakdown?.length > 0 && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Repository</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Flaky</th>
                <th>Success Rate</th>
              </tr>
            </thead>
            <tbody>
              {data.repo_breakdown.map(r => (
                <tr key={r.repo}>
                  <td><span className="mono">{r.repo}</span></td>
                  <td>{r.total}</td>
                  <td style={{ color: 'var(--clr-success)' }}>{r.passed}</td>
                  <td style={{ color: 'var(--clr-danger)' }}>{r.failed}</td>
                  <td style={{ color: '#a78bfa' }}>{r.flaky}</td>
                  <td>
                    <span style={{ color: r.success_rate >= 80 ? 'var(--clr-success)' : 'var(--clr-danger)', fontWeight: 600 }}>
                      {r.success_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
