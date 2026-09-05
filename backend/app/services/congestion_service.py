"""
Congestion forecast service — uses trained LightGBM models when available,
falls back to rule-based estimation from queue health score.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.services.queue_health_service import get_dept_queue_health

logger = logging.getLogger(__name__)

DEPARTMENTS = ['Cardiology', 'General Physician', 'Orthopedics', 'Pediatrics']
TIER_COLORS = {'low': 'green', 'moderate': 'yellow', 'busy': 'orange', 'critical': 'red'}
TIER_LABELS = {
    'low': 'Low load expected',
    'moderate': 'Moderate load expected',
    'busy': 'High load expected',
    'critical': 'Critical load expected'
}
TIER_ORDER = ['low', 'moderate', 'busy', 'critical']

# ── Model loading (lazy, once) ─────────────────────────────────────────────────
_models = {}
_label_encoder = None
_feature_names = None
_models_loaded = False

def _try_load_models():
    global _models, _label_encoder, _feature_names, _models_loaded
    if _models_loaded:
        return bool(_models)

    # Walk up from backend/app/services → project root → ml/models
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    model_dir = os.path.join(base, 'ml', 'models')

    try:
        import lightgbm as lgb
        import joblib

        models = {}
        for h in [30, 60, 120]:
            path = os.path.join(model_dir, f'congestion_{h}m.txt')
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing: {path}")
            models[h] = lgb.Booster(model_file=path)

        enc_path = os.path.join(model_dir, 'congestion_label_encoder.pkl')
        label_encoder = joblib.load(enc_path)

        meta_path = os.path.join(model_dir, 'congestion_metadata.json')
        with open(meta_path) as f:
            meta = json.load(f)

        _models = models
        _label_encoder = label_encoder
        _feature_names = meta['feature_names']
        _models_loaded = True
        logger.info("Congestion ML models loaded successfully from %s", model_dir)
        return True
    except Exception as e:
        logger.warning("Could not load congestion ML models (%s) — using rule-based fallback", e)
        _models_loaded = True   # don't retry every call
        return False


def _build_snapshot_features(health: dict, now: datetime) -> dict:
    """Build feature dict from live queue health data for ML inference."""
    # Approximate snapshot features from what we have in queue health
    active = health['active_count']
    arr_60 = health['arrivals_60m']
    high_acuity = health['high_acuity_ratio']

    # Approximate shorter windows (30m ≈ 55% of 60m, 15m ≈ 30%, 120m ≈ 170%)
    arr_15 = max(0, round(arr_60 * 0.30))
    arr_30 = max(0, round(arr_60 * 0.55))
    arr_120 = max(0, round(arr_60 * 1.70))
    dep_30 = max(0, round(arr_30 * 0.85))  # assume similar departure rate
    dep_60 = max(0, round(arr_60 * 0.80))
    net_flow = arr_60 - dep_60
    trend = (arr_30 / arr_60) if arr_60 > 0 else 1.0
    mean_time = 60.0  # approximate 60 min average time in system

    return {
        'current_active_census': active,
        'arrivals_15m': arr_15,
        'arrivals_30m': arr_30,
        'arrivals_60m': arr_60,
        'arrivals_120m': arr_120,
        'departures_30m': dep_30,
        'departures_60m': dep_60,
        'net_flow_60m': net_flow,
        'high_acuity_ratio': high_acuity,
        'mean_time_in_system': mean_time,
        'hour_of_day': now.hour,
        'day_of_week': now.weekday(),
        'month': now.month,
        'arrival_rate_trend': round(trend, 3),
    }


def _ml_forecast(features: dict, horizon: int, current_state: str) -> dict:
    """Run LightGBM classifier inference for a single horizon."""
    import pandas as pd
    import numpy as np

    df = pd.DataFrame([features])[_feature_names]
    proba = _models[horizon].predict(df)[0]  # array of class probabilities

    if hasattr(_label_encoder, 'classes_'):
        classes = list(_label_encoder.classes_)
    else:
        classes = list(_label_encoder.keys())

    best_idx = int(np.argmax(proba))
    tier = classes[best_idx]
    confidence = round(float(proba[best_idx]), 3)

    return {
        'tier': tier,
        'confidence': confidence,
        'color': TIER_COLORS.get(tier, 'gray'),
        'label': TIER_LABELS.get(tier, tier),
    }


def _rule_based_forecast(queue_health_score: float, horizon_mins: int) -> dict:
    if queue_health_score < 30:
        tier = 'low'
    elif queue_health_score < 55:
        tier = 'moderate'
    elif queue_health_score < 75:
        tier = 'busy'
    else:
        tier = 'critical'

    # Confidence decreases with horizon
    confidence = round(max(0.40, 0.80 - (horizon_mins / 300.0)), 2)
    return {
        'tier': tier,
        'confidence': confidence,
        'color': TIER_COLORS[tier],
        'label': TIER_LABELS[tier],
    }


def get_congestion_forecast(db: Session, department: str = None) -> list:
    """Return congestion forecast for one or all departments."""
    depts = [department] if department else DEPARTMENTS
    has_ml = _try_load_models()
    now = datetime.utcnow()

    results = []
    for dept in depts:
        health = get_dept_queue_health(db, dept)
        score = health['score']

        if has_ml:
            try:
                features = _build_snapshot_features(health, now)
                horizons = {
                    '30m':  _ml_forecast(features, 30,  health['state']),
                    '60m':  _ml_forecast(features, 60,  health['state']),
                    '120m': _ml_forecast(features, 120, health['state']),
                }
                source = 'lgbm'
            except Exception as e:
                logger.warning("ML inference failed for %s: %s — using rule-based", dept, e)
                horizons = {
                    '30m':  _rule_based_forecast(score, 30),
                    '60m':  _rule_based_forecast(score, 60),
                    '120m': _rule_based_forecast(score, 120),
                }
                source = 'rule_based'
        else:
            horizons = {
                '30m':  _rule_based_forecast(score, 30),
                '60m':  _rule_based_forecast(score, 60),
                '120m': _rule_based_forecast(score, 120),
            }
            source = 'rule_based'

        results.append({
            'department': dept,
            'current_state': health['state'],
            'horizons': horizons,
            'model_source': source,
        })

    return results
