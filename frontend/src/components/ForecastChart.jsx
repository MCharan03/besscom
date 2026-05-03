import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip-box">
      <div className="tooltip-label">{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 4 }}>
          <span style={{ color: p.color, fontSize: 11 }}>{p.name}</span>
          <span style={{ color: 'var(--color-text-primary)', fontWeight: 700, fontSize: 12 }}>
            {typeof p.value === 'number' ? p.value.toFixed(2) : p.value} kWh
          </span>
        </div>
      ))}
    </div>
  );
};

export default function ForecastChart({ data, showBaseline = false }) {
  if (!data || !data.timestamps) {
    return <div className="spinner-wrap"><div className="spinner" /><span>Loading forecast…</span></div>;
  }

  const chartData = data.timestamps.map((ts, i) => ({
    time: new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }),
    actual:    data.actuals?.[i] ?? null,
    forecast:  data.forecasts?.[i] ?? null,
    ci80_upper: data.ci_80_upper?.[i] ?? null,
    ci80_lower: data.ci_80_lower?.[i] ?? null,
    ci95_upper: data.ci_95_upper?.[i] ?? null,
    ci95_lower: data.ci_95_lower?.[i] ?? null,
    baseline:  data.baseline?.[i] ?? null,
  }));

  // Only tick every 4th label
  const tickFormatter = (val, idx) => idx % 4 === 0 ? val : '';

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={chartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="gradActual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradForecast" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#a78bfa" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradCI95" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.06} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey="time"
          tick={{ fill: 'var(--color-text-faint)', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={tickFormatter}
        />
        <YAxis
          tick={{ fill: 'var(--color-text-faint)', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          width={48}
          tickFormatter={(v) => v.toFixed(0)}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: 'var(--color-text-muted)', paddingTop: 12 }}
        />

        {/* 95% CI band */}
        <Area
          type="monotone" dataKey="ci95_upper" name="95% CI Upper"
          stroke="none" fill="url(#gradCI95)" dot={false} legendType="none"
        />
        <Area
          type="monotone" dataKey="ci95_lower" name="95% CI Lower"
          stroke="none" fill="var(--color-bg-base)" dot={false} legendType="none"
        />

        {/* 80% CI band */}
        <Area
          type="monotone" dataKey="ci80_upper" name="80% CI"
          stroke="rgba(167,139,250,0.25)" strokeWidth={1}
          fill="rgba(167,139,250,0.08)" strokeDasharray="4 2" dot={false}
        />
        <Area
          type="monotone" dataKey="ci80_lower" name="80% CI Lower"
          stroke="rgba(167,139,250,0.25)" strokeWidth={1}
          fill="var(--color-bg-base)" strokeDasharray="4 2" dot={false} legendType="none"
        />

        {showBaseline && (
          <Area
            type="monotone" dataKey="baseline" name="Naive Baseline"
            stroke="#4a5a78" strokeWidth={1} fill="none"
            strokeDasharray="6 3" dot={false}
          />
        )}

        {/* Actual */}
        <Area
          type="monotone" dataKey="actual" name="Actual"
          stroke="#3b82f6" strokeWidth={2}
          fill="url(#gradActual)" dot={false} activeDot={{ r: 4 }}
        />
        {/* Forecast */}
        <Area
          type="monotone" dataKey="forecast" name="Forecast"
          stroke="#a78bfa" strokeWidth={2} strokeDasharray="5 3"
          fill="url(#gradForecast)" dot={false} activeDot={{ r: 4 }}
        />

        <ReferenceLine
          x={chartData.find(d => d.actual !== null && chartData[chartData.indexOf(d) + 1]?.actual === null)?.time}
          stroke="rgba(255,255,255,0.2)"
          strokeDasharray="4 2"
          label={{ value: 'Now', fill: 'var(--color-text-faint)', fontSize: 10 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
