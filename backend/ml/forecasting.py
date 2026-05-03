"""
BESCOM Smart Meter AI — Demand Forecasting ML Module
XGBoost regressor with lag features, quantile regression for CI bands,
SHAP feature attribution, and STL decomposition.
"""

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from statsmodels.tsa.seasonal import STL
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

FESTIVALS = {(10,20),(10,31),(3,30),(4,18),(8,26),(9,15),(12,25),(1,1),(12,31)}
SUMMER_MONTHS = {4, 5, 6}


def is_festival(dt) -> int:
    return int((dt.month, dt.day) in FESTIVALS)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer all lag + calendar features."""
    df = df.copy()
    col = df.columns[0] if df.columns[0] != "timestamp" else df.columns[1]
    df = df.rename(columns={col: "y"})

    # Calendar
    df["hour"]       = df.index.hour
    df["dow"]        = df.index.dayofweek
    df["month"]      = df.index.month
    df["is_weekend"] = (df["dow"] >= 5).astype(int)
    df["is_summer"]  = df["month"].isin(SUMMER_MONTHS).astype(int)
    df["is_festival"]= df.index.map(is_festival)
    df["is_peak"]    = df["hour"].between(18, 21).astype(int)
    df["is_trough"]  = df["hour"].between(2, 4).astype(int)

    # Lags (15-min intervals)
    df["lag_1h"]    = df["y"].shift(4)
    df["lag_24h"]   = df["y"].shift(96)
    df["lag_168h"]  = df["y"].shift(672)
    df["lag_336h"]  = df["y"].shift(1344)

    # Rolling statistics
    df["roll_7d_mean"]  = df["y"].shift(1).rolling(672).mean()
    df["roll_30d_mean"] = df["y"].shift(1).rolling(2880).mean()
    df["roll_7d_std"]   = df["y"].shift(1).rolling(672).std()
    df["roll_24h_max"]  = df["y"].shift(1).rolling(96).max()

    # Time encoding (cyclic)
    df["hour_sin"]  = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]  = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"]   = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"]   = np.cos(2 * np.pi * df["dow"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * (df["month"] - 1) / 12)
    df["month_cos"] = np.cos(2 * np.pi * (df["month"] - 1) / 12)

    return df.dropna()


FEATURE_COLS = [
    "hour", "dow", "month", "is_weekend", "is_summer", "is_festival",
    "is_peak", "is_trough",
    "lag_1h", "lag_24h", "lag_168h", "lag_336h",
    "roll_7d_mean", "roll_30d_mean", "roll_7d_std", "roll_24h_max",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
]

FEATURE_LABELS = {
    "lag_24h": "Same hour yesterday",
    "lag_168h": "Same hour last week",
    "roll_7d_mean": "7-day rolling avg",
    "roll_30d_mean": "30-day rolling avg",
    "is_summer": "Summer season",
    "is_peak": "Evening peak hours",
    "is_festival": "Festival day",
    "is_weekend": "Weekend",
    "hour_sin": "Time of day (sin)",
    "hour_cos": "Time of day (cos)",
    "lag_1h": "1-hour lag",
    "roll_7d_std": "7-day variability",
    "roll_24h_max": "24h peak reading",
    "dow_sin": "Day of week (sin)",
    "is_trough": "Night trough hours",
    "lag_336h": "Two-week lag",
    "dow_cos": "Day of week (cos)",
    "month_sin": "Month (sin)",
    "month_cos": "Month (cos)",
    "dow": "Day of week",
    "month": "Month",
    "hour": "Hour of day",
}


class DemandForecaster:
    def __init__(self, feeder_id: str):
        self.feeder_id = feeder_id
        self.model_mean = None
        self.model_low80 = None
        self.model_high80 = None
        self.model_low95 = None
        self.model_high95 = None
        self.explainer = None
        self._df = None

    def _load_data(self) -> pd.DataFrame:
        path = os.path.join(DATA_DIR, f"feeder_{self.feeder_id}.parquet")
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        return df[["consumption_kw"]]

    def _make_xgb(self, objective="reg:squarederror", **kwargs):
        return xgb.XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective=objective,
            random_state=42,
            n_jobs=-1,
            **kwargs,
        )

    def train(self):
        raw = self._load_data()
        self._df = raw
        feat = build_features(raw)

        X = feat[FEATURE_COLS]
        y = feat["y"]

        # Walk-forward split: train on first 18 months
        split = int(len(X) * 0.75)
        X_tr, y_tr = X.iloc[:split], y.iloc[:split]

        # Point forecast
        self.model_mean = self._make_xgb()
        self.model_mean.fit(X_tr, y_tr)

        # Quantile models for CI bands
        for attr, q in [
            ("model_low80", 0.10), ("model_high80", 0.90),
            ("model_low95", 0.025), ("model_high95", 0.975),
        ]:
            m = self._make_xgb(objective="reg:quantileerror", quantile_alpha=q)
            m.fit(X_tr, y_tr)
            setattr(self, attr, m)

        # SHAP explainer (tree-based)
        self.explainer = shap.TreeExplainer(self.model_mean)

    def forecast(self, hours_ahead: int = 24) -> dict:
        """Generate forecast for next `hours_ahead` hours (96 × 15-min intervals)."""
        if self.model_mean is None:
            self.train()

        n_intervals = hours_ahead * 4
        raw = self._df

        # Last known timestamp
        last_ts = raw.index[-1]
        future_idx = pd.date_range(
            start=last_ts + timedelta(minutes=15),
            periods=n_intervals,
            freq="15min",
        )

        # Bootstrap future by repeating last-week same-hour window
        week_back = raw.iloc[-672:].copy()
        week_back.index = future_idx[:len(week_back)]
        extended = pd.concat([raw, week_back.reindex(future_idx, method="nearest")])
        extended = extended[~extended.index.duplicated(keep="last")]

        feat = build_features(extended)
        future_feat = feat.loc[feat.index >= future_idx[0]]
        if len(future_feat) == 0:
            future_feat = feat.iloc[-n_intervals:]

        future_feat = future_feat.iloc[:n_intervals]
        X_fut = future_feat[FEATURE_COLS]

        y_mean  = self.model_mean.predict(X_fut)
        y_l80   = self.model_low80.predict(X_fut)
        y_h80   = self.model_high80.predict(X_fut)
        y_l95   = self.model_low95.predict(X_fut)
        y_h95   = self.model_high95.predict(X_fut)

        # SHAP for first 4 intervals (1 hr) as representative
        shap_vals = self.explainer.shap_values(X_fut.iloc[:4])
        shap_mean = np.mean(np.abs(shap_vals), axis=0)
        shap_pairs = sorted(zip(FEATURE_COLS, shap_mean), key=lambda x: x[1], reverse=True)[:8]
        shap_output = [
            {
                "feature": FEATURE_LABELS.get(f, f),
                "value": round(float(v), 3),
                "positive": float(v) > 0,
            }
            for f, v in shap_pairs
        ]

        # Naive baseline: same 24h window from 7 days ago
        hist_7d = raw.iloc[-672:]["consumption_kw"].values
        naive = np.tile(hist_7d[:96], (n_intervals // 96) + 1)[:n_intervals]

        return {
            "feeder_id": self.feeder_id,
            "generated_at": datetime.utcnow().isoformat(),
            "hours_ahead": hours_ahead,
            "timestamps": [ts.isoformat() for ts in future_feat.index[:n_intervals]],
            "forecast":   [round(float(v), 2) for v in y_mean],
            "ci_80_low":  [round(float(v), 2) for v in y_l80],
            "ci_80_high": [round(float(v), 2) for v in y_h80],
            "ci_95_low":  [round(float(v), 2) for v in y_l95],
            "ci_95_high": [round(float(v), 2) for v in y_h95],
            "naive_baseline": [round(float(v), 2) for v in naive],
            "shap_features": shap_output,
            "peak_forecast_kw": round(float(np.max(y_mean)), 1),
            "peak_time": future_feat.index[int(np.argmax(y_mean))].isoformat(),
        }

    def history(self, days: int = 7) -> dict:
        raw = self._df if self._df is not None else self._load_data()
        n = days * 96
        subset = raw.iloc[-n:] if len(raw) >= n else raw
        return {
            "feeder_id": self.feeder_id,
            "days": days,
            "timestamps": [ts.isoformat() for ts in subset.index],
            "values": [round(float(v), 2) for v in subset["consumption_kw"]],
        }

    def stl_decomposition(self, days: int = 30) -> dict:
        raw = self._df if self._df is not None else self._load_data()
        n = days * 96
        subset = raw.iloc[-n:]["consumption_kw"]
        # Resample to hourly for STL (period = 24)
        hourly = subset.resample("h").mean().dropna()
        stl = STL(hourly, period=24, robust=True).fit()
        return {
            "timestamps": [ts.isoformat() for ts in hourly.index],
            "observed":   [round(float(v), 2) for v in stl.observed],
            "trend":      [round(float(v), 2) for v in stl.trend],
            "seasonal":   [round(float(v), 2) for v in stl.seasonal],
            "residual":   [round(float(v), 2) for v in stl.resid],
        }


INTERVALS_PER_DAY = 96

# Cache trained models in memory (per feeder)
_forecaster_cache: dict[str, DemandForecaster] = {}


def get_forecaster(feeder_id: str) -> DemandForecaster:
    if feeder_id not in _forecaster_cache:
        fc = DemandForecaster(feeder_id)
        fc.train()
        _forecaster_cache[feeder_id] = fc
    return _forecaster_cache[feeder_id]
