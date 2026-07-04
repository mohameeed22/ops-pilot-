import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, GitBranch, FileText, Heart,
  Bell, BarChart3, RotateCcw,
} from 'lucide-react';

const navItems = [
  { to: '/',           label: 'Dashboard',        icon: LayoutDashboard },
  { to: '/runs',       label: 'Pipeline Runs',     icon: GitBranch },
  { to: '/sla',        label: 'SLA / MTTR',        icon: BarChart3 },
  { to: '/deployments',label: 'Deployments',       icon: RotateCcw },
  { to: '/notif-rules',label: 'Notification Rules',icon: Bell },
  { to: '/audit',      label: 'Audit Log',         icon: FileText },
  { to: '/health',     label: 'Health',            icon: Heart },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-text">Ops-Pilot</div>
        <div className="sidebar-logo-sub">AI DevOps Autopilot</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-nav-item${isActive ? ' active' : ''}`
            }
          >
            <Icon className="nav-icon" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-version">v2.0.0 · mohameeed22</div>
      </div>
    </aside>
  );
}
