import RiskBadge from './RiskBadge';

export default function AlertCard({ alert, onClick }) {
  const levelMap = {
    CRITICAL: 'critical',
    HIGH: 'high',
    MEDIUM: 'medium',
    LOW: 'low',
  };
  const cls = levelMap[alert.risk_level] || 'medium';

  return (
    <div
      className={`glass-card alert-card ${cls} clickable anim-fade-in`}
      onClick={() => onClick && onClick(alert)}
    >
      <div className="alert-card-header">
        <div>
          <div className="alert-card-title">{alert.anomaly_type}</div>
          <div className="alert-card-meta">
            Meter {alert.meter_id} · Feeder {alert.feeder_id} · {alert.days_active} day{alert.days_active !== 1 ? 's' : ''} active
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <span
            className={`score-badge ${alert.risk_score >= 80 ? 'score-critical' : alert.risk_score >= 60 ? 'score-high' : 'score-low'}`}
          >
            {alert.risk_score}
          </span>
          <RiskBadge level={alert.risk_level} />
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 6 }}>
        {alert.recommended_action?.slice(0, 110)}{alert.recommended_action?.length > 110 ? '…' : ''}
      </div>
    </div>
  );
}
