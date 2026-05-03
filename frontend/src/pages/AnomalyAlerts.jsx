import { useState, useEffect, useCallback } from 'react';
import RiskBadge from '../components/RiskBadge';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip
} from 'recharts';

const API = 'http://localhost:8000/api';

function ScoreBadge({ score }) {
  const cls = score >= 80 ? 'score-critical' : score >= 60 ? 'score-high' : 'score-low';
  return <span className={`score-badge ${cls}`}>{score}</span>;
}

function AlertDetailModal({ alert, onClose }) {
  const [loading, setLoading]  = useState(false);
  const [detail, setDetail]    = useState(null);
  const [actionDone, setActionDone] = useState('');

  useEffect(() => {
    if (!alert) return;
    setLoading(true);
    fetch(`${API}/anomalies/${alert.anomaly_id}`)
      .then(r => r.json())
      .then(setDetail)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [alert]);

  const postAction = async (action) => {
    await fetch(`${API}/anomalies/${alert.anomaly_id}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, analyst_id: 'operator_01', notes: `Action: ${action}` }),
    });
    setActionDone(action);
  };

  if (!alert) return null;
  const d = detail || alert;

  const radarData = d.risk_components ? [
    { subject: 'Statistical', value: d.risk_components.statistical_severity * 100 / 40 },
    { subject: 'Pattern',     value: d.risk_components.pattern_consistency * 100 / 30 },
    { subject: 'Peer',        value: d.risk_components.peer_comparison * 100 / 20 },
    { subject: 'Risk Profile',value: d.risk_components.consumer_risk_profile * 100 / 10 },
  ] : [];

  const tsData = d.evidence_values?.map((v, i) => ({
    t: i,
    value: v,
    ref: d.reference_values?.[i] ?? null,
  })) || [];

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(6,11,24,0.82)',
      backdropFilter: 'blur(6px)', zIndex: 200,
      display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
      padding: '40px 24px', overflowY: 'auto',
    }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="glass-card anim-slide-right" style={{
        width: '100%', maxWidth: 720,
        border: `1px solid ${d.risk_level === 'CRITICAL' ? 'rgba(239,68,68,0.3)' : 'var(--color-border-bright)'}`,
      }}>
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <ScoreBadge score={d.risk_score} />
              <RiskBadge level={d.risk_level} />
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>{d.anomaly_type}</div>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
              Meter {d.meter_id} · Feeder {d.feeder_id} · {d.days_active} day(s) active
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose} style={{ fontSize: 16 }}>✕</button>
        </div>

        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /><span>Loading detail…</span></div>
        ) : (
          <div style={{ padding: '20px 24px' }}>
            {/* Detection trigger */}
            <div className="glass-card" style={{ padding: '14px 16px', marginBottom: 16, borderLeft: '3px solid var(--color-accent-amber)' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-accent-amber)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>Detection Trigger</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{d.detection_trigger || d.rule_triggered || 'Multi-layer ensemble detection'}</div>
            </div>

            {/* Evidence + Peer */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div className="glass-card" style={{ padding: '14px 16px' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 }}>Key Evidence</div>
                {d.key_evidence?.map((ev, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 4, display: 'flex', gap: 6 }}>
                    <span style={{ color: 'var(--color-accent-red)' }}>▸</span>{ev}
                  </div>
                )) || <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Anomalous consumption pattern detected</div>}
              </div>

              <div className="glass-card" style={{ padding: '14px 16px' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 }}>Peer Comparison</div>
                {d.peer_comparison?.map((p, i) => (
                  <div key={i} className="stat-row">
                    <span className="stat-key">{p.meter_id}</span>
                    <span className="stat-val">{p.value?.toFixed(2)} kWh avg</span>
                  </div>
                )) || <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Peer data loading…</div>}
              </div>
            </div>

            {/* Charts row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              {/* Time series evidence */}
              {tsData.length > 0 && (
                <div className="glass-card" style={{ padding: '14px 16px' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 }}>Anomalous Period</div>
                  <ResponsiveContainer width="100%" height={120}>
                    <AreaChart data={tsData}>
                      <defs>
                        <linearGradient id="tsGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="value" stroke="#ef4444" fill="url(#tsGrad)" strokeWidth={1.5} dot={false} name="Meter" />
                      <Area type="monotone" dataKey="ref" stroke="#3b82f6" fill="none" strokeWidth={1} strokeDasharray="3 2" dot={false} name="Reference" />
                      <XAxis hide /><YAxis hide />
                      <Tooltip contentStyle={{ background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', fontSize: 11 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Radar risk breakdown */}
              {radarData.length > 0 && (
                <div className="glass-card" style={{ padding: '14px 16px' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>Risk Score Breakdown</div>
                  <ResponsiveContainer width="100%" height={140}>
                    <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                      <PolarGrid stroke="rgba(255,255,255,0.08)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--color-text-muted)', fontSize: 9 }} />
                      <Radar name="Risk" dataKey="value" stroke="#ef4444" fill="#ef4444" fillOpacity={0.2} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Recommended action */}
            <div className="glass-card" style={{ padding: '14px 16px', marginBottom: 20, borderLeft: '3px solid var(--color-accent-blue)' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-accent-blue)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>Recommended Action</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{d.recommended_action}</div>
            </div>

            {/* Action buttons */}
            {actionDone ? (
              <div style={{ padding: '12px 16px', background: 'var(--color-green-dim)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--color-accent-green)', fontWeight: 600, textAlign: 'center' }}>
                ✓ Action logged: {actionDone} — added to audit trail
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-success" style={{ flex: 1 }} onClick={() => postAction('CONFIRM')}>✅ Confirm Alert</button>
                <button className="btn btn-danger"  style={{ flex: 1 }} onClick={() => postAction('DISMISS')}>✗ Dismiss</button>
                <button className="btn btn-warning" style={{ flex: 1 }} onClick={() => postAction('ESCALATE')}>⬆ Escalate</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnomalyAlerts() {
  const [tab, setTab]     = useState('active');
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [sortKey, setSortKey]   = useState('risk_score');
  const [sortDir, setSortDir]   = useState(-1);

  const fetchAlerts = useCallback(async () => {
    try {
      const res  = await fetch(`${API}/anomalies?limit=100`);
      const data = await res.json();
      setAlerts(data.anomalies || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const filtered = alerts.filter(a => {
    if (tab === 'active')  return a.risk_score >= 60 && a.status !== 'CLOSED';
    if (tab === 'review')  return a.risk_score < 60 && a.status !== 'CLOSED';
    if (tab === 'closed')  return a.status === 'CLOSED';
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    return typeof av === 'number' ? (bv - av) * sortDir : av.localeCompare(bv) * sortDir;
  });

  const sort = (key) => {
    if (sortKey === key) setSortDir(d => -d);
    else { setSortKey(key); setSortDir(-1); }
  };

  const sortIcon = (key) => sortKey === key ? (sortDir === -1 ? ' ↓' : ' ↑') : '';

  return (
    <div className="page-container anim-fade-in">
      {/* Tabs + Summary */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div className="tab-bar">
          {[
            { id: 'active', label: `Active (${alerts.filter(a => a.risk_score >= 60 && a.status !== 'CLOSED').length})` },
            { id: 'review', label: `Review Queue (${alerts.filter(a => a.risk_score < 60 && a.status !== 'CLOSED').length})` },
            { id: 'closed', label: `Closed (${alerts.filter(a => a.status === 'CLOSED').length})` },
          ].map(t => (
            <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
          {sorted.length} alert{sorted.length !== 1 ? 's' : ''} shown
        </div>
      </div>

      {/* Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /><span>Loading alerts…</span></div>
        ) : sorted.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">✅</span>
            <span className="empty-state-text">No alerts in this category</span>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => sort('risk_score')}>Score{sortIcon('risk_score')}</th>
                  <th onClick={() => sort('risk_level')}>Risk{sortIcon('risk_level')}</th>
                  <th onClick={() => sort('anomaly_type')}>Type{sortIcon('anomaly_type')}</th>
                  <th onClick={() => sort('feeder_id')}>Feeder{sortIcon('feeder_id')}</th>
                  <th onClick={() => sort('meter_id')}>Meter ID{sortIcon('meter_id')}</th>
                  <th onClick={() => sort('days_active')}>Days Active{sortIcon('days_active')}</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(alert => (
                  <tr key={alert.anomaly_id} onClick={() => setSelected(alert)}>
                    <td><ScoreBadge score={alert.risk_score} /></td>
                    <td><RiskBadge level={alert.risk_level} /></td>
                    <td style={{ maxWidth: 200 }}>{alert.anomaly_type}</td>
                    <td><code style={{ background: 'var(--color-glass)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>{alert.feeder_id}</code></td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{alert.meter_id}</td>
                    <td style={{ color: alert.days_active > 5 ? 'var(--color-accent-red)' : 'var(--color-text-secondary)' }}>
                      {alert.days_active}d
                    </td>
                    <td>
                      <span style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
                        background: 'var(--color-glass)', color: 'var(--color-text-muted)',
                        textTransform: 'uppercase', letterSpacing: 0.5,
                      }}>
                        {alert.status || 'OPEN'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-ghost" style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={e => { e.stopPropagation(); setSelected(alert); }}>
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selected && (
        <AlertDetailModal alert={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
