from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth import require_role
from app.models.schema import Appointment, Consultation
from app.services.noshowml import NoShowPredictor

router = APIRouter()

_predictor = NoShowPredictor()


@router.get("/{appointment_id}/noshowrisk", dependencies=[Depends(require_role(["staff", "admin"]))])
def get_noshow_risk(appointment_id: str, db: Session = Depends(get_db)):
    """
    Compute and persist the no-show risk score for a given appointment.

    Access: staff and admin only.

    Returns
    -------
    JSON with:
        appointment_id : str
        risk_score     : float  (0.0 - 1.0)
        risk_level     : "low" | "medium" | "high"
        factors        : dict   (human-readable factor breakdown)
    """
    # Fetch the target appointment
    appointment = (
        db.query(Appointment)
        .filter(Appointment.appointment_id == appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Fetch complete appointment history for the patient (excluding current)
    patient_history = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == appointment.patient_id,
            Appointment.appointment_id != appointment_id,
        )
        .all()
    )

    # Compute risk score
    risk_score = _predictor.compute_risk_score(appointment, patient_history)
    risk_level = _predictor.risk_level(risk_score)

    # Persist the score back to the DB
    appointment.noshowrisk_score = risk_score
    db.commit()

    # Build a lightweight factor summary for the API consumer
    factors = _build_factor_summary(appointment, patient_history)

    return {
        "appointment_id": appointment_id,
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level,
        "factors": factors,
    }


# Private helper

def _build_factor_summary(appointment: Appointment, patient_history: list) -> dict:
    """
    Return a human-readable dict describing which risk factors were triggered.
    Mirrors the logic in NoShowPredictor so the API consumer can display details.
    """
    from datetime import datetime

    now = datetime.utcnow()
    scheduled = appointment.scheduled_time
    days_until = (scheduled.date() - now.date()).days
    hour = scheduled.hour
    weekday = scheduled.weekday()

    completed_visits = sum(
        1 for a in patient_history
        if _has_actual_start(a)
    )
    past_noshows = sum(
        1 for a in patient_history
        if not _has_actual_start(a)
    )
    noshow_ratio = (
        round(past_noshows / len(patient_history), 3) if patient_history else 0.0
    )

    return {
        "days_until_appointment": days_until,
        "appointment_type": appointment.appointment_type,
        "hour_of_day": hour,
        "day_of_week": scheduled.strftime("%A"),
        "past_total_appointments": len(patient_history),
        "past_completed_visits": completed_visits,
        "past_noshows": past_noshows,
        "past_noshow_ratio": noshow_ratio,
        "far_appointment_flag": days_until > 7,
        "same_day_flag": days_until == 0,
        "new_patient_flag": getattr(appointment, "appointment_type", "") == "new",
        "early_morning_flag": hour < 9,
        "lunch_hour_flag": 12 <= hour <= 13,
        "monday_flag": weekday == 0,
        "friday_flag": weekday == 4,
        "no_prior_visits_flag": completed_visits == 0,
    }


def _has_actual_start(appointment: Appointment) -> bool:
    """Return True if the appointment was attended (has an actual_start_time)."""
    consultation = getattr(appointment, "consultation", None)
    if consultation is not None:
        return bool(getattr(consultation, "actual_start_time", None))
    return bool(getattr(appointment, "actual_start_time", None))
