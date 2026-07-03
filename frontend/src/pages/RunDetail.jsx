import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchRun } from '../api';
import StatusBadge from '../components/StatusBadge';
import { ArrowLeft, ExternalLink, Sparkles } from 'lucide-react';

function Field({ label, value, mono = false }) {
  if (!value && value !== 0) return null;
  return (
    <div className="detail-field">
      <span className="detail-label">{label}</span>
      <span className="detail-value" style={mono ? { fontFamily: 'monospace', fontSize: '0.82rem' } : {}}>
        {value}
      </span>
    </div>
  );
}

export default function RunDetail() {
  const { runId }         = useParams();
  const [run, setRun]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchRun(runId)
      .then(setRun)
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <div className="spinner-wrap"><div className="spinner" /></div>;
  if (error)   return <div className="page-container"><div className="error-box">⚠ {error}</div></div>;
  if (!run)    return null;

  return (
    <div className="page-container">
      <div className="page-header">
        <Link to="/runs" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--clr-muted)', fontSize: '0.8rem', textDecoration: 'none', marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to Runs
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <h2 className="page-title" style={{ fontSize: '1.4rem' }}>
            Run #{run.run_id}
          </h2>
          <StatusBadge status={run.status} />
          {run.is_flaky && (
            <span className="badge flaky">
              <span className="badge-dot" />
              Flaky
            </span>
          )}
        </div>
        <p className="page-subtitle">{run.repo_name}</p>
      </div>

      {/* LLM Summary */}
      {run.llm_summary && (
        <div className="llm-summary-card">
          <div className="llm-summary-label">
            <Sparkles size={12} /> AI Incident Summary
          </div>
          <p className="llm-summary-text">{run.llm_summary}</p>
        </div>
      )}

      {/* Core Details */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">Run Details</div>
        <div className="detail-grid">
          <Field label="Repository"    value={run.repo_name} />
          <Field label="Workflow"      value={run.workflow_name} />
          <Field label="Branch"        value={run.branch} />
          <Field label="Commit SHA"    value={run.commit_sha} mono />
          <Field label="Status"        value={run.status} />
          <Field label="Created"       value={new Date(run.created_at).toLocaleString()} />
          <Field label="Updated"       value={new Date(run.updated_at).toLocaleString()} />
        </div>
        {run.run_url && (
          <a href={run.run_url} target="_blank" rel="noreferrer" className="ext-link" style={{ marginTop: 16, display: 'inline-flex' }}>
            <ExternalLink size={13} /> View on GitHub Actions
          </a>
        )}
      </div>

      {/* Error Details */}
      {run.error_type && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ color: 'var(--clr-danger)' }}>⚡ Error Details</div>
          <div className="detail-grid" style={{ marginBottom: 16 }}>
            <Field label="Error Type"    value={run.error_type} />
            <Field label="Language"      value={run.error_language} />
            <Field label="File"          value={run.error_filename} mono />
            <Field label="Line Number"   value={run.error_line_number} />
            <Field label="Step Log File" value={run.step_log_file} mono />
          </div>
          {run.error_message && (
            <div style={{ marginBottom: 16 }}>
              <div className="detail-label" style={{ marginBottom: 6 }}>Error Message</div>
              <div className="code-block">{run.error_message}</div>
            </div>
          )}
          {run.error_traceback && (
            <div>
              <div className="detail-label" style={{ marginBottom: 6 }}>Traceback</div>
              <div className="code-block">{run.error_traceback}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
