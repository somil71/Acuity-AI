# Acuity-AI
*Intelligent Patient Flow & Clinical Operations Platform*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![LightGBM](https://img.shields.io/badge/LightGBM-ff69b4?style=flat-square&logo=lightgbm)](https://lightgbm.readthedocs.io/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)

**Acuity-AI** bridges the gap between patient transparency and hospital operational intelligence. By unifying a modern patient portal with an advanced Emergency Department (ED) and outpatient command center, it solves the dual problem of patient wait-time anxiety and hospital capacity bottlenecking.

---

## 🌟 Key Capabilities

### For Operations & Staff (Command Center)
- **Live Queue Health Score (0-100)**: Composite metric tracking census pressure, arrival velocity, and acuity load.
- **Multi-Horizon Congestion Forecasting**: LightGBM-powered classifications predicting department congestion (Low, Moderate, Busy, Critical) at 30, 60, and 120-minute intervals.
- **Bottleneck Detection**: Real-time identification of specific physician overruns and department-wide queue breaches.
- **What-If Simulation**: Model the impact of capacity changes, arrival surges, or discharge accelerations using Monte Carlo simulations.

### For Patients (Portal)
- **Wait-Time Transparency**: ML-driven duration predictions backed by **Conformal Calibration**, guaranteeing 90% statistical coverage on estimated wait windows.
- **SHAP Explainability**: "Why this estimate?" factor breakdowns (e.g., *"+3 min due to High Acuity Surge"*), promoting trust.
- **Complete Clinical Loop**: Secure messaging, health records & lab result timelines, prescription refills, and billing/invoice payments.
- **AI Triage**: Symptom-based department routing and urgency assessment.

---

## 🧠 Machine Learning Engine
Acuity-AI utilizes a sophisticated, leakage-free ML pipeline trained on realistic clinical data.
- **Conformal Prediction Intervals**: Replaces heuristic quantiles with formal mathematical guarantees on prediction intervals.
- **TreeSHAP Attributions**: Per-prediction feature impact extraction.
- **MIMIC-IV-ED Compatibility**: Ships with a synthetic generator matching the exact schema of the official PhysioNet MIMIC-IV-ED dataset, allowing seamless drop-in of real hospital data.
- **Anomaly Detection**: CUSUM (Cumulative Sum) tracking for sudden queue depth spikes.

*(See [docs/ml_methodology.md](./docs/ml_methodology.md) for a deep dive into our chronological splitting, leakage prevention, and model architectures).*

---

## 🏗️ Architecture Stack
- **Frontend**: Next.js 16, React 19, Tailwind CSS v4, SWR for reactive polling.
- **Backend**: FastAPI, SQLAlchemy, SQLite (stateless API design).
- **Security**: JWT-based Role-Based Access Control (RBAC) supporting `patient`, `staff`, and `admin` scopes.
- **Data Engineering**: Pandas & NumPy for real-time feature snapshotting.

*(See [docs/architecture.md](./docs/architecture.md) for system design).*

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start the API server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Demo Credentials
The system comes pre-seeded with demo data.
- **Patient**: Username: `PAT_1`, Password: `pat`
- **Staff (Doctor)**: Username: `DOC_CAR_1`, Password: `doc`
- **Admin**: Username: `admin1`, Password: `admin`

---

## 🧪 Testing & Audits
Acuity-AI maintains a rigorous quality standard:
- **API Tests**: Comprehensive Playwright E2E suite covering 51 critical user flows (`tests/audit.mjs`).
- **ML Coverage**: Validated 90%+ marginal coverage on conformal intervals.

```bash
# Run the audit suite
node tests/audit.mjs
```

---
*Developed as a next-generation approach to hospital flow dynamics and patient experience.*
