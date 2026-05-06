import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import KPICard from '../components/KPICard';
import AlertCard from '../components/AlertCard';
import RiskBadge from '../components/RiskBadge';
import { useLanguage } from '../LanguageContext';

const API = 'http://localhost:8001/api';
const WS_URL = 'ws://localhost:8001/ws/alerts';

function FeederCell({ feeder, onClick, t }) {
  const riskColors = {
    CRITICAL: 'var(--color-accent-red)',
    HIGH:     'var(--color-accent-amber)',
    MEDIUM:   'var(--color-accent-blue)',
    LOW:      'var(--color-accent-green)',
    NORMAL:   'var(--color-accent-green)',
  };
  const riskBgs = {
    CRITICAL: 'rgba(239,68,68,0.08)',
    HIGH:     'rgba(245,158,11,0.08)',
    MEDIUM:   'rgba(59,130,246,0.08)',
    LOW:      'rgba(34,197,94,0.06)',
    NORMAL:   'rgba(34,197,94,0.06)',
  };
  const color = riskColors[feeder.risk_zone] || 'var(--color-text-muted)';
  const bg    = riskBgs[feeder.risk_zone]   || 'transparent';

  return (
    <div
      className="glass-card clickable anim-fade-in"
      onClick={() => onClick(feeder)}
      style={{
        padding: '14px 16px',
        borderTop: `2px solid ${color}`,
        background: bg,
        borderRadius: 'var(--radius-md)',
        transition: 'all 0.2s ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>{feeder.feeder_id}</div>
          <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>{feeder.locality}</div>
        </div>
        <RiskBadge level={feeder.risk_zone} />
      </div>
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{t('load_increase').split(' ')[0]}</span>
          <span style={{ fontSize: 11, fontWeight: 700, color }}>{feeder.load_percent?.toFixed(1)}%</span>
        </div>
        <div className="progress-bar-wrap">
          <div
            className="progress-bar-fill"
            style={{
              width: `${Math.min(feeder.load_percent || 0, 100)}%`,
              background: color,
            }}
          />
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-muted)' }}>
        <span>{feeder.active_consumers} consumers</span>
        <span>{feeder.status}</span>
      </div>
    </div>
  );
}

export default function CommandCenter() {
  const { lang, t } = useLanguage();
  const [summary, setSummary]   = useState(null);
  const [feeders, setFeeders]   = useState([]);
  const [alerts, setAlerts]     = useState([]);
  const [loading, setLoading]   = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [sentientEvent, setSentientEvent] = useState(null);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    try {
      const [sumRes, feedRes, alertRes] = await Promise.all([
        fetch(`${API}/dashboard/summary`),
        fetch(`${API}/feeders`),
        fetch(`${API}/anomalies?limit=5`),
      ]);
      const [sumData, feedData, alertData] = await Promise.all([
        sumRes.json(), feedRes.json(), alertRes.json(),
      ]);
      setSummary(sumData);
      setFeeders(feedData.feeders || []);
      setAlerts(alertData.anomalies || []);
      setLastRefresh(new Date());
    } catch (e) {
      console.error('Dashboard fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);

    // WebSocket for Live Push
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'SENTIENT_NOTIFY') {
        setSentientEvent(msg);
        // Auto-clear after 10s
        setTimeout(() => setSentientEvent(null), 15000);
      }
    };

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [fetchData]);

  if (loading) {
    return (
      <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div className="spinner-wrap"><div className="spinner" /><span>Loading grid data…</span></div>
      </div>
    );
  }

  return (
    <div className="page-container anim-fade-in">
      {/* Sentient Notification Toast */}
      {sentientEvent && (
        <div className="glass-card anim-slide-right" style={{
          position: 'fixed', bottom: 40, right: 40, zIndex: 1000,
          width: 320, padding: '16px 20px', borderLeft: '4px solid var(--color-accent-amber)',
          background: 'rgba(6,11,24,0.95)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-accent-amber)', textTransform: 'uppercase' }}>🧠 {sentientEvent.title}</div>
            <button className="btn btn-ghost" style={{ padding: 0, height: 'auto', minWidth: 0 }} onClick={() => setSentientEvent(null)}>✕</button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--color-text-primary)', lineHeight: 1.5, marginBottom: 10 }}>{sentientEvent.message}</div>
          <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{new Date(sentientEvent.timestamp).toLocaleTimeString()} · AI Engine v2.2</div>
        </div>
      )}

      {/* KPI Strip */}
      <div className="kpi-strip stagger">
        <KPICard
          label={t('active_feeders')}
          value={summary?.active_feeders ?? '—'}
          delta={`${t('total')}: ${summary?.total_feeders ?? 20}`}
          color="green"
          icon="⚡"
        />
        <KPICard
          label={t('critical_zones')}
          value={summary?.critical_risk_zones ?? '—'}
          delta={`${summary?.high_risk_zones ?? 0} ${t('high')} · ${summary?.medium_risk_zones ?? 0} ${t('medium')}`}
          color="red"
          icon="🚨"
        />
        <KPICard
          label={t('open_alerts')}
          value={summary?.open_alerts ?? '—'}
          delta={`${summary?.critical_alerts ?? 0} ${t('critical')} this session`}
          color="amber"
          icon="🔔"
        />
        <KPICard
          label={t('atc_loss')}
          value={`${(summary?.atc_loss_estimate ?? 0).toFixed(1)}%`}
          delta={`Threshold: ${summary?.atc_loss_threshold ?? 15}%`}
          color="blue"
          icon="📉"
        />
      </div>

      {/* Main content grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>

        {/* Feeder Risk Grid */}
        <div>
          <div className="section-header">
            <div>
              <div className="section-title">{t('feeder_risk_grid')}</div>
              <div className="section-sub">{feeders.length} feeders across 5 localities — click to view details</div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {t('last_refresh')} {lastRefresh.toLocaleTimeString(lang === 'kn' ? 'kn-IN' : 'en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {feeders.map((f, i) => (
              <div key={f.feeder_id} style={{ animationDelay: `${i * 30}ms` }}>
                <FeederCell
                  feeder={f}
                  t={t}
                  onClick={() => navigate(`/forecast?feeder=${f.feeder_id}`)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Live Alert Feed */}
        <div>
          <div className="section-header">
            <div>
              <div className="section-title">{t('live_alert_feed')}</div>
              <div className="section-sub">Top anomalies by risk score</div>
            </div>
            <button className="btn btn-ghost" onClick={() => navigate('/alerts')}>
              {t('view_all')} →
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {alerts.length === 0 ? (
              <div className="glass-card empty-state">
                <span className="empty-state-icon">✅</span>
                <span className="empty-state-text">{t('no_alerts')}</span>
              </div>
            ) : (
              alerts.map(alert => (
                <AlertCard
                  key={alert.anomaly_id}
                  alert={alert}
                  onClick={() => navigate('/alerts')}
                />
              ))
            )}
          </div>

          {/* System Status */}
          <div className="glass-card" style={{ padding: '14px 16px', marginTop: 16 }}>
            <div className="section-title" style={{ marginBottom: 10 }}>{t('system_status')}</div>
            <div className="stat-row">
              <span className="stat-key">{t('model_version')}</span>
              <span className="stat-val">XGBoost v2.2 · IF v1.4</span>
            </div>
            <div className="stat-row">
              <span className="stat-key">{t('kerc_audit')}</span>
              <span className="stat-val" style={{ color: 'var(--color-accent-green)' }}>{t('compliant')} ✓</span>
            </div>
            <div className="stat-row">
              <span className="stat-key">{t('uptime')}</span>
              <span className="stat-val">{summary?.uptime ?? '99.7%'}</span>
            </div>
            <div className="stat-row">
              <span className="stat-key">{t('last_ingest')}</span>
              <span className="stat-val">{summary?.last_updated ? new Date(summary.last_updated).toLocaleTimeString('en-IN') : 'Just now'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
