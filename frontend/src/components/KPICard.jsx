export default function KPICard({ label, value, delta, color = 'blue', icon }) {
  return (
    <div className={`glass-card kpi-card ${color} anim-fade-in`}>
      {icon && <span className="kpi-icon">{icon}</span>}
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {delta && <div className="kpi-delta">{delta}</div>}
    </div>
  );
}
