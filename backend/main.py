"""
BESCOM Smart Meter AI - FastAPI Backend
All API endpoints as per PRD specification.
"""

import os, sys, io, json, uuid, random
import threading
from datetime import datetime, timedelta
from typing import Optional

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml.anomaly_detection import (
    build_alert_cache, get_alerts, get_alert_by_id, log_analyst_action, route_alert,
)
from ml.forecasting import get_forecaster, DemandForecaster

# -- App setup ------------------------------------------------------------------
app = FastAPI(
    title="BESCOM Smart Meter AI",
    description="Demand Forecasting & Anomaly Detection API",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# -- Startup: load metadata + build alert cache ---------------------------------
_feeders: list[dict] = []
_meters:  list[dict] = []
_audit_log: list[dict] = []
FP_LOG: list[dict] = []
_fp_log_lock = threading.Lock()


def log_action(anomaly_id: str, action: str, analyst_id: str):
    """Append-only, thread-safe analyst action log for false-positive metrics."""
    entry = {
        "anomaly_id": anomaly_id,
        "action": action,
        "analyst_id": analyst_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "is_false_positive": action == "dismiss",
    }
    with _fp_log_lock:
        FP_LOG.append(entry)

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

# -- GET /api/dashboard/summary -------------------------------------------------
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

    _append_audit("MODEL_DECISION", "DASHBOARD", "SYSTEM",
                  f"Dashboard summary generated — {len(feeder_stats)} feeders, {len(alerts)} active alerts")

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
        "data_freshness_min": 15,
    }


# -- GET /api/feeders -----------------------------------------------------------
@app.get("/api/feeders")
async def list_feeders(locality: Optional[str] = None, risk: Optional[str] = None):
    stats = [_feeder_live_stats(f) for f in _feeders]
    if locality:
        stats = [s for s in stats if s["locality"].lower() == locality.lower()]
    if risk:
        stats = [s for s in stats if s["risk_zone"].lower() == risk.lower()]
    return {"feeders": stats, "count": len(stats)}


# -- GET /api/feeders/{feeder_id} -----------------------------------------------
@app.get("/api/feeders/{feeder_id}")
async def get_feeder(feeder_id: str):
    feeder = next((f for f in _feeders if f["feeder_id"] == feeder_id), None)
    if not feeder:
        raise HTTPException(404, f"Feeder {feeder_id} not found")
    stats = _feeder_live_stats(feeder)
    feeder_meters = [m for m in _meters if m["feeder_id"] == feeder_id]
    stats["meters"] = feeder_meters
    stats["alerts"] = [a for a in get_alerts("all") if a["feeder_id"] == feeder_id]
    return stats


# -- GET /api/feeders/{feeder_id}/forecast --------------------------------------
@app.get("/api/feeders/{feeder_id}/forecast")
async def feeder_forecast(feeder_id: str, hours: int = Query(24, ge=1, le=72)):
    feeder = next((f for f in _feeders if f["feeder_id"] == feeder_id), None)
    if not feeder:
        raise HTTPException(404, f"Feeder {feeder_id} not found")
    try:
        fc = get_forecaster(feeder_id)
        result = fc.forecast(hours_ahead=hours)
        _append_audit("MODEL_DECISION", feeder_id, "XGBOOST_v2.1",
                      f"Forecast generated: {hours}hr ahead, peak={result['peak_forecast_kw']}kW at {result['peak_time']}")
        rated_kw = feeder["rated_mw"] * 1000
        peak_pct = round(result["peak_forecast_kw"] / rated_kw * 100, 1)
        result["feeder_info"] = _feeder_live_stats(feeder)
        result["rated_kw"]    = rated_kw
        result["peak_load_pct"] = peak_pct
        result["risk_at_peak"] = (
            "CRITICAL" if peak_pct >= 90 else
            "HIGH"     if peak_pct >= 75 else
            "MEDIUM"   if peak_pct >= 50 else "LOW"
        )
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


# -- GET /api/feeders/{feeder_id}/history ---------------------------------------
@app.get("/api/feeders/{feeder_id}/history")
async def feeder_history(feeder_id: str, days: int = Query(7, ge=1, le=90)):
    path = os.path.join(DATA_DIR, f"feeder_{feeder_id}.parquet")
    if not os.path.exists(path):
        raise HTTPException(404, f"Feeder {feeder_id} not found")
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    n = days * 96
    subset = df["consumption_kw"].tail(n)
    hourly = subset.resample("h").mean().dropna()
    return {
        "feeder_id":  feeder_id,
        "days":       days,
        "timestamps": [ts.isoformat() for ts in hourly.index],
        "values":     [round(float(v), 2) for v in hourly.values],
        "avg_kw":     round(float(hourly.mean()), 1),
        "peak_kw":    round(float(hourly.max()), 1),
        "min_kw":     round(float(hourly.min()), 1),
    }


# -- GET /api/anomalies ---------------------------------------------------------
@app.get("/api/anomalies")
async def list_anomalies(
    feeder_id: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    limit: int     = Query(100, ge=1, le=500),
):
    all_alerts = get_alerts("all")
    if feeder_id:
        all_alerts = [a for a in all_alerts if a["feeder_id"] == feeder_id]
    all_alerts = [a for a in all_alerts if a["risk_score"] >= min_score]
    all_alerts.sort(key=lambda a: a["risk_score"], reverse=True)
    return {
        "anomalies": all_alerts[:limit],
        "total":     len(all_alerts),
    }


# -- GET /api/anomalies/{alert_id} ---------------------------------------------
@app.get("/api/anomalies/{alert_id}")
async def get_anomaly(alert_id: str):
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return alert


# -- POST /api/anomalies/{alert_id}/action -------------------------------------
class ActionPayload(BaseModel):
    action:     str  # confirm | dismiss | escalate
    analyst_id: str = "ANALYST-01"
    notes:      str = ""

@app.get("/metrics/false-positive-rate")
async def get_false_positive_rate():
    with _fp_log_lock:
        logs = list(FP_LOG)

    if not logs:
        return {
            "false_positive_rate": 0.0,
            "total_flagged": 0,
            "confirmed": 0,
            "dismissed": 0,
            "escalated": 0,
            "target_fp_rate": 0.10,
            "status": "insufficient_data",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

    total_actioned = len(logs)
    confirmed = sum(1 for e in logs if e["action"] == "confirm")
    dismissed = sum(1 for e in logs if e["action"] == "dismiss")
    escalated = sum(1 for e in logs if e["action"] == "escalate")
    fp_rate = dismissed / total_actioned if total_actioned > 0 else 0.0

    return {
        "false_positive_rate": float(fp_rate),
        "total_flagged": int(total_actioned),
        "confirmed": int(confirmed),
        "dismissed": int(dismissed),
        "escalated": int(escalated),
        "target_fp_rate": 0.10,
        "status": "on_target" if fp_rate < 0.10 else "needs_review",
        "last_updated": datetime.utcnow().isoformat() + "Z",
    }

@app.post("/api/anomalies/{alert_id}/action")
@app.post("/anomalies/{alert_id}/action")
async def analyst_action(alert_id: str, payload: ActionPayload):
    action_lower = payload.action.lower()
    if action_lower not in ("confirm", "dismiss", "escalate"):
        raise HTTPException(400, "action must be: confirm | dismiss | escalate")

    # 1) Append immutable analyst action record for FP metrics.
    log_action(alert_id, action_lower, payload.analyst_id)

    success = log_analyst_action(alert_id, action_lower, payload.analyst_id)
    if not success:
        raise HTTPException(404, f"Alert {alert_id} not found")

    updated_alert = get_alert_by_id(alert_id)
    if not updated_alert:
        raise HTTPException(404, f"Alert {alert_id} not found")

    # 2) Route alert based on current risk score.
    routing = route_alert(float(updated_alert.get("risk_score", 0.0)), alert_id)
    updated_alert["route_status"] = routing["status"]
    updated_alert["notify_supervisor"] = routing["notify_supervisor"]
    updated_alert["routing"] = routing

    # 3) Add escalation audit entry when analyst escalates.
    if action_lower == "escalate":
        _append_audit("escalation", alert_id, payload.analyst_id,
                      f"Escalated anomaly by analyst | Notes: {payload.notes or 'None'}")

    _append_audit("ANALYST_ACTION", alert_id, payload.analyst_id,
                  f"Action: {payload.action.upper()} | Notes: {payload.notes or 'None'}")

    # 4) Return updated anomaly record including route_alert output.
    return {
        "status": "logged",
        "alert_id": alert_id,
        "action": payload.action,
        "route_alert": routing,
        "anomaly": updated_alert,
    }


# -- GET /api/meters -----------------------------------------------------------
@app.get("/api/meters")
async def list_meters(feeder_id: Optional[str] = None, limit: int = 100):
    meters = _meters
    if feeder_id:
        meters = [m for m in meters if m["feeder_id"] == feeder_id]
    result = []
    for m in meters[:limit]:
        last_kwh = round(m["base_kwh_day"] / 96 * random.uniform(0.5, 1.5), 2)
        result.append({**m, "last_reading_kwh": last_kwh,
                       "status": "ONLINE", "last_read": datetime.utcnow().isoformat() + "Z"})
    return {"meters": result, "count": len(result)}


# -- GET /api/audit ------------------------------------------------------------
@app.get("/api/audit")
async def audit_log(
    limit: int = Query(200, ge=1, le=2000),
    event_type: Optional[str] = None,
):
    # Add seed entries for demo if log is empty
    if not _audit_log:
        seed_types = ["MODEL_DECISION","ANALYST_ACTION","RETRAINING","DATA_INGEST"]
        for i in range(40):
            ts = datetime.utcnow() - timedelta(hours=i * 2)
            et = seed_types[i % 4]
            _audit_log.append({
                "log_id":    f"SEED{i:04d}",
                "timestamp": ts.isoformat() + "Z",
                "event_type": et,
                "entity_id": f"F{(i % 20) + 1:02d}" if "DECISION" in et else f"M{i:04d}",
                "actor":     "XGBOOST_v2.1" if "MODEL" in et else ("ANALYST-01" if "ANALYST" in et else "SYSTEM"),
                "details":   f"Seeded audit entry #{i} — {et.replace('_',' ').title()}",
            })

    logs = list(reversed(_audit_log))
    if event_type and event_type != "ALL":
        logs = [l for l in logs if l["event_type"] == event_type]
    return {"entries": logs[:limit], "total": len(_audit_log)}


# -- GET /api/recommendations --------------------------------------------------
@app.get("/api/recommendations")
async def recommendations():
    feeder_stats = [_feeder_live_stats(f) for f in _feeders]
    recs = []
    for fs in feeder_stats:
        if fs["risk_zone"] in ("CRITICAL", "HIGH"):
            pct = fs["load_percent"]
            hr  = datetime.utcnow().hour
            peak_time = f"{(hr + 2) % 24:02d}:00"
            recs.append({
                "feeder_id":   fs["feeder_id"],
                "locality":    fs["locality"],
                "risk_zone":   fs["risk_zone"],
                "load_pct":    pct,
                "recommendation": (
                    f"Feeder {fs['feeder_id']} forecast to reach {pct}% rated capacity "
                    f"at {peak_time} IST. Recommend pre-emptive load rebalancing."
                ) if pct >= 90 else (
                    f"Feeder {fs['feeder_id']} at {pct}% capacity. "
                    f"Monitor and prepare load-shedding plan if load continues rising."
                ),
                "action_by": f"{(hr + 1) % 24:02d}:00 IST",
                "priority":   1 if pct >= 90 else 2,
            })
    recs.sort(key=lambda r: r["priority"])
    return {"recommendations": recs, "count": len(recs),
            "generated_at": datetime.utcnow().isoformat() + "Z"}


# -- GET /api/localities -------------------------------------------------------
@app.get("/api/localities")
async def localities():
    feeder_stats = [_feeder_live_stats(f) for f in _feeders]
    loc_map = {}
    for fs in feeder_stats:
        loc = fs["locality"]
        if loc not in loc_map:
            loc_map[loc] = {"locality": loc, "feeders": []}
        loc_map[loc]["feeders"].append(fs)
    for loc in loc_map:
        feeders = loc_map[loc]["feeders"]
        risks   = [f["risk_zone"] for f in feeders]
        loc_map[loc]["feeder_count"]  = len(feeders)
        loc_map[loc]["max_risk"]      = (
            "CRITICAL" if "CRITICAL" in risks else
            "HIGH"     if "HIGH"     in risks else
            "MEDIUM"   if "MEDIUM"   in risks else "LOW"
        )
        loc_map[loc]["avg_load_pct"]  = round(float(np.mean([f["load_percent"] for f in feeders])), 1)
        loc_map[loc]["total_load_kw"] = round(sum(f["current_kw"] for f in feeders), 1)
    return {"localities": list(loc_map.values())}


# -- Health check -------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status":          "ok",
        "feeders_loaded":  len(_feeders),
        "meters_loaded":   len(_meters),
        "alerts_cached":   len(get_alerts("all")),
        "timestamp":       datetime.utcnow().isoformat() + "Z",
    }
