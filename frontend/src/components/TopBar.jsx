import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

const PAGE_META = {
  '/':         { title: 'Command Center',  subtitle: 'Live grid overview — all feeders, risk zones & active alerts' },
  '/forecast': { title: 'Demand Forecast', subtitle: '24-hour XGBoost + SHAP forecast with confidence intervals' },
  '/alerts':   { title: 'Anomaly Alerts',  subtitle: 'Multi-layer anomaly detection — active alerts & review queue' },
  '/map':      { title: 'Feeder Map',      subtitle: 'Geographic view of Bengaluru distribution grid' },
  '/audit':    { title: 'Audit Log',       subtitle: 'Immutable KERC-compliant decision & action history' },
};

export default function TopBar() {
  const location = useLocation();
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const meta = PAGE_META[location.pathname] || PAGE_META['/'];

  const timeStr = now.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
  const dateStr = now.toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="topbar-title">{meta.title}</span>
        <span className="topbar-subtitle">{meta.subtitle}</span>
      </div>

      <div className="topbar-right">
        <div className="topbar-meta">
          <span className="topbar-meta-dot" />
          <span>Live · {dateStr} {timeStr}</span>
        </div>
        <div className="model-badge">XGBoost v2</div>
        <div className="model-badge" style={{ background: 'var(--color-green-dim)', color: 'var(--color-accent-green)', borderColor: 'rgba(34,197,94,0.2)' }}>
          KERC
        </div>
      </div>
    </header>
  );
}
