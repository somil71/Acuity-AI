# Machine Learning & AI Methodology

Acuity-AI employs a rigorous, production-ready machine learning approach designed to prioritize patient safety, statistical validity, and operational transparency.

## 1. Conformal Prediction for Wait Times

Standard machine learning regression outputs a single point estimate (e.g., "22 minutes"). While useful, this fails to communicate uncertainty to the patient. Previous iterations used heuristic LightGBM quantiles (P10/P90), which lacked formal coverage guarantees.

**Our Approach:** Split-Conformal Calibration
1. We train a median (`q=0.5`) LightGBM duration model on the training split.
2. On a strictly held-out calibration set, we calculate the absolute residuals: $R_i = |y_i - \hat{y}_i|$.
3. We compute the $(1-\alpha)(1+1/n)$ empirical quantile of these residuals to find our cutoff $q$.
4. At inference time, our interval is: $[\max(0, \hat{y} - q), \hat{y} + q]$.

**Why?** This provides a mathematical, distribution-free guarantee of marginal coverage (e.g., exactly 90% of future patients will be seen within their quoted window, assuming exchangeability).

## 2. SHAP Explainability (TreeSHAP)

To foster trust with patients and staff, predictive models cannot act as "black boxes." 

We wrap our LightGBM duration models in `shap.TreeExplainer`. At inference time, we calculate the exact additive Shapley values for the patient's specific feature vector. 

**Patient Portal Output:**
The backend maps one-hot encoded features back to human-readable strings (e.g., `queue_depth: 4` $\rightarrow$ "4 Patients Ahead"), extracting the top factors driving the wait time up or down relative to the baseline average.

## 3. Multi-Horizon Congestion Forecasting

Operations managers need to know not just *how busy it is now*, but *how busy it will be*.

We built three distinct LightGBM classifiers predicting the hospital's congestion tier (`LOW`, `MODERATE`, `BUSY`, `CRITICAL`) at 30, 60, and 120-minute forward horizons.

**Features Extracted (Point-in-Time Snapshots):**
- **Flow Velocity:** Arrivals and departures rolling windows (15m, 30m, 60m).
- **Acuity Load:** Ratio of Emergency Severity Index (ESI) 1 & 2 patients to total active census.
- **Seasonality:** Hour of day, day of week, month.

## 4. Strict Leakage Prevention

In healthcare operations, predicting the future using data that wouldn't be available at the time of the prediction is a fatal error.

**Chronological Splitting:**
We strictly enforce temporal train/val/test splits (70/15/15). 
$$\max(T_{\text{train}}) \le \min(T_{\text{val}}) \le \max(T_{\text{val}}) \le \min(T_{\text{test}})$$
Random sampling cross-validation is prohibited, as it allows future congestion states to bleed into historical training data.

**Event Filtering:**
When building historical snapshots for training the congestion models, any event (vital sign recorded, arrival, departure) where $t_{\text{event}} > T_{\text{snapshot}}$ is explicitly masked and excluded.

## 5. MIMIC-IV-ED Compatibility

Our data pipeline is natively compatible with the [MIMIC-IV-ED dataset](https://physionet.org/content/mimic-iv-ed/), the gold standard for emergency department flow research. 

Because MIMIC requires credentialing and a signed DUA, Acuity-AI ships with a `mimic_generator.py` script. This generates a synthetic dataset containing realistic clinical distributions (Poisson arrivals, Lognormal length-of-stays, bounded physiological vitals) shaped exactly like the MIMIC schemas (`edstays`, `triage`, `vitalsign`). When you obtain your PhysioNet credentials, you can drop the real CSVs in and retrain with zero code changes.
