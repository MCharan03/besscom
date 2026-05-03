import { NavLink, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/',         icon: '⚡', label: 'Command Center' },
  { to: '/forecast', icon: '📈', label: 'Demand Forecast' },
  { to: '/alerts',   icon: '🔔', label: 'Anomaly Alerts' },
  { to: '/map',      icon: '🗺️', label: 'Feeder Map' },
  { to: '/audit',    icon: '📋', label: 'Audit Log' },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-badge">
          <div className="sidebar-logo-icon">⚡</div>
          <div className="sidebar-logo-text">
            <span className="sidebar-logo-title">BESCOM AI</span>
            <span className="sidebar-logo-sub">Smart Meter Intelligence</span>
          </div>
        </div>
      </div>

      <div className="sidebar-section-label">Navigation</div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon, label }) => {
          const isActive = to === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(to);
          return (
            <NavLink
              key={to}
              to={to}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-nav-icon">{icon}</span>
              <span>{label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
          <span className="sidebar-status-dot" />
          <span className="sidebar-status-text">All systems operational</span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--color-text-faint)' }}>
          KERC Compliant · v2.1.0 · © 2024 BESCOM
        </div>
      </div>
    </aside>
  );
}
