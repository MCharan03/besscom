import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tooltip-box">
      <div className="tooltip-label">{d.feature}</div>
      <div style={{ fontSize: 13, fontWeight: 700, color: d.value >= 0 ? 'var(--color-accent-red)' : 'var(--color-accent-cyan)', marginTop: 4 }}>
        {d.value >= 0 ? '+' : ''}{d.value.toFixed(4)}
      </div>
    </div>
  );
};

export default function SHAPChart({ shapData }) {
  if (!shapData?.features?.length) {
    return <div className="empty-state"><span className="empty-state-icon">📊</span><span className="empty-state-text">No SHAP data available</span></div>;
  }

  const sorted = [...shapData.features]
    .map((feature, i) => ({ feature, value: shapData.values[i] }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 8);

  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 10 }}>
        Feature contributions to forecast. <span style={{ color: 'var(--color-accent-red)' }}>Red = increases</span> · <span style={{ color: 'var(--color-accent-cyan)' }}>Teal = decreases</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 0, right: 16, bottom: 0, left: 120 }}
        >
          <XAxis
            type="number"
            tick={{ fill: 'var(--color-text-faint)', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="feature"
            tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={115}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
          <Bar dataKey="value" radius={[0, 3, 3, 0]}>
            {sorted.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.value >= 0 ? '#ef4444' : '#06b6d4'}
                fillOpacity={0.75}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
