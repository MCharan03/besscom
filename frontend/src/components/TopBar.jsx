import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLanguage } from '../LanguageContext';

const PAGE_META = {
  '/':         { key: 'command_center',  subtitle_en: 'Live grid overview — all feeders, risk zones & active alerts', subtitle_kn: 'ಲೈವ್ ಗ್ರಿಡ್ ಅವಲೋಕನ — ಎಲ್ಲಾ ಫೀಡರ್‌ಗಳು, ಅಪಾಯದ ವಲಯಗಳು ಮತ್ತು ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು' },
  '/forecast': { key: 'demand_forecast', subtitle_en: '24-hour XGBoost + SHAP forecast with confidence intervals', subtitle_kn: 'ವಿಶ್ವಾಸಾರ್ಹ ಮಧ್ಯಂತರಗಳೊಂದಿಗೆ 24-ಗಂಟೆಗಳ XGBoost + SHAP ಮುನ್ಸೂಚನೆ' },
  '/alerts':   { key: 'anomaly_alerts',  subtitle_en: 'Multi-layer anomaly detection — active alerts & review queue', subtitle_kn: 'ಮಲ್ಟಿ-ಲೇಯರ್ ಅಸಹಜತೆ ಪತ್ತೆ — ಸಕ್ರಿಯ ಎಚ್ಚರಿಕೆಗಳು ಮತ್ತು ವಿಮರ್ಶೆ ಸರತಿ ಸಾಲು' },
  '/map':      { key: 'feeder_map',      subtitle_en: 'Geographic view of Bengaluru distribution grid', subtitle_kn: 'ಬೆಂಗಳೂರು ವಿತರಣಾ ಗ್ರಿಡ್‌ನ ಭೌಗೋಳಿಕ ನೋಟ' },
  '/audit':    { key: 'audit_log',       subtitle_en: 'Immutable KERC-compliant decision & action history', subtitle_kn: 'ಬದಲಾಗದ KERC-ಅನುಸರಣೆಯ ನಿರ್ಧಾರ ಮತ್ತು ಕ್ರಿಯೆಯ ಇತಿಹಾಸ' },
};

export default function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { lang, t } = useLanguage();
  const [now, setNow] = useState(new Date());
  const [query, setQuery] = useState('');

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      const res = await fetch(`http://localhost:8001/api/query?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (data.route) {
        navigate(data.route);
        setQuery('');
      } else {
        alert(lang === 'en' ? "I couldn't find a match for that. Try 'show alerts' or 'go to map'." : "ಅದಕ್ಕೆ ಹೊಂದಾಣಿಕೆ ಕಂಡುಬಂದಿಲ್ಲ. 'ಎಚ್ಚರಿಕೆಗಳನ್ನು ತೋರಿಸಿ' ಅಥವಾ 'ನಕ್ಷೆಗೆ ಹೋಗಿ' ಪ್ರಯತ್ನಿಸಿ.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const meta = PAGE_META[location.pathname] || PAGE_META['/'];

  const timeStr = now.toLocaleTimeString(lang === 'kn' ? 'kn-IN' : 'en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
  const dateStr = now.toLocaleDateString(lang === 'kn' ? 'kn-IN' : 'en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });

  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="topbar-title">{t(meta.key)}</span>
        <span className="topbar-subtitle">{lang === 'en' ? meta.subtitle_en : meta.subtitle_kn}</span>
      </div>

      <form className="topbar-center" onSubmit={handleQuery} style={{ flex: 1, maxWidth: 400, margin: '0 40px' }}>
        <input
          type="text"
          className="select-styled"
          style={{ width: '100%', borderRadius: 20, padding: '8px 20px', background: 'var(--color-bg-elevated)' }}
          placeholder={t('search_placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </form>

      <div className="topbar-right">
        <div className="topbar-meta">
          <span className="topbar-meta-dot" />
          <span>{lang === 'en' ? 'Live' : 'ಲೈವ್'} · {dateStr} {timeStr}</span>
        </div>
        <div className="model-badge">XGBoost v2</div>
        <div className="model-badge" style={{ background: 'var(--color-green-dim)', color: 'var(--color-accent-green)', borderColor: 'rgba(34,197,94,0.2)' }}>
          KERC
        </div>
      </div>
    </header>
  );
}
