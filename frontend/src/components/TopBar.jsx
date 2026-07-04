import React from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';

const titles = {
  '/':             'Dashboard',
  '/runs':         'Pipeline Runs',
  '/audit':        'Audit Log',
  '/health':       'System Health',
  '/sla':          'SLA / MTTR',
  '/deployments':  'Deployments',
  '/notif-rules':  'Notification Rules',
};

export default function TopBar({ onRefresh, isRefreshing }) {
  const location = useLocation();
  const base = '/' + location.pathname.split('/')[1];
  const title = titles[base] || 'Ops-Pilot';

  return (
    <header className="topbar">
      <h1 className="topbar-title">{title}</h1>
      <div className="topbar-right">
        <button
          className={`refresh-btn${isRefreshing ? ' spinning' : ''}`}
          onClick={onRefresh}
          aria-label="Refresh data"
        >
          <RefreshCw size={14} />
          {isRefreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}
