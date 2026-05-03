import { useState } from 'react';

// Bengaluru locality coordinates for SVG map (relative to 500x400 canvas)
const LOCALITIES = [
  {
    id: 'jayanagar',
    name: 'Jayanagar',
    x: 195,
    y: 260,
    feeders: ['F01', 'F02', 'F03', 'F04'],
    type: 'Residential-heavy',
  },
  {
    id: 'shivajinagar',
    name: 'Shivajinagar',
    x: 230,
    y: 170,
    feeders: ['F05', 'F06', 'F07', 'F08'],
    type: 'Commercial-heavy',
  },
  {
    id: 'whitefield',
    name: 'Whitefield',
    x: 360,
    y: 190,
    feeders: ['F09', 'F10', 'F11', 'F12'],
    type: 'Industrial + IT',
  },
  {
    id: 'yeshwanthpur',
    name: 'Yeshwanthpur',
    x: 160,
    y: 145,
    feeders: ['F13', 'F14', 'F15', 'F16'],
    type: 'Mixed Res/Comm',
  },
  {
    id: 'koramangala',
    name: 'Koramangala',
    x: 270,
    y: 285,
    feeders: ['F17', 'F18', 'F19', 'F20'],
    type: 'Mixed + High Density',
  },
];

// Simplified Bengaluru boundary polygon (approximation for demo)
const BLR_OUTLINE = `
  M 100 80
  Q 150 50 220 60
  Q 300 40 370 80
  Q 420 130 410 200
  Q 400 270 360 320
  Q 300 370 230 360
  Q 150 350 110 290
  Q 70 240 80 170
  Q 85 120 100 80
  Z
`;

function getRiskColor(locality, feeders) {
  if (!feeders) return 'var(--color-text-faint)';
  const localFeeders = feeders.filter(f => locality.feeders.includes(f.feeder_id));
  const maxRisk = localFeeders.reduce((max, f) => {
    const riskMap = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1, NORMAL: 0 };
    return Math.max(max, riskMap[f.risk_zone] || 0);
  }, 0);
  if (maxRisk >= 4) return 'var(--color-accent-red)';
  if (maxRisk >= 3) return 'var(--color-accent-amber)';
  if (maxRisk >= 2) return 'var(--color-accent-blue)';
  return 'var(--color-accent-green)';
}

function getLocalityStats(locality, feeders) {
  if (!feeders) return { load: 'N/A', alerts: 0, risk: 'N/A' };
  const localFeeders = feeders.filter(f => locality.feeders.includes(f.feeder_id));
  const avgLoad = localFeeders.length
    ? (localFeeders.reduce((s, f) => s + (f.load_percent || 0), 0) / localFeeders.length).toFixed(1)
    : 'N/A';
  const alerts = localFeeders.filter(f => f.risk_zone === 'CRITICAL' || f.risk_zone === 'HIGH').length;
  const risks = localFeeders.map(f => f.risk_zone);
  const highestRisk = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NORMAL'].find(r => risks.includes(r)) || 'N/A';
  return { load: avgLoad, alerts, risk: highestRisk };
}

export default function FeederMap({ feeders, onLocalityClick }) {
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState(null);

  const handleClick = (loc) => {
    setSelected(loc.id === selected ? null : loc.id);
    onLocalityClick && onLocalityClick(loc);
  };

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox="60 30 400 370"
        style={{ width: '100%', maxHeight: 400, display: 'block' }}
      >
        {/* Background gradient */}
        <defs>
          <radialGradient id="mapGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0d1425" />
            <stop offset="100%" stopColor="#060b18" />
          </radialGradient>
        </defs>

        {/* Bengaluru boundary */}
        <path
          d={BLR_OUTLINE}
          fill="url(#mapGlow)"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1.5"
        />

        {/* Grid lines */}
        {[100, 150, 200, 250, 300, 350].map(y => (
          <line key={`h${y}`} x1={60} y1={y} x2={440} y2={y}
            stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
        ))}
        {[100, 150, 200, 250, 300, 350, 400].map(x => (
          <line key={`v${x}`} x1={x} y1={30} x2={x} y2={400}
            stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
        ))}

        {/* Connection lines between localities */}
        {LOCALITIES.map((a, i) =>
          LOCALITIES.slice(i + 1).map((b) => (
            <line
              key={`${a.id}-${b.id}`}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke="rgba(59,130,246,0.08)"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          ))
        )}

        {/* Localities */}
        {LOCALITIES.map(loc => {
          const color = getRiskColor(loc, feeders);
          const stats = getLocalityStats(loc, feeders);
          const isHov = hovered === loc.id;
          const isSel = selected === loc.id;
          return (
            <g
              key={loc.id}
              transform={`translate(${loc.x}, ${loc.y})`}
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHovered(loc.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => handleClick(loc)}
            >
              {/* Outer glow ring */}
              <circle
                r={isHov || isSel ? 28 : 22}
                fill={color}
                fillOpacity={isHov || isSel ? 0.12 : 0.06}
                style={{ transition: 'all 0.25s ease' }}
              />
              {/* Pulsing ring for critical */}
              {stats.risk === 'CRITICAL' && (
                <circle r={32} fill="none" stroke={color} strokeWidth="1" strokeOpacity="0.3"
                  style={{ animation: 'pulse-red 2s infinite' }}
                />
              )}
              {/* Main circle */}
              <circle
                r={isHov || isSel ? 18 : 14}
                fill={`${color}22`}
                stroke={color}
                strokeWidth={isSel ? 2.5 : 1.5}
                style={{ transition: 'all 0.25s ease' }}
              />
              {/* Inner dot */}
              <circle r={5} fill={color} fillOpacity={0.9} />

              {/* Label */}
              <text
                dy={isHov ? -26 : -22}
                textAnchor="middle"
                fontSize={9}
                fill="var(--color-text-primary)"
                fontFamily="Inter, sans-serif"
                fontWeight="600"
                style={{ transition: 'all 0.25s ease' }}
              >
                {loc.name}
              </text>

              {/* Feeder count label */}
              <text
                dy={isHov ? -14 : -11}
                textAnchor="middle"
                fontSize={7}
                fill="var(--color-text-muted)"
                fontFamily="Inter, sans-serif"
              >
                {loc.feeders.length} feeders · {stats.load}% avg
              </text>

              {/* Alert count badge */}
              {stats.alerts > 0 && (
                <g transform="translate(12, -14)">
                  <circle r={7} fill="var(--color-accent-red)" />
                  <text textAnchor="middle" dy={4} fontSize={8} fill="white" fontWeight="700"
                    fontFamily="Inter, sans-serif">
                    {stats.alerts}
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* Legend */}
        <g transform="translate(65, 35)">
          {[
            { color: 'var(--color-accent-red)',   label: 'Critical' },
            { color: 'var(--color-accent-amber)', label: 'High' },
            { color: 'var(--color-accent-blue)',  label: 'Medium' },
            { color: 'var(--color-accent-green)', label: 'Normal' },
          ].map(({ color, label }, i) => (
            <g key={label} transform={`translate(0, ${i * 16})`}>
              <circle cx={5} cy={5} r={4} fill={color} fillOpacity={0.8} />
              <text x={13} y={9} fontSize={8} fill="var(--color-text-muted)" fontFamily="Inter, sans-serif">
                {label}
              </text>
            </g>
          ))}
        </g>
      </svg>

      {/* Tooltip */}
      {hovered && (() => {
        const loc = LOCALITIES.find(l => l.id === hovered);
        const stats = getLocalityStats(loc, feeders);
        const color = getRiskColor(loc, feeders);
        return (
          <div style={{
            position: 'absolute',
            top: 8, right: 8,
            background: 'var(--color-bg-elevated)',
            border: `1px solid ${color}44`,
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            minWidth: 180,
            pointerEvents: 'none',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
              {loc.name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 8 }}>{loc.type}</div>
            <div className="stat-row"><span className="stat-key">Feeders</span><span className="stat-val">{loc.feeders.length}</span></div>
            <div className="stat-row"><span className="stat-key">Avg Load</span><span className="stat-val">{stats.load}%</span></div>
            <div className="stat-row"><span className="stat-key">Risk</span><span className="stat-val" style={{ color }}>{stats.risk}</span></div>
            <div className="stat-row"><span className="stat-key">High Alerts</span><span className="stat-val">{stats.alerts}</span></div>
          </div>
        );
      })()}
    </div>
  );
}
