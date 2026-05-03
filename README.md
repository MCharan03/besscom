# BESCOM Smart Meter AI 🔌⚡

> **Full-stack AI platform for BESCOM grid demand forecasting and anomaly detection**  
> Built for the AI for Bharat Hackathon · KERC-Compliant · Explainable AI

---

## 🚀 Quick Start

```bash
# Clone / navigate to the project
cd "d:\Hackathon\ai for bharath"

# Install backend dependencies (first time only)
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies (first time only)
cd frontend
npm install
cd ..

# One-command launch (generates data + starts both servers)
start.bat
```

- **Dashboard:** http://localhost:5173  
- **API Docs (Swagger):** http://localhost:8000/docs

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    BESCOM Operator Browser                   │
│         React 18 + Vite Dashboard  (port 5173)              │
│  ┌──────────┬───────────┬──────────┬──────────┬──────────┐  │
│  │Command   │ Demand    │ Anomaly  │ Feeder   │ Audit    │  │
│  │Center    │ Forecast  │ Alerts   │ Map      │ Log      │  │
│  └──────────┴───────────┴──────────┴──────────┴──────────┘  │
└───────────────────────┬──────────────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────▼──────────────────────────────────────┐
│               FastAPI Backend  (port 8000)                   │
│  /dashboard  /feeders  /forecasts  /anomalies  /audit        │
└────────────┬─────────────────────────────────────┬───────────┘
             │                                     │
┌────────────▼──────────────┐    ┌─────────────────▼──────────┐
│       ML Engine           │    │   Synthetic Data Layer     │
│  - XGBoost + SHAP         │    │  20 feeders (5 localities) │
│  - Isolation Forest       │    │  200 meters, 24 months     │
│  - LSTM Autoencoder       │    │  15-min interval readings  │
│  - STL Decomposition      │    │  Bengaluru seasonality     │
│  - Rule Engine            │    │  15 injected anomalies     │
└───────────────────────────┘    └────────────────────────────┘
```

---

## 📊 Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| **Command Center** | `/` | KPI strip, 4×5 feeder risk grid, live alert feed, system status |
| **Demand Forecast** | `/forecast` | Per-feeder XGBoost forecast + 80/95% CI bands + STL + SHAP |
| **Anomaly Alerts** | `/alerts` | Tabbed alert table, full detail modal, confirm/dismiss/escalate |
| **Feeder Map** | `/map` | SVG Bengaluru locality map, click to expand feeder panel |
| **Audit Log** | `/audit` | Immutable event table, CSV export, KERC compliance |

---

## 🤖 ML Models

### Demand Forecasting
- **XGBoost Regressor** with walk-forward cross-validation
- **Quantile regression** for 80%/95% confidence intervals
- **SHAP TreeExplainer** for feature attribution
- **STL Decomposition** (statsmodels) for trend/seasonal/residual
- Feature engineering: lags (1h, 24h, 168h), rolling stats, calendar flags

### Anomaly Detection (3-Layer Ensemble)
| Layer | Methods |
|-------|---------|
| Statistical | Z-score (30d rolling), STL residual breach, IQR peer clustering |
| ML | Isolation Forest, LSTM Autoencoder, K-Means peer clustering |
| Rules | 5 deterministic rules (meter freeze, DT mismatch, night spike, etc.) |

**Composite Risk Score (0–100):** Statistical 40% + Pattern 30% + Peer 20% + Profile 10%

---

## 📍 Synthetic Data

**20 feeders across 5 Bengaluru localities:**

| Locality | Feeders | Consumer Mix |
|----------|---------|--------------|
| Jayanagar | F01–F04 | Residential-heavy |
| Shivajinagar | F05–F08 | Commercial-heavy |
| Whitefield | F09–F12 | Industrial + IT parks |
| Yeshwanthpur | F13–F16 | Mixed residential/commercial |
| Koramangala | F17–F20 | Mixed + high density |

**Baked-in patterns:** Summer peaks (Apr–Jun), festival spikes (Diwali, Ugadi), evening peaks (6–9 PM), weekend patterns.  
**15 injected anomalies:** Meter freeze, night spikes, peer deviation, seasonal non-conformity, DT aggregate mismatch.

---

## 🔐 PRD Compliance

| Requirement | Status |
|-------------|--------|
| No external LLM APIs | ✅ All ML runs on-machine |
| Read-only data access | ✅ Backend reads synthetic files only |
| Decision-support only | ✅ No automated control actions |
| SHAP explainability | ✅ Every forecast & alert has SHAP |
| Immutable audit log | ✅ Append-only + dedicated page |
| KERC compliance | ✅ Full audit trail + CSV export |
| False positive visibility | ✅ Review queue + FP Rate KPI |
| Masked consumer data | ✅ Meter IDs only, no PII |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Charts | Recharts |
| Styling | Vanilla CSS (glassmorphism dark theme) |
| Backend | FastAPI (Python 3.11) |
| ML | XGBoost, scikit-learn, statsmodels |
| Explainability | SHAP |
| Data | pandas, numpy, pyarrow |
| Fonts | Inter (Google Fonts) |

---

## 📂 File Structure

```
├── backend/
│   ├── main.py                 # FastAPI + all API routes
│   ├── data_generator.py       # Synthetic Bengaluru data
│   ├── ml/
│   │   ├── forecasting.py      # XGBoost + SHAP + STL
│   │   └── anomaly_detection.py # Isolation Forest + Rules
│   ├── models/
│   │   └── schemas.py          # Pydantic response models
│   ├── data/                   # Generated parquet files
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/         # Sidebar, TopBar, Charts, etc.
│       └── pages/              # 5 dashboard pages
├── start.bat                   # One-command startup
└── README.md
```

---

*Built with ❤️ for AI for Bharat Hackathon · BESCOM Smart Meter Intelligence Platform*
