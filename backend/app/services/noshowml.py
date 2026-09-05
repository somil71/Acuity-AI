"""
noshowml.py - Calibrated Heuristic No-Show Risk Scorer
=======================================================
Approximates a trained binary classifier using domain-weighted heuristics.
Designed to be swapped for a real LightGBM model once labelled no-show data
is available (collect data, label with actual_start_time IS NULL as no-show,
train a classifier on the same feature set, then replace compute_risk_score).

Risk score: float in [0.0, 1.0]
  0.00 - 0.33  -> "low"
  0.33 - 0.66  -> "medium"
  0.67 - 1.00  -> "high"
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class NoShowPredictor:
    """
    Heuristic no-show risk scorer.

    Population base-rate: 25% (base_score = 0.25), consistent with
    published hospital no-show rates (15-30%).

    Usage::

        predictor = NoShowPredictor()
        score = predictor.compute_risk_score(appointment_obj, past_appointments_list)
    """

    BASE_SCORE: float = 0.25

    # Factor weights (additive unless noted)
    W_FAR_APPOINTMENT: float = 0.15    # >7 days away: people forget
    W_SAME_DAY: float = -0.15          # Same day: high commitment
    W_NEW_PATIENT: float = 0.10        # New appointments no-show more
    W_EARLY_MORNING: float = 0.10      # Before 09:00
    W_LUNCH_HOUR: float = 0.08         # 12:00-13:59
    W_MONDAY: float = 0.05             # Start-of-week fatigue
    W_FRIDAY: float = 0.08             # Weekend proximity
    W_NO_PRIOR_VISITS: float = 0.20    # No completed history

    def compute_risk_score(self, appointment: Any, patient_history: list) -> float:
        """
        Compute a calibrated no-show risk score.

        Parameters
        ----------
        appointment:
            An ORM Appointment instance with at minimum:
            - scheduled_time (datetime)
            - appointment_type (str: "new" | "follow_up")
        patient_history:
            List of historical ORM Appointment objects for the same patient.
            Used to derive past no-show ratio and completed visit count.

        Returns
        -------
        float
            Risk score clamped to [0.0, 1.0].
        """
        score = self.BASE_SCORE
        factors: dict[str, float] = {}

        scheduled_time: datetime = appointment.scheduled_time
        now = datetime.utcnow()

        # 1. Days until appointment
        days_until = (scheduled_time.date() - now.date()).days
        if days_until > 7:
            score += self.W_FAR_APPOINTMENT
            factors["far_appointment"] = self.W_FAR_APPOINTMENT
        elif days_until == 0:
            score += self.W_SAME_DAY
            factors["same_day"] = self.W_SAME_DAY

        # 2. Appointment type
        if getattr(appointment, "appointment_type", "").lower() == "new":
            score += self.W_NEW_PATIENT
            factors["new_patient"] = self.W_NEW_PATIENT

        # 3. Hour of day
        hour = scheduled_time.hour
        if hour < 9:
            score += self.W_EARLY_MORNING
            factors["early_morning"] = self.W_EARLY_MORNING
        elif 12 <= hour <= 13:
            score += self.W_LUNCH_HOUR
            factors["lunch_hour"] = self.W_LUNCH_HOUR

        # 4. Day of week (Monday=0, Sunday=6)
        weekday = scheduled_time.weekday()
        if weekday == 0:
            score += self.W_MONDAY
            factors["monday"] = self.W_MONDAY
        elif weekday == 4:
            score += self.W_FRIDAY
            factors["friday"] = self.W_FRIDAY

        # 5. Past no-show ratio (multiplicative penalty)
        if patient_history:
            past_noshows = sum(
                1 for a in patient_history
                if not _has_actual_start(a)
            )
            noshow_ratio = past_noshows / len(patient_history)
            if noshow_ratio > 0:
                multiplier = 1.0 + noshow_ratio
                score *= multiplier
                factors["past_noshow_ratio"] = round(noshow_ratio, 3)

        # 6. No prior completed visits
        completed_visits = sum(1 for a in patient_history if _has_actual_start(a))
        if completed_visits == 0:
            score += self.W_NO_PRIOR_VISITS
            factors["no_prior_visits"] = self.W_NO_PRIOR_VISITS

        # Clamp to [0, 1]
        return float(max(0.0, min(1.0, score)))

    def risk_level(self, score: float) -> str:
        """Map a continuous score to a categorical label."""
        if score < 0.33:
            return "low"
        if score < 0.67:
            return "medium"
        return "high"


# Private helpers

def _has_actual_start(appointment: Any) -> bool:
    """
    Return True if the appointment has a recorded actual_start_time
    (i.e. the patient showed up).

    Works for ORM objects (via .consultation relationship) and plain dicts.
    """
    if isinstance(appointment, dict):
        return bool(appointment.get("actual_start_time"))
    consultation = getattr(appointment, "consultation", None)
    if consultation is not None:
        return bool(getattr(consultation, "actual_start_time", None))
    # Fallback: attribute directly on appointment (denormalised)
    return bool(getattr(appointment, "actual_start_time", None))
