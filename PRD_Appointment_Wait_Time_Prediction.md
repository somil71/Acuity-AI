# Product Requirements Document
## Predictive Appointment Wait-Time System for Hospitals

**Status:** Draft v1.0
**Owner:** Somil
**Last updated:** September 2026

---

## 1. Problem Statement

Hospitals assign patients fixed appointment slots (e.g., 10:00 AM), but the *actual* time a doctor sees the patient often drifts significantly due to:

- Influx of emergency/walk-in cases that day
- Staff shortages (nurses, technicians, support staff)
- Doctor-specific factors (on leave, running behind, in surgery)
- Queue backlog — number of patients already ahead in the doctor's list
- Department-specific consultation time variance (a General Physician visit averages far less time than a Cardiologist or Oncologist consult)
- Day-of-week / seasonal patterns (Mondays and post-holiday days tend to be busier)

The result: patients scheduled for 10 AM may not be seen until 1 PM, with no visibility into the delay until they've already wasted hours waiting at the hospital.

**Core idea:** Build a system that predicts a *realistic* expected consultation time for each patient — not just the nominal slot — using live and historical data, and communicates this proactively so patients can plan their arrival instead of sitting in a waiting room.

---

## 2. Goals & Objectives

| Goal | Description |
|---|---|
| G1 | Predict expected actual consultation time (not just booked slot) for a given patient's appointment, updated dynamically as the day progresses |
| G2 | Reduce patient in-hospital idle/waiting time by giving accurate arrival-time recommendations |
| G3 | Give hospital staff a live view of queue drift and bottlenecks per doctor/department |
| G4 | Maintain a longitudinal patient record (visit history, prescriptions, past wait patterns) accessible to the patient and doctor |
| G5 | Build a system that generalizes across departments with very different consultation-time baselines |

### Non-goals (out of scope for v1)
- Replacing the hospital's existing appointment booking / scheduling system (this augments it, doesn't replace it)
- Diagnosis, triage severity classification, or any clinical decision-making
- Insurance, billing, or payment processing
- Multi-hospital network optimization (v1 is single-facility)

---

## 3. Users & Personas

1. **Patient** — booked an appointment, wants to know realistically when to arrive instead of showing up at the nominal slot and waiting for hours.
2. **Doctor** — wants a realistic live queue view, not a rigid slot list that's already wrong by 11 AM.
3. **Front-desk / Hospital Admin Staff** — manages check-ins, needs visibility into which doctors are backed up, needs to reallocate patients or notify them of delays.
4. **Hospital Operations / Management** — wants aggregate analytics: which departments chronically overrun, staffing gaps, patient satisfaction impact.

---

## 4. Core Features

### 4.1 Predictive Wait-Time Engine (core ML system)
- For every booked appointment, continuously output: **predicted actual consultation time**, with a confidence interval (e.g., "1:00 PM – 1:20 PM").
- Predictions recompute in near-real-time as the day unfolds (a new emergency case at 11 AM should shift downstream predictions immediately).
- Model factors in (see Section 6 for full feature list): doctor's current backlog, emergency case count, staff availability, department-average consult duration, patient's position in queue, historical drift patterns for that doctor/department/day-of-week.

### 4.2 Patient-Facing App/Portal
- Shows current predicted time for their upcoming appointment, with push/SMS notification if it shifts by more than a threshold (e.g., >20 min change).
- "Leave-by" or "arrive-by" recommendation instead of raw prediction, factoring in patient's stated travel time.
- Patient history: past visits, prescriptions/notes attached by doctor, past wait-time patterns for their own reference.

### 4.3 Doctor/Staff Dashboard
- Live queue view per doctor: booked patients, actual arrival status, revised order.
- Emergency-case injection flow — when an emergency is logged, system immediately recalculates downstream predictions and notifies affected patients.
- Staff availability input (shift start/end, absences) feeding directly into the model.

### 4.4 Admin/Operations Dashboard
- Department-wise and doctor-wise historical accuracy of predictions vs. actuals.
- Bottleneck analytics: which department/doctor/day combinations chronically overrun, by how much.
- Staffing-gap correlation: does wait time spike correlate with specific staff being absent?

### 4.5 Patient Record System
- Persistent record per patient: visit history, department visited, doctor seen, notes/prescriptions (structured fields, not full EHR scope in v1), and their personal historical wait-time experience.
- Used both for patient self-reference and as a feature source for the model (e.g., patients with certain chronic-care follow-ups may have predictably shorter/longer consults).

---

## 5. System Architecture (high-level)

```
┌─────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│ Booking System   │─────▶│ Data Ingestion    │─────▶│ Feature Store       │
│ (existing/new)   │      │ Layer (events)    │      │ (real-time + hist.) │
└─────────────────┘      └──────────────────┘      └─────────┬──────────┘
                                                               │
┌─────────────────┐      ┌──────────────────┐      ┌─────────▼──────────┐
│ Staff/Doctor     │─────▶│ Live Queue State  │─────▶│ Prediction Engine   │
│ Availability     │      │ Manager           │      │ (ML model + rules)  │
│ Input            │      └──────────────────┘      └─────────┬──────────┘
└─────────────────┘                                            │
┌─────────────────┐      ┌──────────────────┐      ┌─────────▼──────────┐
│ Emergency Case   │─────▶│ Event Bus /       │      │ Notification &      │
│ Logging          │      │ Recompute Trigger │      │ Patient/Staff UI     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

Key design principle: this is a **live, event-driven recomputation system**, not a batch one-time prediction. Every state change (emergency logged, doctor delayed, staff marked absent, patient no-show) should trigger a recompute of downstream predictions.

---

## 6. ML Approach

### 6.1 Prediction target
`actual_consultation_start_time − scheduled_appointment_time` (delay, in minutes), or directly the predicted timestamp. Framing as a **regression on delay** is cleaner since it's more stable across departments than absolute time.

### 6.2 Feature categories

**Doctor/queue-state features**
- Number of patients ahead of this one in the doctor's queue today
- Doctor's average running-behind time so far today (real-time signal)
- Doctor's historical average delay (rolling window, e.g., last 30 days)
- Doctor currently in emergency/surgery flag

**Staffing features**
- Support staff count present vs. rostered for that shift
- Nurse-to-doctor ratio available that day
- Any flagged staff shortage/absence

**Case-load features**
- Number of emergency/walk-in cases logged so far today (hospital-wide and department-wide)
- Total booked appointments that day for this doctor/department
- Historical case-load pattern for this day of week / date (e.g., Mondays, post-holiday, flu season)

**Department features**
- Department-wise average consultation duration (e.g., General Physician ~8-10 min vs. Cardiologist ~20-25 min) — computed as a rolling historical average per department, not hardcoded
- Department-specific variance (some departments are more unpredictable than others)

**Patient-specific features**
- Patient's appointment type (new consultation vs. follow-up — follow-ups are often faster)
- Patient's historical no-show/late-arrival pattern (affects queue dynamics)
- Time already elapsed since patient's scheduled slot (if querying mid-wait)

**Temporal features**
- Time of day, day of week, month/season
- Proximity to holidays or known high-load periods

### 6.3 Modeling strategy
- **Baseline (v1):** Gradient-boosted trees (XGBoost/LightGBM) on the engineered features above — strong choice given the tabular, mixed-type feature set and need for interpretability (hospitals will want to know *why* a prediction is what it is).
- **Cold-start handling:** for doctors/departments with insufficient historical data, fall back to department-wide or hospital-wide averages with wider confidence intervals.
- **Online/incremental updates:** the live queue-state features must be recomputed per request (not stale), even though the trained model itself may retrain on a daily/weekly cadence.
- **Confidence intervals:** use quantile regression or a lightweight ensemble to output a predicted range, not just a point estimate — critical for setting patient expectations honestly.
- **Explainability:** SHAP or similar for the admin dashboard, so operations staff can see *why* a doctor is predicted to run late (e.g., "3 emergency cases + 1 staff absence today").

### 6.4 Retraining & feedback loop
- Every completed appointment logs actual vs. predicted time — this becomes new training data.
- Scheduled retraining (e.g., weekly) plus drift monitoring (if prediction error trends upward, trigger retrain/alert).

---

## 7. Data Requirements

| Data | Source | Notes |
|---|---|---|
| Appointment bookings (scheduled time, doctor, department, patient) | Hospital booking system | Core input |
| Actual consultation start/end times | Check-in/check-out logging (front desk or doctor-side "start consult" button) | Ground truth for training |
| Emergency case logs | Staff-entered, timestamped | Real-time feature |
| Staff roster & attendance | HR/admin system or manual daily input | Real-time + historical |
| Patient visit history | Internal patient record system | Also patient-facing feature |
| Department reference data | Historical aggregation from consultation logs | Computed, not manually maintained |

**Data collection gap to flag:** this system's biggest dependency is having *actual* consultation start times logged, not just booked times. If the hospital doesn't already capture "doctor actually started seeing patient at X," that instrumentation has to be built first — it's the ground truth the whole model depends on.

---

## 8. Success Metrics

| Metric | Target (illustrative — tune with real hospital) |
|---|---|
| Mean Absolute Error of predicted vs. actual consultation time | < 15 minutes at steady state |
| % of predictions within ±20 min of actual | > 75% |
| Reduction in average patient in-hospital waiting time | Track pre/post rollout |
| Patient satisfaction / NPS on wait-time predictability | Survey-based |
| Notification accuracy (did the "arrive by" recommendation avoid unnecessary early arrival or missed slots) | Track patient-reported outcomes |

---

## 9. Non-Functional Requirements
- **Latency:** prediction recompute should complete within a few seconds of a triggering event (new emergency, staff update) so the UI feels live.
- **Privacy:** patient records and visit history involve sensitive health data — requires proper access control, encryption at rest/in transit, and compliance with applicable healthcare data regulations for the deployment region.
- **Reliability:** the system should degrade gracefully — if the ML service is down, fall back to showing the scheduled slot rather than failing silently or showing stale data.
- **Auditability:** every prediction and its underlying feature snapshot should be logged for later analysis/debugging.

---

## 10. Risks & Open Questions

- **Cold start:** a new hospital/department has no historical drift data — need a sensible fallback and a plan for how fast the model becomes useful.
- **Data instrumentation:** does the hospital already log actual consultation start times? If not, this is a prerequisite, not a v1 feature.
- **Behavioral feedback loop:** if patients start arriving late based on predictions, does that itself change the queue dynamics the model was trained on? (Self-fulfilling prediction risk — worth monitoring post-launch.)
- **Emergency-case unpredictability:** emergencies are inherently unpredictable; the model should communicate *uncertainty* honestly rather than false precision.
- **Staff data entry burden:** if staff availability/absence has to be manually entered, adoption friction could undermine data quality — consider integrating with existing HR/roster systems instead of a new manual input.

---

## 11. Rollout Plan (suggested phases)

1. **Phase 0 — Instrumentation:** ensure actual consult start/end times are captured; build the patient record schema.
2. **Phase 1 — Historical baseline model:** train on retrospective data (department averages, doctor averages, day-of-week patterns) without live event-driven recompute; validate offline accuracy.
3. **Phase 2 — Live recompute engine:** add real-time emergency/staffing event triggers and dynamic recomputation.
4. **Phase 3 — Patient-facing rollout:** notifications, "arrive by" recommendations, patient portal.
5. **Phase 4 — Admin analytics & feedback loop:** bottleneck dashboards, retraining pipeline, drift monitoring.

---

## 12. Appendix: Example Prediction Flow

1. Patient X booked for 10:00 AM with Dr. Y (Cardiology).
2. At 8:45 AM, system computes initial prediction: 10:10 AM (small buffer, based on Dr. Y's typical morning pace).
3. At 9:30 AM, two emergency cases are logged for Dr. Y. Event bus triggers recompute.
4. New prediction for Patient X: 12:40 PM – 1:00 PM. Patient is notified via app/SMS.
5. Patient adjusts arrival time accordingly instead of sitting in the waiting room from 9:45 AM.
6. At 12:50 PM, Dr. Y actually starts seeing Patient X. This is logged as ground truth for future model training.
