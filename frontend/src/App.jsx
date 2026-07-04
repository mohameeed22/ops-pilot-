import React, { useState, useCallback, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { getMe } from './api';
import Login from './pages/Login';
import Sidebar from './components/Sidebar';
import TopBar  from './components/TopBar';
import Dashboard    from './pages/Dashboard';
import PipelineRuns from './pages/PipelineRuns';
import RunDetail    from './pages/RunDetail';
import AuditLog     from './pages/AuditLog';
import Health       from './pages/Health';
import SLADashboard from './pages/SLADashboard';
import Deployments  from './pages/Deployments';
import NotificationRules from './pages/NotificationRules';

export default function App() {
  const [refreshKey, setRefreshKey]     = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [user, setUser]                 = useState(null);
  const [authLoading, setAuthLoading]   = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('opspilot_token');
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('opspilot_token');
        })
        .finally(() => setAuthLoading(false));
    } else {
      setAuthLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setRefreshKey(k => k + 1);
    setTimeout(() => setIsRefreshing(false), 800);
  }, []);

  if (authLoading) return <div className="spinner-wrap" style={{ height: '100vh' }}><div className="spinner" /></div>;

  if (!user) {
    return <Login onLoginSuccess={setUser} />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopBar onRefresh={handleRefresh} isRefreshing={isRefreshing} />
        <Routes>
          <Route path="/"             element={<Dashboard          refreshKey={refreshKey} />} />
          <Route path="/runs"         element={<PipelineRuns       refreshKey={refreshKey} />} />
          <Route path="/runs/:runId"  element={<RunDetail          refreshKey={refreshKey} />} />
          <Route path="/audit"        element={<AuditLog           refreshKey={refreshKey} />} />
          <Route path="/health"       element={<Health             refreshKey={refreshKey} />} />
          <Route path="/sla"          element={<SLADashboard       refreshKey={refreshKey} />} />
          <Route path="/deployments"  element={<Deployments        refreshKey={refreshKey} />} />
          <Route path="/notif-rules"  element={<NotificationRules  refreshKey={refreshKey} />} />
        </Routes>
      </div>
    </div>
  );
}
