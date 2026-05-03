export default function RiskBadge({ level }) {
  const levels = {
    CRITICAL: 'critical',
    HIGH:     'high',
    MEDIUM:   'medium',
    LOW:      'low',
    NORMAL:   'low',
  };
  const cls = levels[level?.toUpperCase()] || 'low';
  return (
    <span className={`risk-badge ${cls}`}>
      <span className="badge-dot" />
      {level}
    </span>
  );
}
