import React, { useState, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar  from './components/TopBar';
import Dashboard    from './pages/Dashboard';
import PipelineRuns from './pages/PipelineRuns';
import RunDetail    from './pages/RunDetail';
import AuditLog     from './pages/AuditLog';
import Health       from './pages/Health';

export default function App() {
  const [refreshKey, setRefreshKey]     = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    setRefreshKey(k => k + 1);
    setTimeout(() => setIsRefreshing(false), 800);
  }, []);

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopBar onRefresh={handleRefresh} isRefreshing={isRefreshing} />
        <Routes>
          <Route path="/"          element={<Dashboard    refreshKey={refreshKey} />} />
          <Route path="/runs"      element={<PipelineRuns refreshKey={refreshKey} />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/audit"     element={<AuditLog    refreshKey={refreshKey} />} />
          <Route path="/health"    element={<Health      refreshKey={refreshKey} />} />
        </Routes>
      </div>
    </div>
  );
}
