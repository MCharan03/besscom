"""
BESCOM Smart Meter AI — Synthetic Data Generator
Generates 24 months of realistic 15-minute interval meter data for
20 feeders and 200 meters across 5 Bengaluru localities.
Injects 15 anomaly signatures matching PRD taxonomy.
"""

import os
import json
import random
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

INTERVALS_PER_DAY = 96          # 15-min intervals
START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime(2025, 12, 31, 23, 45)

LOCALITIES = {
    "Jayanagar":    {"type": "residential", "base_mw": 2.0},
    "Shivajinagar": {"type": "commercial",  "base_mw": 2.8},
    "Whitefield":   {"type": "industrial",  "base_mw": 3.5},
    "Yeshwanthpur": {"type": "mixed",       "base_mw": 2.4},
    "Koramangala":  {"type": "mixed",       "base_mw": 2.6},
}

FEEDER_PER_LOCALITY = 4
METERS_PER_FEEDER   = 10

# Festival calendar (month, day)
FESTIVALS = {
    "diwali":    [(10, 20), (10, 31)],
    "ugadi":     [(3, 30), (4, 18)],
    "ganesh":    [(8, 26), (9, 15)],
    "christmas": [(12, 25)],
    "new_year":  [(1, 1), (12, 31)],
}

SUMMER_MONTHS = [4, 5, 6]
PEAK_HOURS    = range(18, 22)   # 6 PM – 10 PM
TROUGH_HOURS  = range(2, 5)     # 2 AM – 5 AM


# ── Consumer ID Masking ────────────────────────────────────────────────────────
def mask_consumer_id(meter_id: str) -> str:
    """
    Pseudonymise a meter ID using SHA-256 hashing.
    Returns format: "MTR-" followed by first 8 characters of hex digest.
    
    Args:
        meter_id: Raw meter ID string (e.g., "MTR-00001")
        
    Returns:
        Masked meter ID (e.g., "MTR-a7f8c2d5")
    """
    hash_digest = hashlib.sha256(meter_id.encode()).hexdigest()
    return f"MTR-{hash_digest[:8]}"


# ── Helpers ────────────────────────────────────────────────────────────────────
def is_festival(dt: datetime) -> bool:
    for dates in FESTIVALS.values():
        for m, d in dates:
            if dt.month == m and dt.day == d:
                return True
    return False


def hour_multiplier(hour: int, consumer_type: str) -> float:
    """Shape the intraday load curve per consumer category."""
    if consumer_type == "residential":
        if hour in PEAK_HOURS:     return 1.75
        if hour in TROUGH_HOURS:   return 0.35
        if 7 <= hour <= 9:         return 1.20
        return 0.85
    elif consumer_type == "commercial":
        if 9 <= hour <= 20:        return 1.55
        if hour in TROUGH_HOURS:   return 0.15
        return 0.50
    elif consumer_type == "industrial":
        if 8 <= hour <= 22:        return 1.40
        if hour in TROUGH_HOURS:   return 0.70
        return 1.00
    else:  # mixed
        if hour in PEAK_HOURS:     return 1.55
        if hour in TROUGH_HOURS:   return 0.30
        return 0.90


def seasonal_multiplier(dt: datetime, consumer_type: str) -> float:
    m = dt.month
    mult = 1.0
    if m in SUMMER_MONTHS and consumer_type in ("residential", "mixed", "commercial"):
        mult *= 1.40   # AC load
    if is_festival(dt):
        mult *= 1.25
    if m == 12:
        mult *= 0.90   # winter dip
    return mult


def weekly_multiplier(dt: datetime, consumer_type: str) -> float:
    dow = dt.weekday()  # 0=Mon, 6=Sun
    if consumer_type == "commercial":
        return 0.40 if dow >= 5 else 1.0
    if consumer_type == "residential":
        return 1.15 if dow >= 5 else 1.0
    return 1.0


# ── Feeder & Meter Metadata ────────────────────────────────────────────────────
def build_metadata():
    feeders, meters = [], []
    fid, mid = 0, 0
    for locality, info in LOCALITIES.items():
        for fi in range(FEEDER_PER_LOCALITY):
            fid += 1
            feeder = {
                "feeder_id":     f"FDR-{fid:03d}",
                "locality":      locality,
                "type":          info["type"],
                "base_mw":       info["base_mw"] + round(random.uniform(-0.3, 0.3), 2),
                "rated_mw":      round(info["base_mw"] * 1.3, 2),
                "meter_count":   METERS_PER_FEEDER,
            }
            feeders.append(feeder)
            for mi in range(METERS_PER_FEEDER):
                mid += 1
                raw_meter_id = f"MTR-{mid:05d}"
                masked_meter_id = mask_consumer_id(raw_meter_id)
                meters.append({
                    "meter_id":    masked_meter_id,
                    "feeder_id":   feeder["feeder_id"],
                    "locality":    locality,
                    "consumer_type": info["type"],
                    "base_kwh_day":  round(random.uniform(80, 600), 1),
                    "has_ac":       random.random() > 0.3,
                    "category":     random.choice(["residential", "commercial", "industrial"])
                                    if info["type"] == "mixed" else info["type"],
                })
    return feeders, meters


# ── Core Signal Generator ──────────────────────────────────────────────────────
def generate_meter_series(meter: dict, timestamps: pd.DatetimeIndex,
                           anomaly: dict | None = None) -> np.ndarray:
    base   = meter["base_kwh_day"] / INTERVALS_PER_DAY   # kWh per 15-min
    ct     = meter["consumer_type"]
    values = []

    for ts in timestamps:
        h_mult  = hour_multiplier(ts.hour, ct)
        s_mult  = seasonal_multiplier(ts.to_pydatetime(), ct)
        w_mult  = weekly_multiplier(ts.to_pydatetime(), ct)
        noise   = np.random.normal(1.0, 0.06)
        val     = base * h_mult * s_mult * w_mult * noise
        values.append(max(val, 0.0))

    vals = np.array(values, dtype=np.float32)

    # ── Inject anomaly ─────────────────────────────────────────────────────────
    if anomaly:
        atype = anomaly["type"]
        n     = len(vals)

        if atype == "meter_freeze":
            # 48+ consecutive identical readings in a random window
            start = random.randint(n // 3, n * 2 // 3)
            frozen_val = float(vals[start])
            vals[start:start + 200] = frozen_val   # ~50 hrs

        elif atype == "dt_mismatch":
            # Sum of downstream meters differs from DT output by >15%
            # Simulate by introducing random jumps that break aggregation consistency
            start = random.randint(n // 4, n * 3 // 4)
            end   = min(start + 7 * INTERVALS_PER_DAY, n)  # 7-day window
            vals[start:end] *= random.uniform(0.85, 1.20)  # ±15% deviation

        elif atype == "sustained_drop":
            # Consumption drops 60%+ vs 30-day baseline for 3+ days
            start = random.randint(n // 4, n * 3 // 4)
            end   = min(start + 3 * INTERVALS_PER_DAY, n)
            vals[start:end] *= 0.35  # 65% drop

        elif atype == "peer_deviation":
            # 50%+ below peer cluster average for same consumer type
            # Persistent reduction across whole series
            vals *= 0.45

        elif atype == "night_spike":
            # Significant surge between 01:00-04:00 on multiple days
            start_day = random.randint(n // 4, n * 3 // 4) // INTERVALS_PER_DAY
            for d in range(start_day, min(start_day + 5, n // INTERVALS_PER_DAY)):
                for h in range(1, 5):
                    idx = d * INTERVALS_PER_DAY + h * 4
                    if idx < n:
                        vals[idx:idx+4] *= 5.5  # 4.5x spike

        elif atype == "seasonal_nonconformity":
            # No summer rise in Apr-Jun for AC-category consumers
            for i, ts in enumerate(timestamps):
                if ts.month in SUMMER_MONTHS and meter.get("has_ac", False):
                    vals[i] *= 0.50  # Suppress AC load in summer (anomalous)

        elif atype == "gradual_drift":
            # Slow monotonic decline over 8+ weeks vs peer trend
            drift_start = max(0, n - 8 * 7 * INTERVALS_PER_DAY)
            slope = np.linspace(1.0, 0.25, n - drift_start)
            vals[drift_start:] *= slope

    return vals


# ── Feeder Aggregate ───────────────────────────────────────────────────────────
def generate_feeder_series(feeder: dict, meter_vals: list[np.ndarray],
                            timestamps: pd.DatetimeIndex) -> np.ndarray:
    """DT output = sum of meters + distribution loss factor."""
    agg   = np.sum(meter_vals, axis=0)
    loss  = np.random.uniform(0.04, 0.08, size=len(agg))   # 4–8% line loss
    dt_out = agg * (1 + loss)
    return dt_out.astype(np.float32)


# ── Anomaly Injection Map ──────────────────────────────────────────────────────
# 40 anomalies distributed evenly across all 7 types (~5-6 each)
ANOMALY_ASSIGNMENTS = [
    # meter_freeze (6 anomalies: indices 5, 25, 45, 65, 85, 105)
    (5,   "meter_freeze"),
    (25,  "meter_freeze"),
    (45,  "meter_freeze"),
    (65,  "meter_freeze"),
    (85,  "meter_freeze"),
    (105, "meter_freeze"),
    
    # dt_mismatch (6 anomalies: indices 10, 30, 50, 70, 90, 110)
    (10,  "dt_mismatch"),
    (30,  "dt_mismatch"),
    (50,  "dt_mismatch"),
    (70,  "dt_mismatch"),
    (90,  "dt_mismatch"),
    (110, "dt_mismatch"),
    
    # sustained_drop (6 anomalies: indices 15, 35, 55, 75, 95, 115)
    (15,  "sustained_drop"),
    (35,  "sustained_drop"),
    (55,  "sustained_drop"),
    (75,  "sustained_drop"),
    (95,  "sustained_drop"),
    (115, "sustained_drop"),
    
    # peer_deviation (6 anomalies: indices 20, 40, 60, 80, 100, 120)
    (20,  "peer_deviation"),
    (40,  "peer_deviation"),
    (60,  "peer_deviation"),
    (80,  "peer_deviation"),
    (100, "peer_deviation"),
    (120, "peer_deviation"),
    
    # night_spike (5 anomalies: indices 125, 130, 135, 140, 145)
    (125, "night_spike"),
    (130, "night_spike"),
    (135, "night_spike"),
    (140, "night_spike"),
    (145, "night_spike"),
    
    # seasonal_nonconformity (6 anomalies: indices 150, 155, 160, 165, 170, 175)
    (150, "seasonal_nonconformity"),
    (155, "seasonal_nonconformity"),
    (160, "seasonal_nonconformity"),
    (165, "seasonal_nonconformity"),
    (170, "seasonal_nonconformity"),
    (175, "seasonal_nonconformity"),
    
    # gradual_drift (5 anomalies: indices 180, 185, 190, 195, 199)
    (180, "gradual_drift"),
    (185, "gradual_drift"),
    (190, "gradual_drift"),
    (195, "gradual_drift"),
    (199, "gradual_drift"),
]

ANOMALY_METER_INDICES = {idx: atype for idx, atype in ANOMALY_ASSIGNMENTS}


# ── Main Generate Function ─────────────────────────────────────────────────────
def generate_all():
    print("Building metadata...")
    feeders, meters = build_metadata()

    timestamps = pd.date_range(start=START_DATE, end=END_DATE, freq="15min")
    print(f"Timestamps: {len(timestamps):,} intervals ({START_DATE.date()} to {END_DATE.date()})")

    # Save metadata
    with open(os.path.join(DATA_DIR, "feeders.json"), "w") as f:
        json.dump(feeders, f, indent=2)
    with open(os.path.join(DATA_DIR, "meters.json"), "w") as f:
        json.dump(meters, f, indent=2)
    print(f"Saved {len(feeders)} feeders, {len(meters)} meters")

    # Generate per-feeder data
    all_meter_data = {}
    for fi, feeder in enumerate(feeders):
        feeder_meters = [m for m in meters if m["feeder_id"] == feeder["feeder_id"]]
        meter_series_list = []

        for mi, meter in enumerate(feeder_meters):
            global_meter_idx = fi * METERS_PER_FEEDER + mi
            anomaly = None
            if global_meter_idx in ANOMALY_METER_INDICES:
                atype = ANOMALY_METER_INDICES[global_meter_idx]
                anomaly = {"type": atype, "anomaly_type": atype}

            vals = generate_meter_series(meter, timestamps, anomaly)
            meter_series_list.append(vals)
            all_meter_data[meter["meter_id"]] = vals

        # Feeder aggregate
        feeder_vals = generate_feeder_series(feeder, meter_series_list, timestamps)

        # Build DataFrames
        df_meters = pd.DataFrame(
            {m["meter_id"]: s for m, s in zip(feeder_meters, meter_series_list)},
            index=timestamps
        )
        df_meters.index.name = "timestamp"

        df_feeder = pd.DataFrame({
            "timestamp":     timestamps,
            "feeder_id":     feeder["feeder_id"],
            "consumption_kw": feeder_vals,
        }).set_index("timestamp")

        # Save parquet
        meter_path  = os.path.join(DATA_DIR, f"meters_{feeder['feeder_id']}.parquet")
        feeder_path = os.path.join(DATA_DIR, f"feeder_{feeder['feeder_id']}.parquet")
        df_meters.to_parquet(meter_path)
        df_feeder.to_parquet(feeder_path)

        rated = feeder["rated_mw"] * 1000  # kW
        cur   = float(np.mean(feeder_vals[-96:]))
        pct   = round(cur / rated * 100, 1)
        print(f"  [{feeder['feeder_id']}] {feeder['locality']:<15} current={cur:.0f}kW  rated={rated:.0f}kW  load={pct}%")

    print(f"\nDONE - data saved to: {DATA_DIR}")
    print(f"   Feeder parquets:  {len(feeders)}")
    print(f"   Meter parquets:   {len(feeders)}")
    print(f"   Anomalies injected: {len(ANOMALY_ASSIGNMENTS)}")
    print(f"   Distribution by type:")
    from collections import Counter
    anomaly_counts = Counter(atype for _, atype in ANOMALY_ASSIGNMENTS)
    for atype in sorted(anomaly_counts.keys()):
        print(f"      - {atype}: {anomaly_counts[atype]}")
    print(f"   Consumer ID masking: ENABLED (SHA-256 hashing)")


if __name__ == "__main__":
    generate_all()
