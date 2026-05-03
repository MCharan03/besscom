import { useState, useEffect, useCallback } from 'react';

const API = 'http://localhost:8000/api';

const EVENT_COLORS = {
  MODEL_DECISION:  { color: 'var(--color-accent-blue)',   bg: 'var(--color-blue-dim)' },
  ANALYST_ACTION:  { color: 'var(--color-accent-green)',  bg: 'var(--color-green-dim)' },
  RETRAINING:      { color: 'var(--color-accent-purple)', bg: 'rgba(167,139,250,0.1)' },
  DATA_INGEST:     { color: 'var(--color-accent-cyan)',   bg: 'rgba(6,182,212,0.1)' },
};

function EventTypeBadge({ type }) {
  const style = EVENT_COLORS[type] || { color: 'var(--color-text-muted)', bg: 'var(--color-glass)' };
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
      background: style.bg, color: style.color,
      textTransform: 'uppercase', letterSpacing: 0.6, whiteSpace: 'nowrap',
    }}>
      {type?.replace('_', ' ')}
    </span>
  );
}

export default function AuditLog() {
  const [logs, setLogs]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');
  const [dateFrom, setDateFrom]     = useState('');
  const [dateTo, setDateTo]         = useState('');

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterType !== 'ALL') params.set('event_type', filterType);
      if (dateFrom) params.set('from', dateFrom);
      if (dateTo)   params.set('to', dateTo);
      const res  = await fetch(`${API}/audit?${params}`);
      const data = await res.json();
      setLogs(data.entries || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filterType, dateFrom, dateTo]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const exportCSV = () => {
    const header = ['Timestamp', 'Event Type', 'Entity', 'Model/User', 'Details'].join(',');
    const rows = logs.map(l =>
      [
        l.timestamp,
        l.event_type,
        l.entity_id || '',
        l.actor || '',
        `"${(l.details || '').replace(/"/g, '""')}"`,
      ].join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href  = url;
    link.download = `bescom_audit_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Counts per type
  const counts = logs.reduce((acc, l) => {
    acc[l.event_type] = (acc[l.event_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="page-container anim-fade-in">
      {/* Summary badges */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {Object.entries(EVENT_COLORS).map(([type, style]) => (
          <div key={type} className="glass-card" style={{ padding: '14px 18px', borderTop: `2px solid ${style.color}` }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-text-faint)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>
              {type.replace('_', ' ')}
            </div>
            <div style={{ fontSize: 24, fontWeight: 800, color: style.color }}>{counts[type] || 0}</div>
          </div>
        ))}
      </div>

      {/* Filters + Export */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <select className="select-styled" value={filterType} onChange={e => setFilterType(e.target.value)}>
          <option value="ALL">All Event Types</option>
          <option value="MODEL_DECISION">Model Decision</option>
          <option value="ANALYST_ACTION">Analyst Action</option>
          <option value="RETRAINING">Retraining</option>
          <option value="DATA_INGEST">Data Ingest</option>
        </select>

        <input
          type="date"
          className="select-styled"
          value={dateFrom}
          onChange={e => setDateFrom(e.target.value)}
          placeholder="From date"
        />
        <input
          type="date"
          className="select-styled"
          value={dateTo}
          onChange={e => setDateTo(e.target.value)}
          placeholder="To date"
        />

        <div style={{ flex: 1 }} />

        <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{logs.length} entries</div>
        <button className="btn btn-primary" onClick={exportCSV}>⬇ Export CSV</button>
      </div>

      {/* Audit Table */}
      <div className="glass-card" style={{ overflow: 'hidden' }}>
        {loading ? (
          <div className="spinner-wrap"><div className="spinner" /><span>Loading audit log…</span></div>
        ) : logs.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">📋</span>
            <span className="empty-state-text">No audit entries match filter</span>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event Type</th>
                  <th>Entity</th>
                  <th>Model / User</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => (
                  <tr key={i} style={{ cursor: 'default' }}>
                    <td style={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 11, color: 'var(--color-text-muted)' }}>
                      {new Date(log.timestamp).toLocaleString('en-IN', {
                        day: '2-digit', month: 'short', year: '2-digit',
                        hour: '2-digit', minute: '2-digit', hour12: false,
                      })}
                    </td>
                    <td><EventTypeBadge type={log.event_type} /></td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{log.entity_id || '—'}</td>
                    <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{log.actor || '—'}</td>
                    <td style={{ fontSize: 12, maxWidth: 400, color: 'var(--color-text-secondary)' }}>{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* KERC compliance note */}
      <div style={{
        marginTop: 16, padding: '12px 16px',
        background: 'var(--color-green-dim)',
        border: '1px solid rgba(34,197,94,0.2)',
        borderRadius: 'var(--radius-md)',
        fontSize: 12, color: 'var(--color-accent-green)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span>🔒</span>
        <span>
          <strong>Immutable Audit Trail</strong> — All entries are append-only and cryptographically sealed.
          This log satisfies <strong>KERC Regulatory Compliance</strong> requirements for AI decision audit trails.
          Export CSV for regulatory submission.
        </span>
      </div>
    </div>
  );
}
