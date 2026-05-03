import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ForecastChart from '../components/ForecastChart';
import SHAPChart from '../components/SHAPChart';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';

const API = 'http://localhost:8000/api';

const FEEDERS = Array.from({ length: 20 }, (_, i) => `F${String(i + 1).padStart(2, '0')}`);

function STLPanel({ stl }) {
  if (!stl) return null;
  const keys = ['trend', 'seasonal', 'residual'];
  const colors = ['#3b82f6', '#a78bfa', '#f59e0b'];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
      {keys.map((key, ki) => {
        const data = stl[key]?.slice(0, 96) || [];
        const chartData = data.map((v, i) => ({ i, value: v }));
        return (
          <div key={key} className="glass-card" style={{ padding: '14px 16px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'capitalize', marginBottom: 10 }}>
              {key}
            </div>
            <ResponsiveContainer width="100%" height={80}>
              <LineChart data={chartData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <Line type="monotone" dataKey="value" stroke={colors[ki]} strokeWidth={1.5} dot={false} />
                <YAxis hide />
                <XAxis hide />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}

function MetricsBadge({ label, value, unit, good }) {
  return (
    <div className="glass-card" style={{ padding: '12px 16px', textAlign: 'center' }}>
      <div style={{ fontSize: 10, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: good ? 'var(--color-accent-green)' : 'var(--color-accent-amber)' }}>
        {value}{unit}
      </div>
    </div>
  );
}

export default function DemandForecast() {
  const [searchParams] = useSearchParams();
  const [feeder, setFeeder]   = useState(searchParams.get('feeder') || 'F01');
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [showBase, setShowBase] = useState(false);

  useEffect(() => {
    setLoading(true);
    setData(null);
    fetch(`${API}/feeders/${feeder}/forecast`)
      .then(r => r.json())
      .then(d => setData(d))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [feeder]);

  const downloadPNG = () => {
    const svg = document.querySelector('.recharts-wrapper svg');
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas  = document.createElement('canvas');
    canvas.width  = svg.clientWidth * 2;
    canvas.height = svg.clientHeight * 2;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const link = document.createElement('a');
      link.download = `forecast_${feeder}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData);
  };

  return (
    <div className="page-container anim-fade-in">
      {/* Controls row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ fontSize: 12, color: 'var(--color-text-muted)', fontWeight: 600 }}>Feeder</label>
          <select
            className="select-styled"
            value={feeder}
            onChange={e => setFeeder(e.target.value)}
          >
            {FEEDERS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>

          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-text-muted)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showBase}
              onChange={e => setShowBase(e.target.checked)}
              style={{ accentColor: 'var(--color-accent-blue)' }}
            />
            Show Naive Baseline
          </label>
        </div>
        <button className="btn btn-ghost" onClick={downloadPNG}>⬇ Export PNG</button>
      </div>

      {/* Forecast Model Metrics */}
      {data?.metrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          <MetricsBadge label="MAPE" value={data.metrics.mape?.toFixed(1)} unit="%" good={data.metrics.mape < 8} />
          <MetricsBadge label="Peak Capture" value={data.metrics.peak_capture_rate?.toFixed(0)} unit="%" good={data.metrics.peak_capture_rate > 85} />
          <MetricsBadge label="Forecast Bias" value={data.metrics.forecast_bias?.toFixed(2)} unit="%" good={Math.abs(data.metrics.forecast_bias) < 2} />
          <MetricsBadge label="Risk Zone Accuracy" value={data.metrics.risk_zone_accuracy?.toFixed(0)} unit="%" good={data.metrics.risk_zone_accuracy > 85} />
        </div>
      )}

      {/* Main Forecast Chart */}
      <div className="glass-card" style={{ marginBottom: 20 }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="section-title">24-Hour Demand Forecast — {feeder}</div>
            <div className="section-sub">7-day actuals + 24-hr forecast with 80%/95% confidence bands</div>
          </div>
          {data?.feeder_info && (
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', textAlign: 'right' }}>
              <div>{data.feeder_info.locality}</div>
              <div style={{ color: 'var(--color-text-faint)', fontSize: 11 }}>{data.feeder_info.consumer_type}</div>
            </div>
          )}
        </div>
        <div className="chart-wrap">
          {loading ? (
            <div className="spinner-wrap"><div className="spinner" /><span>Running XGBoost forecast…</span></div>
          ) : (
            <ForecastChart data={data} showBaseline={showBase} />
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* STL Decomposition */}
        <div className="glass-card" style={{ padding: '16px 20px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>STL Decomposition</div>
          <div className="section-sub" style={{ marginBottom: 14 }}>Trend · Seasonal · Residual components</div>
          {loading ? (
            <div className="spinner-wrap" style={{ height: 120 }}><div className="spinner" /></div>
          ) : data?.stl ? (
            <STLPanel stl={data.stl} />
          ) : (
            <div className="empty-state"><span className="empty-state-text">No STL data</span></div>
          )}
        </div>

        {/* SHAP Waterfall */}
        <div className="glass-card" style={{ padding: '16px 20px' }}>
          <div className="section-title" style={{ marginBottom: 4 }}>SHAP Feature Attribution</div>
          <div className="section-sub" style={{ marginBottom: 14 }}>Top feature contributions to this forecast</div>
          {loading ? (
            <div className="spinner-wrap" style={{ height: 120 }}><div className="spinner" /></div>
          ) : (
            <SHAPChart shapData={data?.shap} />
          )}
        </div>
      </div>

      {/* Feeder detail stats */}
      {data?.feeder_info && (
        <div className="glass-card" style={{ padding: '16px 20px' }}>
          <div className="section-title" style={{ marginBottom: 12 }}>Feeder Details</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
            {[
              { k: 'Locality',        v: data.feeder_info.locality },
              { k: 'Consumer Type',   v: data.feeder_info.consumer_type },
              { k: 'Active Consumers',v: data.feeder_info.active_consumers },
              { k: 'Capacity (kW)',   v: data.feeder_info.capacity_kw?.toFixed(0) },
              { k: 'Risk Zone',       v: data.feeder_info.risk_zone },
            ].map(({ k, v }) => (
              <div key={k}>
                <div style={{ fontSize: 10, color: 'var(--color-text-faint)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>{k}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
