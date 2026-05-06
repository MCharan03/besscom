import { useState, useEffect } from 'react';
import FeederMap from '../components/FeederMap';
import RiskBadge from '../components/RiskBadge';

const API = 'http://localhost:8001/api';

const LOCALITY_FEEDERS = {
  jayanagar:    ['F01','F02','F03','F04'],
  shivajinagar: ['F05','F06','F07','F08'],
  whitefield:   ['F09','F10','F11','F12'],
  yeshwanthpur: ['F13','F14','F15','F16'],
  koramangala:  ['F17','F18','F19','F20'],
};

export default function FeederMapPage() {
  const [feeders, setFeeders]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [selected, setSelected]   = useState(null);
  const [panelFeeders, setPanelFeeders] = useState([]);

  useEffect(() => {
    fetch(`${API}/feeders`)
      .then(r => r.json())
      .then(d => setFeeders(d.feeders || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleLocalityClick = (locality) => {
    setSelected(locality);
    const ids = LOCALITY_FEEDERS[locality.id] || [];
    setPanelFeeders(feeders.filter(f => ids.includes(f.feeder_id)));
  };

  // Summary stats
  const critical = feeders.filter(f => f.risk_zone === 'CRITICAL').length;
  const high     = feeders.filter(f => f.risk_zone === 'HIGH').length;
  const avgLoad  = feeders.length
    ? (feeders.reduce((s, f) => s + (f.load_percent || 0), 0) / feeders.length).toFixed(1)
    : '—';

  return (
    <div className="page-container anim-fade-in">
      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Total Feeders',     value: feeders.length,  color: 'var(--color-accent-blue)' },
          { label: 'Critical Feeders',  value: critical,        color: 'var(--color-accent-red)' },
          { label: 'High Risk',         value: high,            color: 'var(--color-accent-amber)' },
          { label: 'Avg Grid Load',     value: `${avgLoad}%`,   color: 'var(--color-accent-green)' },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass-card" style={{ padding: '16px 20px', textAlign: 'center' }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-faint)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 800, color }}>{value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* Map */}
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Bengaluru Distribution Grid</div>
            <div className="section-sub">Hover to preview · Click locality to view feeders</div>
          </div>
          {loading ? (
            <div className="spinner-wrap"><div className="spinner" /><span>Loading grid map…</span></div>
          ) : (
            <FeederMap feeders={feeders} onLocalityClick={handleLocalityClick} />
          )}
        </div>

        {/* Side panel */}
        <div>
          {selected ? (
            <div className="glass-card anim-slide-right" style={{ padding: '18px 20px' }}>
              <div style={{ marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--color-border)' }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>{selected.name}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{selected.type}</div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {panelFeeders.map(f => (
                  <div key={f.feeder_id} className="glass-card" style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text-primary)' }}>{f.feeder_id}</div>
                        <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 1 }}>{f.consumer_type}</div>
                      </div>
                      <RiskBadge level={f.risk_zone} />
                    </div>
                    <div style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                        <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Load</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: f.risk_zone === 'CRITICAL' ? 'var(--color-accent-red)' : 'var(--color-text-secondary)' }}>
                          {f.load_percent?.toFixed(1)}%
                        </span>
                      </div>
                      <div className="progress-bar-wrap">
                        <div className="progress-bar-fill" style={{
                          width: `${Math.min(f.load_percent || 0, 100)}%`,
                          background: f.risk_zone === 'CRITICAL' ? 'var(--color-accent-red)' :
                            f.risk_zone === 'HIGH' ? 'var(--color-accent-amber)' : 'var(--color-accent-green)',
                        }} />
                      </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--color-text-muted)' }}>
                      <span>{f.active_consumers} consumers</span>
                      <span>{f.capacity_kw?.toFixed(0)} kW cap</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>🗺️</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 6 }}>Click a Locality</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
                Select any locality on the map to view its feeder details, load percentages, and risk status.
              </div>

              <div style={{ marginTop: 24, textAlign: 'left' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 10 }}>All Localities</div>
                {Object.keys(LOCALITY_FEEDERS).map(loc => {
                  const ids = LOCALITY_FEEDERS[loc];
                  const locFeeders = feeders.filter(f => ids.includes(f.feeder_id));
                  const maxRisk = ['CRITICAL','HIGH','MEDIUM','LOW','NORMAL'].find(r => locFeeders.some(f => f.risk_zone === r)) || 'NORMAL';
                  return (
                    <div key={loc} className="stat-row">
                      <span className="stat-key" style={{ textTransform: 'capitalize' }}>{loc.replace('nagar','nagar ').replace('thpur','thpur ')}</span>
                      <RiskBadge level={maxRisk} />
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
