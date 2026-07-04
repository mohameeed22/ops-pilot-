import React, { useState, useEffect, useCallback } from 'react';
import { fetchNotifRules, createNotifRule, updateNotifRule, deleteNotifRule } from '../api';
import { Plus, Trash2, Save } from 'lucide-react';

const channelOptions = ['slack', 'discord', 'teams', 'email', 'pagerduty', 'pr_comment'];

const channelLabels = {
  slack: 'Slack',
  discord: 'Discord',
  teams: 'Teams',
  email: 'Email',
  pagerduty: 'PagerDuty',
  pr_comment: 'PR Comment',
};

export default function NotificationRules({ refreshKey }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ name: '', repo_pattern: '', branch_pattern: '', status_filter: '', channels: ['slack', 'discord'] });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRules(await fetchNotifRules());
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, [refreshKey]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.name) return;
    try {
      const rule = await createNotifRule({
        name: form.name,
        repo_pattern: form.repo_pattern || null,
        branch_pattern: form.branch_pattern || null,
        status_filter: form.status_filter || null,
        channels: form.channels.join(','),
      });
      setRules(prev => [rule, ...prev]);
      setForm({ name: '', repo_pattern: '', branch_pattern: '', status_filter: '', channels: ['slack', 'discord'] });
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleUpdate = async (rule) => {
    try {
      const updated = await updateNotifRule(rule.id, {
        name: rule.name,
        repo_pattern: rule.repo_pattern,
        branch_pattern: rule.branch_pattern,
        status_filter: rule.status_filter,
        channels: rule.channels.join(','),
        is_active: rule.is_active,
      });
      setRules(prev => prev.map(r => r.id === updated.id ? updated : r));
      setEditingId(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteNotifRule(id);
      setRules(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const toggleChannel = (channels, ch) => {
    if (channels.includes(ch)) return channels.filter(c => c !== ch);
    return [...channels, ch];
  };

  if (loading) return (
    <div className="spinner-wrap"><div className="spinner" /><span>Loading rules…</span></div>
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">Notification Rules</h2>
        <p className="page-subtitle">Route CI failure notifications to channels based on repo/branch/status</p>
      </div>

      {error && <div className="error-box">{error}</div>}

      {/* Add rule form */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">New Rule</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
          <input className="search-input" style={{ flex: '0 0 180px' }} placeholder="Rule name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          <input className="search-input" style={{ flex: '0 0 160px' }} placeholder="Repo pattern (e.g. myorg/frontend)" value={form.repo_pattern} onChange={e => setForm(f => ({ ...f, repo_pattern: e.target.value }))} />
          <input className="search-input" style={{ flex: '0 0 120px' }} placeholder="Branch regex" value={form.branch_pattern} onChange={e => setForm(f => ({ ...f, branch_pattern: e.target.value }))} />
          <select className="select-input" value={form.status_filter} onChange={e => setForm(f => ({ ...f, status_filter: e.target.value }))}>
            <option value="">All statuses</option>
            <option value="failed">Failed</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {channelOptions.map(ch => (
            <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.8rem', color: 'var(--clr-muted)', cursor: 'pointer' }}>
              <input type="checkbox" checked={form.channels.includes(ch)} onChange={() => setForm(f => ({ ...f, channels: toggleChannel(f.channels, ch) }))} />
              {channelLabels[ch]}
            </label>
          ))}
        </div>
        <button className="page-btn" onClick={handleCreate} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <Plus size={14} /> Add Rule
        </button>
      </div>

      {/* Rules list */}
      {rules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🔔</div>
          <div className="empty-text">No notification rules yet. Create one above.</div>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Repo Pattern</th>
                <th>Branch Pattern</th>
                <th>Status</th>
                <th>Channels</th>
                <th>Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id}>
                  {editingId === rule.id ? (
                    <>
                      <td><input className="search-input" value={rule.name} onChange={e => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, name: e.target.value } : r))} /></td>
                      <td><input className="search-input" value={rule.repo_pattern || ''} onChange={e => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, repo_pattern: e.target.value } : r))} /></td>
                      <td><input className="search-input" value={rule.branch_pattern || ''} onChange={e => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, branch_pattern: e.target.value } : r))} /></td>
                      <td>
                        <select className="select-input" value={rule.status_filter || ''} onChange={e => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, status_filter: e.target.value || null } : r))}>
                          <option value="">All</option>
                          <option value="failed">Failed</option>
                          <option value="completed">Completed</option>
                        </select>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {channelOptions.map(ch => (
                            <label key={ch} style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: 2, cursor: 'pointer' }}>
                              <input type="checkbox" checked={rule.channels.includes(ch)} onChange={() => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, channels: toggleChannel(r.channels, ch) } : r))} />
                              {channelLabels[ch]}
                            </label>
                          ))}
                        </div>
                      </td>
                      <td>
                        <input type="checkbox" checked={rule.is_active} onChange={e => setRules(prev => prev.map(r => r.id === rule.id ? { ...r, is_active: e.target.checked } : r))} />
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="page-btn" onClick={() => handleUpdate(rule)} style={{ padding: '4px 8px' }}><Save size={12} /></button>
                          <button className="page-btn" onClick={() => setEditingId(null)} style={{ padding: '4px 8px' }}>Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={{ fontWeight: 600 }}>{rule.name}</td>
                      <td className="mono">{rule.repo_pattern || '—'}</td>
                      <td className="mono">{rule.branch_pattern || '—'}</td>
                      <td>{rule.status_filter || 'All'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {rule.channels.map(ch => (
                            <span key={ch} className="badge" style={{
                              background: ch === 'pagerduty' ? 'var(--clr-danger-bg)' : 'var(--clr-accent-dim)',
                              color: ch === 'pagerduty' ? 'var(--clr-danger)' : 'var(--clr-accent)',
                              border: 'none',
                            }}>
                              {channelLabels[ch] || ch}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <span style={{ color: rule.is_active ? 'var(--clr-success)' : 'var(--clr-muted-2)', fontSize: '0.8rem' }}>
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="page-btn" onClick={() => setEditingId(rule.id)} style={{ padding: '4px 8px' }}>Edit</button>
                          <button className="page-btn" onClick={() => handleDelete(rule.id)} style={{ padding: '4px 8px', color: 'var(--clr-danger)' }}>
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
