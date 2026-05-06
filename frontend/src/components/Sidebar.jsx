import { NavLink, useLocation } from 'react-router-dom';
import { useLanguage } from '../LanguageContext';

const NAV_ITEMS = [
  { to: '/',         icon: '⚡', key: 'command_center' },
  { to: '/forecast', icon: '📈', key: 'demand_forecast' },
  { to: '/alerts',   icon: '🔔', key: 'anomaly_alerts' },
  { to: '/map',      icon: '🗺️', key: 'feeder_map' },
  { to: '/audit',    icon: '📋', key: 'audit_log' },
];

export default function Sidebar() {
  const location = useLocation();
  const { lang, setLang, t } = useLanguage();

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

      <div className="sidebar-section-label">{lang === 'en' ? 'Navigation' : 'ನ್ಯಾವಿಗೇಷನ್'}</div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon, key }) => {
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
              <span>{t(key)}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {/* Language Toggle */}
        <div style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ fontSize: 10, color: 'var(--color-text-faint)', marginBottom: 6, textTransform: 'uppercase' }}>{t('language')}</div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => setLang('en')}
              className={`btn ${lang === 'en' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ fontSize: 9, padding: '4px 8px', flex: 1 }}
            >
              EN
            </button>
            <button
              onClick={() => setLang('kn')}
              className={`btn ${lang === 'kn' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ fontSize: 9, padding: '4px 8px', flex: 1 }}
            >
              ಕನ್ನಡ
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
          <span className="sidebar-status-dot" />
          <span className="sidebar-status-text">{lang === 'en' ? 'All systems operational' : 'ಎಲ್ಲಾ ವ್ಯವಸ್ಥೆಗಳು ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತಿವೆ'}</span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--color-text-faint)' }}>
          KERC Compliant · v2.1.0 · © 2024 BESCOM
        </div>
      </div>
    </aside>
  );
}
