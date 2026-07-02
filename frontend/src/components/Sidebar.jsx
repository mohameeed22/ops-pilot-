import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, GitBranch, FileText, Activity, Heart,
} from 'lucide-react';

const navItems = [
  { to: '/',       label: 'Dashboard',    icon: LayoutDashboard },
  { to: '/runs',   label: 'Pipeline Runs', icon: GitBranch },
  { to: '/audit',  label: 'Audit Log',    icon: FileText },
  { to: '/health', label: 'Health',       icon: Heart },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-text">⚡ Ops-Pilot</div>
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
