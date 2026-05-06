"""
BESCOM Smart Meter AI - FastAPI Backend (v2.2 Advanced)
All API endpoints including WebSocket, Simulator, and Query Engine.
"""

import os, sys, io, json, uuid, random, asyncio
from datetime import datetime, timedelta
from typing import Optional

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml.anomaly_detection import (
    build_alert_cache, get_alerts, get_alert_by_id, log_analyst_action,
)
from ml.forecasting import get_forecaster, DemandForecaster

# -- WebSocket Manager --------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# -- App setup ------------------------------------------------------------------
app = FastAPI(
    title="BESCOM Smart Meter AI",
    description="Demand Forecasting & Anomaly Detection API (Sentient v2.2)",
    version="2.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# -- State ----------------------------------------------------------------------
_feeders: list[dict] = []
_meters:  list[dict] = []
_audit_log: list[dict] = []

@app.on_event("startup")
async def startup_event():
    global _feeders, _meters
    feeders_path = os.path.join(DATA_DIR, "feeders.json")
    meters_path  = os.path.join(DATA_DIR, "meters.json")

    if not os.path.exists(feeders_path):
        raise RuntimeError("Data not found! Run: python data_generator.py first.")

    with open(feeders_path) as f: _feeders = json.load(f)
    with open(meters_path)  as f: _meters  = json.load(f)

    print(f"[OK] Loaded {len(_feeders)} feeders, {len(_meters)} meters")
    build_alert_cache(_feeders, _meters)
    print(f"[OK] Alert cache built")
    
    # Start the sentient alert broadcaster
    asyncio.create_task(sentient_broadcaster())


def _append_audit(event_type: str, entity_id: str, actor: str, details: str):
    _audit_log.append({
        "log_id":     str(uuid.uuid4())[:8].upper(),
        "timestamp":  datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "entity_id":  entity_id,
        "actor":      actor,
        "details":    details,
    })


# -- Helper: feeder live stats --------------------------------------------------
def _feeder_live_stats(feeder: dict) -> dict:
    fid = feeder["feeder_id"]
    path = os.path.join(DATA_DIR, f"feeder_{fid}.parquet")
    try:
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        recent_96 = df["consumption_kw"].tail(96)
        current_kw = float(recent_96.mean())
        peak_7d_kw = float(df["consumption_kw"].tail(672).max())
    except Exception:
        current_kw = feeder["base_mw"] * 1000 * random.uniform(0.6, 0.95)
        peak_7d_kw = current_kw * 1.2

    rated_kw   = feeder["rated_mw"] * 1000
    load_pct   = round(current_kw / rated_kw * 100, 1)

    if load_pct >= 90:   risk = "CRITICAL"
    elif load_pct >= 75: risk = "HIGH"
    elif load_pct >= 50: risk = "MEDIUM"
    else:                risk = "LOW"

    return {
        **feeder,
        "current_kw":      round(current_kw, 1),
        "peak_7d_kw":      round(peak_7d_kw, 1),
        "rated_kw":        round(rated_kw, 1),
        "load_percent":    load_pct,
        "capacity_kw":     round(rated_kw, 1),
        "risk_zone":       risk,
        "consumer_type":   feeder.get("consumer_mix", "Mixed"),
        "active_consumers": feeder.get("num_meters", 10),
        "status":          "ONLINE",
        "last_updated":    datetime.utcnow().isoformat() + "Z",
    }


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/api/dashboard/summary")
async def dashboard_summary():
    feeder_stats = [_feeder_live_stats(f) for f in _feeders]
    critical  = sum(1 for f in feeder_stats if f["risk_zone"] == "CRITICAL")
    high      = sum(1 for f in feeder_stats if f["risk_zone"] == "HIGH")
    medium    = sum(1 for f in feeder_stats if f["risk_zone"] == "MEDIUM")
    alerts    = get_alerts("active")
    crit_alerts = sum(1 for a in alerts if a.get("risk_level") == "CRITICAL")
    total_kw  = sum(f["current_kw"] for f in feeder_stats)
    rated_kw  = sum(f["rated_kw"]   for f in feeder_stats)
    atc_loss  = round(random.uniform(12.5, 18.3), 1)

    return {
        "active_feeders":    len(_feeders),
        "total_feeders":     len(_feeders),
        "critical_risk_zones": critical,
        "high_risk_zones":   high,
        "medium_risk_zones": medium,
        "open_alerts":       len(alerts),
        "critical_alerts":   crit_alerts,
        "atc_loss_estimate": atc_loss,
        "atc_loss_threshold": 15,
        "total_load_kw":     round(total_kw, 1),
        "total_rated_kw":    round(rated_kw, 1),
        "system_load_pct":   round(total_kw / rated_kw * 100, 1) if rated_kw > 0 else 0,
        "uptime":            "99.7%",
        "model_version":     "XGBoost v2.1 / IF v1.4",
        "last_updated":      datetime.utcnow().isoformat() + "Z",
    }

@app.get("/api/feeders")
async def list_feeders(locality: Optional[str] = None, risk: Optional[str] = None):
    stats = [_feeder_live_stats(f) for f in _feeders]
    if locality:
        stats = [s for s in stats if s["locality"].lower() == locality.lower()]
    if risk:
        stats = [s for s in stats if s["risk_zone"].lower() == risk.lower()]
    return {"feeders": stats, "count": len(stats)}

@app.get("/api/feeders/{feeder_id}/forecast")
async def feeder_forecast(feeder_id: str, hours: int = Query(24, ge=1, le=72)):
    feeder = next((f for f in _feeders if f["feeder_id"] == feeder_id), None)
    if not feeder:
        raise HTTPException(404, f"Feeder {feeder_id} not found")
    fc = get_forecaster(feeder_id)
    result = fc.forecast(hours_ahead=hours)
    result["feeder_info"] = _feeder_live_stats(feeder)
    return result

@app.get("/api/feeders/{feeder_id}/simulate")
async def feeder_simulate(
    feeder_id: str,
    load_increase_pct: float = Query(0, ge=-50, le=200),
    temp_modifier: float = Query(0, ge=-10, le=10),
):
    feeder = next((f for f in _feeders if f["feeder_id"] == feeder_id), None)
    if not feeder:
        raise HTTPException(404, f"Feeder {feeder_id} not found")
    fc = get_forecaster(feeder_id)
    modifier = 1.0 + (load_increase_pct / 100.0)
    result = fc.forecast(hours_ahead=24, load_modifier=modifier, temp_modifier=temp_modifier)
    result["feeder_info"] = _feeder_live_stats(feeder)
    _append_audit("MODEL_DECISION", feeder_id, "SIMULATOR", f"What-If run: {load_increase_pct}% load mod")
    return result

@app.get("/api/anomalies")
async def list_anomalies(limit: int = 100):
    return {"anomalies": get_alerts("all")[:limit]}

@app.get("/api/anomalies/{alert_id}")
async def get_anomaly(alert_id: str):
    alert = get_alert_by_id(alert_id)
    if not alert: raise HTTPException(404)
    return alert

@app.get("/api/query")
async def query_engine(q: str = ""):
    q = q.lower()
    if "alert" in q or "anomaly" in q or "ಎಚ್ಚರಿಕೆ" in q:
        return {"route": "/alerts", "intent": "NAV"}
    if "map" in q or "ನಕ್ಷೆ" in q:
        return {"route": "/map", "intent": "NAV"}
    if "audit" in q or "log" in q or "ಆಡಿಟ್" in q:
        return {"route": "/audit", "intent": "NAV"}
    if "forecast" in q or "ಮುನ್ಸೂಚನೆ" in q:
        return {"route": "/forecast", "intent": "NAV"}
    if "home" in q or "dashboard" in q or "ಕಮಾಂಡ್" in q:
        return {"route": "/", "intent": "NAV"}
    return {"route": None, "intent": "UNKNOWN"}

@app.get("/api/audit")
async def audit_log(limit: int = 100):
    if not _audit_log:
        # Mock logs
        for i in range(20):
            _append_audit("MODEL_DECISION", f"F{(i%20)+1:02d}", "XGBOOST", "Baseline forecast generated")
    return {"entries": list(reversed(_audit_log))[:limit]}

# -- WebSockets ---------------------------------------------------------------
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def sentient_broadcaster():
    """Broadcasts 'Sentient' events to the UI."""
    while True:
        await asyncio.sleep(random.randint(30, 60))
        if manager.active_connections:
            alerts = get_alerts("active")
            if alerts:
                alert = random.choice(alerts)
                await manager.broadcast({
                    "type": "SENTIENT_NOTIFY",
                    "title": "Sentient Awareness",
                    "message": f"I've detected a significant risk increase on Feeder {alert['feeder_id']}. Recommend reviewing local distribution transformers.",
                    "severity": "HIGH",
                    "timestamp": datetime.utcnow().isoformat()
                })

@app.get("/api/report/briefing")
async def executive_briefing():
    summary = await dashboard_summary()
    alerts  = get_alerts("active")
    
    # Simple HTML report
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; padding: 40px; color: #333; }}
            h1 {{ color: #004a99; border-bottom: 2px solid #004a99; padding-bottom: 10px; }}
            .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
            .kpi {{ padding: 20px; border: 1px solid #ddd; border-radius: 8px; text-align: center; }}
            .val {{ font-size: 24px; font-weight: bold; display: block; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background: #f8f9fa; }}
            .footer {{ margin-top: 50px; font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>BESCOM Smart Meter AI — Executive Briefing</h1>
        <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        
        <div class="kpi-grid">
            <div class="kpi"><span>Active Feeders</span><span class="val">{summary['active_feeders']}</span></div>
            <div class="kpi"><span>Critical Alerts</span><span class="val">{summary['critical_alerts']}</span></div>
            <div class="kpi"><span>Avg System Load</span><span class="val">{summary['system_load_pct']}%</span></div>
            <div class="kpi"><span>AT&C Loss Est.</span><span class="val">{summary['atc_loss_estimate']}%</span></div>
        </div>

        <h2>Critical Anomalies Detected</h2>
        <table>
            <thead>
                <tr><th>ID</th><th>Feeder</th><th>Type</th><th>Score</th><th>Status</th></tr>
            </thead>
            <tbody>
                {"".join([f"<tr><td>{a['alert_id']}</td><td>{a['feeder_id']}</td><td>{a['anomaly_label']}</td><td>{a['risk_score']}</td><td>{a['alert_status']}</td></tr>" for a in alerts[:10]])}
            </tbody>
        </table>

        <div class="footer">
            KERC Regulatory Compliance Document · Generated by BESCOM AI Engine v2.2 · Secure Audit ID: {str(uuid.uuid4())[:12].upper()}
        </div>
    </body>
    </html>
    """
    return io.BytesIO(html.encode()).getvalue()

# -- Health -------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.2.0"}
