import React, { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar,
} from 'recharts';
import { fetchStats } from '../api';
import { GitBranch, CheckCircle, XCircle, Clock, Loader, AlertTriangle } from 'lucide-react';

const statCards = [
  { key: 'total',      label: 'Total Runs',    icon: GitBranch,   cls: 'total'      },
  { key: 'completed',  label: 'Completed',     icon: CheckCircle, cls: 'completed'  },
  { key: 'failed',     label: 'Failed',        icon: XCircle,     cls: 'failed'     },
  { key: 'pending',    label: 'Pending',       icon: Clock,       cls: 'pending'    },
  { key: 'processing', label: 'Processing',    icon: Loader,      cls: 'processing' },
  { key: 'flaky_count', label: 'Flaky Tests',  icon: AlertTriangle, cls: ''         },
  { key: 'avg_mttr_minutes', label: 'Avg MTTR', icon: Clock,      cls: ''           },
];

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
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export default function Dashboard({ refreshKey }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load, refreshKey]);

  if (loading) return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <span>Loading dashboard…</span>
    </div>
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Overview</h2>
        <p className="page-subtitle">Real-time CI/CD pipeline health across all repositories</p>
      </div>

      {error && <div className="error-box">⚠ {error}</div>}

      {/* Stat Cards */}
      <div className="stats-grid">
          {statCards.map(({ key, label, icon: Icon, cls }) => (
          <div key={key} className={`stat-card ${cls}`} style={cls === '' ? { borderTop: '3px solid ' + (key === 'flaky_count' ? '#a78bfa' : '#63d3ff') } : {}}>
            <div className="stat-label">
              <Icon size={14} />
              {label}
            </div>
            <div className="stat-value" style={cls === '' ? { color: key === 'flaky_count' ? '#a78bfa' : '#63d3ff' } : {}}>
              {key === 'avg_mttr_minutes'
                ? (stats?.avg_mttr_minutes ?? '—')
                : key === 'flaky_count'
                  ? (stats?.flaky_count ?? 0)
                  : (stats?.counts?.[key] ?? 0)}
            </div>
            <div className="stat-sub">{key === 'avg_mttr_minutes' ? 'minutes to recovery' : 'all time'}</div>
          </div>
        ))}
      </div>

      {/* Trend Area Chart */}
      {stats?.trend?.length > 0 && (
        <div className="chart-container">
          <div className="chart-title">Pipeline Runs – Last 7 Days</div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={stats.trend} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#34d399" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#34d399" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="gradFailed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f87171" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f87171" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.78rem', color: '#94a3b8' }} />
              <Area type="monotone" dataKey="completed" name="Completed" stroke="#34d399" fill="url(#gradCompleted)" strokeWidth={2} />
              <Area type="monotone" dataKey="failed"    name="Failed"    stroke="#f87171" fill="url(#gradFailed)"    strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Bottom row: top failing repos */}
      {stats?.top_failing_repos?.length > 0 && (
        <div className="chart-row">
          <div className="chart-container" style={{ marginBottom: 0 }}>
            <div className="chart-title">Top Failing Repositories</div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={stats.top_failing_repos} layout="vertical" margin={{ left: 20, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="repo" tick={{ fill: '#94a3b8', fontSize: 11 }} tickLine={false} axisLine={false} width={120} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="failures" name="Failures" fill="#f87171" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
