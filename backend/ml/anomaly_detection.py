"""
BESCOM Smart Meter AI — Anomaly Detection ML Module
3-layer ensemble: Statistical baselines + ML (Isolation Forest) + Rule Engine
Composite risk scoring 0-100 per PRD spec.
"""

import os
import json
import uuid
import warnings
import numpy as np
import pandas as pd
import shap
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

SUMMER_MONTHS = {4, 5, 6}
NIGHT_HOURS   = set(range(1, 5))

ANOMALY_TYPES = {
    "sustained_drop":       "Sustained Consumption Drop",
    "night_spike":          "Night Usage Spike",
    "peer_deviation":       "Peer Deviation",
    "meter_freeze":         "Meter Freeze / Malfunction",
    "seasonal_noncompliance": "Seasonal Non-Conformity",
    "gradual_drift":        "Gradual Consumption Drift",
    "dt_mismatch":          "DT Aggregate Mismatch",
    "impossible_reading":   "Impossible Reading",
}

RECOMMENDED_ACTIONS = {
    "sustained_drop":       "Dispatch field team to inspect meter connection and bypass junction. Verify physical meter readings on-site.",
    "night_spike":          "Inspect premises between 0100–0400 hrs. Check for unauthorised commercial activity or illegal sub-metering.",
    "peer_deviation":       "Compare against adjacent meters in cluster. Audit billing records. Check for direct upstream connection.",
    "meter_freeze":         "Schedule meter replacement within 48 hours. Verify communication module and data pipeline integrity.",
    "seasonal_noncompliance": "Verify AC/cooling load register. Inspect for tampered CT ratio or bypassed measurement circuit.",
    "gradual_drift":        "Review billing trend over past 90 days. Inspect meter accuracy and potential mechanical drift.",
    "dt_mismatch":          "Initiate feeder-level upstream connection audit. Survey all meters downstream of DT for potential bypass.",
    "impossible_reading":   "Immediate meter inspection. Check for data corruption, reverse polarity, or tampered display.",
}


MODEL_FEATURE_COLS = ["y", "hour", "dow", "lag_24h", "lag_168h", "roll_7d_mean", "roll_7d_std"]


# ── Routing & Explainability ──────────────────────────────────────────────────
_routing_audit_trail: list[dict] = []


def route_alert(score: float, anomaly_id: str) -> dict:
    """
    Apply staged alert thresholds and produce routing metadata.

    Thresholds:
    - score < 60: review_queue
    - 60 <= score < 80: dashboard_alert (audit logged)
    - score >= 80: sms_escalation (audit logged + supervisor notify)
    """
    now_iso = datetime.utcnow().isoformat() + "Z"
    notify_supervisor = False

    if score < 60:
        status = "review_queue"
    elif score < 80:
        status = "dashboard_alert"
        _routing_audit_trail.append({
            "timestamp": now_iso,
            "anomaly_id": anomaly_id,
            "event_type": "dashboard_alert",
            "score": round(float(score), 2),
        })
    else:
        status = "sms_escalation"
        notify_supervisor = True
        _routing_audit_trail.append({
            "timestamp": now_iso,
            "anomaly_id": anomaly_id,
            "event_type": "sms_escalation",
            "score": round(float(score), 2),
        })

    return {
        "anomaly_id": anomaly_id,
        "score": round(float(score), 2),
        "status": status,
        "notify_supervisor": notify_supervisor,
        "timestamp": now_iso,
    }


def explain_anomaly(features: pd.DataFrame, model) -> dict:
    """
    Generate SHAP-based feature contribution explanation.

    - Uses TreeExplainer for IsolationForest.
    - Uses KernelExplainer otherwise with a 50-sample background dataset.
    """
    if features is None or features.empty:
        return {
            "top_features": [],
            "contributions": {},
            "summary": "Insufficient features available for anomaly explanation.",
        }

    X = features.copy()

    try:
        if isinstance(model, IsolationForest):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            values = np.array(shap_values)
            if values.ndim == 1:
                sample_values = values
            else:
                sample_values = values[0]
        else:
            # KernelExplainer expects a callable that returns model score/output.
            background = getattr(model, "_shap_background", None)
            if background is None or len(background) == 0:
                background = X.sample(n=min(50, len(X)), random_state=42)
            else:
                background = background.sample(n=min(50, len(background)), random_state=42)

            def _predict_fn(arr):
                pred = model.predict(arr)
                return np.array(pred).reshape(-1, 1)

            explainer = shap.KernelExplainer(_predict_fn, background.values)
            shap_values = explainer.shap_values(X.iloc[[0]].values, nsamples=100)
            values = np.array(shap_values)
            if values.ndim == 3:
                sample_values = values[0][0]
            elif values.ndim == 2:
                sample_values = values[0]
            else:
                sample_values = values

        contributions = {
            col: round(float(sample_values[i]), 4)
            for i, col in enumerate(X.columns)
        }
        ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
        top_features = [name for name, _ in ranked[:5]]

        if ranked:
            first_name, first_val = ranked[0]
            second_name, second_val = ranked[1] if len(ranked) > 1 else (None, 0.0)
            if second_name is not None:
                summary = (
                    f"High anomaly score driven by {first_name} ({first_val:.2f}) "
                    f"and {second_name} ({second_val:.2f})"
                )
            else:
                summary = f"High anomaly score driven by {first_name} ({first_val:.2f})"
        else:
            summary = "No significant SHAP contributors were identified."

        return {
            "top_features": top_features,
            "contributions": contributions,
            "summary": summary,
        }
    except Exception:
        return {
            "top_features": [],
            "contributions": {},
            "summary": "SHAP explanation unavailable for this anomaly instance.",
        }


# ── Statistical Detection ──────────────────────────────────────────────────────

def zscore_detect(series: pd.Series, window: int = 2880) -> pd.Series:
    """Z-score on 30-day rolling window. Returns |z| per interval."""
    roll_mean = series.rolling(window, min_periods=96).mean()
    roll_std  = series.rolling(window, min_periods=96).std()
    z = (series - roll_mean) / (roll_std + 1e-6)
    return z.abs()


def iqr_detect(series: pd.Series, peer_series: list[pd.Series]) -> float:
    """Compare meter against peer group IQR. Returns deviation ratio."""
    if not peer_series:
        return 0.0
    peer_means = [p.tail(96).mean() for p in peer_series]
    q1, q3 = np.percentile(peer_means, 25), np.percentile(peer_means, 75)
    iqr = q3 - q1
    meter_mean = series.tail(96).mean()
    lower_bound = q1 - 1.5 * iqr
    if meter_mean < lower_bound and iqr > 0:
        return round(float((lower_bound - meter_mean) / (iqr + 1e-6)), 2)
    return 0.0


# ── Rule Engine ────────────────────────────────────────────────────────────────

def rule_engine(meter_id: str, series: pd.Series,
                consumer_type: str, feeder_series: pd.Series | None = None,
                downstream_sum: pd.Series | None = None) -> list[dict]:
    """
    Hard-coded deterministic rules. Returns list of triggered rule objects.
    These take precedence over probabilistic ML scores.
    """
    alerts = []
    now = datetime.utcnow()

    if len(series) < 672:
        return alerts

    recent     = series.tail(672)
    median_90d = series.tail(8640).median()

    # RULE 1: Sustained drop < 5% of 90-day median for 5+ consecutive days
    if consumer_type in ("commercial", "industrial") and median_90d > 0:
        threshold = median_90d * 0.05
        recent_vals = series.tail(5 * 96)
        if len(recent_vals) >= 5 * 96 and (recent_vals < threshold).all():
            alerts.append({
                "rule": "RULE_1",
                "type": "sustained_drop",
                "severity": "CRITICAL",
                "score_contribution": 85,
                "evidence": f"Consumption <5% of 90-day median ({median_90d:.1f} kW) for 5+ days",
            })

    # RULE 2: DT aggregate mismatch > 15%
    if feeder_series is not None and downstream_sum is not None:
        tail_f = feeder_series.tail(96).mean()
        tail_d = downstream_sum.tail(96).mean()
        if tail_f > 0 and abs(tail_f - tail_d) / tail_f > 0.15:
            loss_pct = round(abs(tail_f - tail_d) / tail_f * 100, 1)
            alerts.append({
                "rule": "RULE_2",
                "type": "dt_mismatch",
                "severity": "HIGH",
                "score_contribution": 75,
                "evidence": f"DT output vs downstream sum delta = {loss_pct}%",
            })

    # RULE 3: Identical readings for 48+ consecutive intervals (meter freeze)
    recent_96 = series.tail(200)
    if len(recent_96) >= 200:
        diffs = recent_96.diff().abs()
        consecutive_zero = (diffs < 0.001).rolling(192).sum()
        if (consecutive_zero >= 192).any():
            alerts.append({
                "rule": "RULE_3",
                "type": "meter_freeze",
                "severity": "HIGH",
                "score_contribution": 80,
                "evidence": "Identical readings for 48+ consecutive 15-minute intervals",
            })

    # RULE 4: Night usage spike 0100–0400 for 3+ consecutive days
    night_mask  = series.index.hour.isin(NIGHT_HOURS)
    night_series = series[night_mask].tail(3 * 4 * 4)   # 3 days × 4 hrs × 4 intervals
    day_median  = series[~night_mask].tail(672).median()
    if len(night_series) > 0 and day_median > 0:
        night_mean = night_series.mean()
        if night_mean > day_median * 3.0:
            alerts.append({
                "rule": "RULE_4",
                "type": "night_spike",
                "severity": "MEDIUM",
                "score_contribution": 65,
                "evidence": f"Night consumption ({night_mean:.1f} kW) = {night_mean/day_median:.1f}x daytime median",
            })

    # RULE 5: No summer rise for AC-category consumer
    if consumer_type in ("residential", "mixed"):
        current_month = datetime.utcnow().month
        if current_month in SUMMER_MONTHS:
            summer_recent = series.tail(96 * 7).mean()
            non_summer_baseline = series[
                ~series.index.month.isin(SUMMER_MONTHS)
            ].tail(96 * 30).mean()
            if non_summer_baseline > 0 and summer_recent < non_summer_baseline * 0.90:
                alerts.append({
                    "rule": "RULE_5",
                    "type": "seasonal_noncompliance",
                    "severity": "MEDIUM",
                    "score_contribution": 60,
                    "evidence": f"Summer consumption ({summer_recent:.1f} kW) lower than non-summer baseline ({non_summer_baseline:.1f} kW)",
                })

    return alerts


# ── ML Detection (Isolation Forest) ───────────────────────────────────────────

def build_meter_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series})
    df["hour"]        = df.index.hour
    df["dow"]         = df.index.dayofweek
    df["lag_24h"]     = df["y"].shift(96)
    df["lag_168h"]    = df["y"].shift(672)
    df["roll_7d_mean"]= df["y"].shift(1).rolling(672).mean()
    df["roll_7d_std"] = df["y"].shift(1).rolling(672).std()
    return df.dropna()


def isolation_forest_score(series: pd.Series) -> float:
    """
    Return anomaly score 0–100 for the most recent 7-day window.
    100 = most anomalous.
    """
    feat = build_meter_features(series)
    if len(feat) < 200:
        return 0.0

    # Train on first 80% (normal behaviour)
    split = int(len(feat) * 0.8)
    X_train = feat.iloc[:split][["y", "hour", "dow", "lag_24h", "lag_168h",
                                   "roll_7d_mean", "roll_7d_std"]]
    X_test  = feat.iloc[-96:][["y", "hour", "dow", "lag_24h", "lag_168h",
                                "roll_7d_mean", "roll_7d_std"]]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train.fillna(0))
    X_test_s  = scaler.transform(X_test.fillna(0))

    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso.fit(X_train_s)

    raw_scores = iso.decision_function(X_test_s)  # more negative = more anomalous
    # Normalise to 0-100
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s == min_s:
        return 0.0
    normalised = 1 - (raw_scores - min_s) / (max_s - min_s)
    return round(float(normalised.mean() * 100), 1)


def isolation_forest_artifacts(series: pd.Series):
    """
    Build Isolation Forest score plus artifacts needed for SHAP explanations.
    Returns (score, latest_feature_row, fitted_model, background_features).
    """
    feat = build_meter_features(series)
    if len(feat) < 200:
        return 0.0, None, None, None

    split = int(len(feat) * 0.8)
    X_train = feat.iloc[:split][MODEL_FEATURE_COLS].fillna(0)
    X_test = feat.iloc[-96:][MODEL_FEATURE_COLS].fillna(0)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    X_train_scaled = pd.DataFrame(X_train_s, index=X_train.index, columns=MODEL_FEATURE_COLS)
    X_test_scaled = pd.DataFrame(X_test_s, index=X_test.index, columns=MODEL_FEATURE_COLS)

    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso.fit(X_train_scaled.values)

    # Attach background for non-tree fallback compatibility.
    iso._shap_background = X_train_scaled

    raw_scores = iso.decision_function(X_test_scaled.values)
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s == min_s:
        return 0.0, X_test_scaled.tail(1), iso, X_train_scaled

    normalised = 1 - (raw_scores - min_s) / (max_s - min_s)
    score = round(float(normalised.mean() * 100), 1)
    return score, X_test_scaled.tail(1), iso, X_train_scaled


# ── Composite Scoring ──────────────────────────────────────────────────────────

def compute_composite_score(
    stat_severity: float,      # 0-100
    pattern_consistency: float,# 0-100
    peer_deviation: float,     # 0-100
    risk_profile: float,       # 0-100
) -> int:
    score = (
        stat_severity       * 0.40 +
        pattern_consistency * 0.30 +
        peer_deviation      * 0.20 +
        risk_profile        * 0.10
    )
    return min(100, max(0, int(score)))


def get_alert_status(score: int) -> str:
    if score >= 80:  return "CRITICAL"
    if score >= 60:  return "HIGH"
    return "REVIEW"


def get_alert_color(score: int) -> str:
    if score >= 80:  return "red"
    if score >= 60:  return "amber"
    return "grey"


# ── Alert Generator ────────────────────────────────────────────────────────────

def generate_anomaly_alert(
    meter_id: str,
    feeder_id: str,
    locality: str,
    consumer_type: str,
    series: pd.Series,
    peer_series: list[pd.Series],
    historical_flags: int = 0,
) -> dict | None:
    """
    Full 3-layer anomaly detection pipeline.
    Returns alert dict or None if no anomaly found.
    """
    if len(series) < 672:
        return None

    # Layer 1: Statistical
    z_scores   = zscore_detect(series)
    z_max      = float(z_scores.tail(96).max())
    stat_sev   = min(100.0, z_max / 5.0 * 100)

    # Consistency: how many of last 7 days had z > 2
    z_7d = z_scores.tail(672)
    consistency = float((z_7d > 2.0).mean() * 100)

    # Layer 2: ML (Isolation Forest)
    iso_score, iso_features, iso_model, _ = isolation_forest_artifacts(series)

    # Layer 3: Rule engine
    rule_alerts = rule_engine(meter_id, series, consumer_type)

    # If no anomaly signal at all, skip
    if stat_sev < 20 and iso_score < 30 and not rule_alerts:
        return None

    # Peer comparison
    peer_dev_raw = iqr_detect(series, peer_series)
    peer_dev_score = min(100.0, peer_dev_raw * 50)

    # Risk profile
    risk_profile_score = min(100.0, historical_flags * 15.0 + (
        10 if consumer_type == "commercial" else 5
    ))

    # Use rule contribution if available
    if rule_alerts:
        best_rule = max(rule_alerts, key=lambda r: r["score_contribution"])
        stat_sev = max(stat_sev, float(best_rule["score_contribution"]))
        anomaly_type = best_rule["type"]
        anomaly_label = ANOMALY_TYPES[anomaly_type]
        trigger = f"Rule {best_rule['rule']}: {best_rule['evidence']}"
        severity = best_rule["severity"]
    else:
        # Determine type from statistical pattern
        recent = series.tail(96 * 7)
        median_90 = series.tail(8640).median()
        if recent.mean() < median_90 * 0.40:
            anomaly_type = "sustained_drop"
        elif iso_score > 70:
            anomaly_type = "peer_deviation"
        else:
            anomaly_type = "gradual_drift"
        anomaly_label = ANOMALY_TYPES[anomaly_type]
        trigger = f"Isolation Forest score: {iso_score}/100 | Z-score max: {z_max:.2f}"
        severity = "MEDIUM"

    # Final composite score
    comp_score = compute_composite_score(stat_sev, consistency, peer_dev_score, risk_profile_score)

    # Peer comparison data
    peer_means = [round(float(p.tail(96).mean()), 1) for p in peer_series[:3]]
    this_mean  = round(float(series.tail(96).mean()), 1)

    # Key evidence
    baseline_30d = round(float(series.tail(2880).mean()), 1)
    recent_mean  = round(float(series.tail(96).mean()), 1)
    deviation_pct = round((baseline_30d - recent_mean) / (baseline_30d + 1e-6) * 100, 1)

    # Time series evidence (last 14 days)
    evidence_series = series.tail(96 * 14)

    alert_id = str(uuid.uuid4())[:8].upper()
    routing = route_alert(comp_score, alert_id)

    alert = {
        "alert_id":      alert_id,
        "anomaly_id":    alert_id,
        "meter_id":      meter_id,
        "feeder_id":     feeder_id,
        "locality":      locality,
        "consumer_type": consumer_type,
        "anomaly_type":  anomaly_type,
        "anomaly_label": anomaly_label,
        "severity":      severity,
        "risk_score":    comp_score,
        "alert_status":  get_alert_status(comp_score),
        "alert_color":   get_alert_color(comp_score),
        "days_active":   max(1, int(consistency / 15)),
        "created_at":    (datetime.utcnow() - timedelta(days=max(1, int(consistency / 14)))).isoformat(),
        "detection_trigger": trigger,
        "key_evidence": {
            "baseline_30d_mean_kw": baseline_30d,
            "recent_24h_mean_kw":   recent_mean,
            "deviation_pct":        deviation_pct,
            "z_score_max":          round(z_max, 2),
            "isolation_forest_score": iso_score,
            "consistency_pct":      round(consistency, 1),
        },
        "peer_comparison": {
            "this_meter_kw":    this_mean,
            "peer_means_kw":    peer_means,
            "peer_avg_kw":      round(float(np.mean(peer_means)), 1) if peer_means else 0,
        },
        "score_breakdown": {
            "statistical_severity": round(stat_sev, 1),
            "pattern_consistency":  round(consistency, 1),
            "peer_deviation":       round(peer_dev_score, 1),
            "risk_profile":         round(risk_profile_score, 1),
        },
        "recommended_action": RECOMMENDED_ACTIONS.get(anomaly_type, "Inspect meter."),
        "chart_timestamps": [ts.isoformat() for ts in evidence_series.index],
        "chart_values":     [round(float(v), 2) for v in evidence_series.values],
        "chart_baseline":   baseline_30d,
        "action_log":       [],
        "route_status":    routing["status"],
        "notify_supervisor": routing["notify_supervisor"],
        "routing":         routing,
    }

    # SHAP explanation is mandatory for alerts routed to analyst/supervisor (score >= 60).
    if comp_score >= 60 and iso_features is not None and iso_model is not None:
        alert["explanation"] = explain_anomaly(iso_features, iso_model)

    return alert


# ── Batch Scanner ──────────────────────────────────────────────────────────────

_alert_cache: list[dict] = []
_cache_built = False


def build_alert_cache(feeders: list[dict], meters: list[dict]) -> list[dict]:
    """
    Scan all meters and generate anomaly alerts.
    Called once at startup; results cached in memory.
    """
    global _alert_cache, _cache_built
    if _cache_built:
        return _alert_cache

    alerts = []
    print("Building anomaly alert cache...")

    for feeder in feeders:
        fid = feeder["feeder_id"]
        feeder_meters = [m for m in meters if m["feeder_id"] == fid]

        # Load all meter series for this feeder
        try:
            df_meters = pd.read_parquet(
                os.path.join(DATA_DIR, f"meters_{fid}.parquet")
            )
            df_meters.index = pd.to_datetime(df_meters.index)
        except Exception:
            continue

        meter_series_map = {col: df_meters[col] for col in df_meters.columns}

        for meter in feeder_meters:
            mid = meter["meter_id"]
            if mid not in meter_series_map:
                continue

            series = meter_series_map[mid]
            peers  = [s for k, s in meter_series_map.items() if k != mid]

            alert = generate_anomaly_alert(
                meter_id=mid,
                feeder_id=fid,
                locality=feeder["locality"],
                consumer_type=meter["consumer_type"],
                series=series,
                peer_series=peers,
                historical_flags=np.random.randint(0, 4),
            )
            if alert:
                alerts.append(alert)

    # Sort by risk score desc
    alerts.sort(key=lambda a: a["risk_score"], reverse=True)
    _alert_cache = alerts
    _cache_built = True
    print(f"  → {len(alerts)} anomaly alerts generated")
    return alerts


def get_alerts(status: str = "all") -> list[dict]:
    return [
        a for a in _alert_cache
        if status == "all"
        or (status == "active" and a.get("route_status") in ("dashboard_alert", "sms_escalation"))
        or (status == "review" and a.get("route_status") == "review_queue")
    ]


def get_alert_by_id(alert_id: str) -> dict | None:
    return next((a for a in _alert_cache if a["alert_id"] == alert_id), None)


def log_analyst_action(alert_id: str, action: str, user_id: str) -> bool:
    alert = get_alert_by_id(alert_id)
    if not alert:
        return False
    alert["action_log"].append({
        "action":    action,
        "user_id":   user_id,
        "timestamp": datetime.utcnow().isoformat(),
    })
    if action in ("confirm", "dismiss"):
        alert["alert_status"] = "CLOSED"
    elif action == "escalate":
        alert["severity"] = "CRITICAL"
    return True
