"""
anomaly.py - Queue Anomaly Detector
=====================================
Detects unusual queue depth for a doctor at a given weekday+hour using
Z-score comparison against a 90-day rolling baseline derived from
Consultation + Appointment history.

Z-score threshold: 2.0 (flag anomaly if current depth deviates by more than
two standard deviations above the historical mean for that slot).

Delay estimate formula:
    delay_estimate_mins = (current_depth - baseline_mean) * avg_consult_duration
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.schema import Appointment, Consultation

# Constants
_BASELINE_DAYS: int = 90
_ANOMALY_Z_THRESHOLD: float = 2.0
_MIN_DATA_POINTS: int = 5
_DEFAULT_CONSULT_DURATION: float = 15.0  # minutes fallback


class QueueAnomalyDetector:
    """
    Detect anomalous queue depths for doctors using Z-score analysis.

    Parameters
    ----------
    db_session:
        An active SQLAlchemy Session.
    """

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    # Public API

    def get_baseline(self, doctor_id: str, weekday: int, hour: int) -> dict:
        """
        Compute historical queue-depth statistics for a given doctor/weekday/hour
        slot using the past 90 days of Consultation+Appointment data.

        Queue depth at a historical slot is the count of non-completed
        appointments scheduled for that doctor within the same calendar hour.

        Returns
        -------
        dict with keys:
            mean_queue_depth : float
            std_queue_depth  : float
            data_points      : int
        """
        cutoff = datetime.utcnow() - timedelta(days=_BASELINE_DAYS)

        historical_appts = (
            self.db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.scheduled_time >= cutoff,
            )
            .all()
        )

        # Group into (date) sessions matching the requested weekday+hour slot
        sessions: dict[str, list] = {}
        for appt in historical_appts:
            if appt.scheduled_time.weekday() != weekday:
                continue
            if appt.scheduled_time.hour != hour:
                continue
            day_key = appt.scheduled_time.strftime("%Y-%m-%d")
            sessions.setdefault(day_key, []).append(appt)

        slot_depths: list[int] = []
        for day_appts in sessions.values():
            depth = sum(1 for a in day_appts if not _appt_completed(a))
            slot_depths.append(depth)

        n = len(slot_depths)
        if n < _MIN_DATA_POINTS:
            return {"mean_queue_depth": 0.0, "std_queue_depth": 0.0, "data_points": n}

        mean = sum(slot_depths) / n
        variance = sum((d - mean) ** 2 for d in slot_depths) / n
        std = math.sqrt(variance)

        return {"mean_queue_depth": mean, "std_queue_depth": std, "data_points": n}

    def current_queue_depth(self, doctor_id: str) -> int:
        """
        Count of non-completed appointments for this doctor today.
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        return (
            self.db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.scheduled_time >= today_start,
                Appointment.scheduled_time < today_end,
                Appointment.status.notin_(["completed", "cancelled", "no_show"]),
            )
            .count()
        )

    def _avg_consult_duration(self, doctor_id: str) -> float:
        """
        Return the average completed consultation duration (minutes) for this
        doctor over the past 90 days. Falls back to the global default if
        there is insufficient history.
        """
        cutoff = datetime.utcnow() - timedelta(days=_BASELINE_DAYS)

        rows = (
            self.db.query(Consultation)
            .join(Appointment, Appointment.appointment_id == Consultation.appointment_id)
            .filter(
                Appointment.doctor_id == doctor_id,
                Consultation.actual_start_time.isnot(None),
                Consultation.actual_end_time.isnot(None),
                Appointment.scheduled_time >= cutoff,
            )
            .all()
        )

        if not rows:
            return _DEFAULT_CONSULT_DURATION

        durations = [
            (c.actual_end_time - c.actual_start_time).total_seconds() / 60.0
            for c in rows
            if c.actual_end_time and c.actual_start_time
        ]
        if not durations:
            return _DEFAULT_CONSULT_DURATION

        return sum(durations) / len(durations)

    def check_anomaly(self, doctor_id: str) -> dict:
        """
        Run anomaly detection for a single doctor at the current moment.

        Returns
        -------
        dict with keys:
            doctor_id           : str
            is_anomalous        : bool
            z_score             : float | None
            current_depth       : int
            baseline_mean       : float | None
            delay_estimate_mins : float
            reason              : str | None  -- set only when result is inconclusive
        """
        now = datetime.utcnow()
        weekday = now.weekday()
        hour = now.hour

        baseline = self.get_baseline(doctor_id, weekday, hour)

        if baseline["data_points"] < _MIN_DATA_POINTS:
            return {
                "doctor_id": doctor_id,
                "is_anomalous": False,
                "z_score": None,
                "current_depth": self.current_queue_depth(doctor_id),
                "baseline_mean": None,
                "delay_estimate_mins": 0.0,
                "reason": "insufficient_history",
            }

        current_depth = self.current_queue_depth(doctor_id)
        mean = baseline["mean_queue_depth"]
        std = baseline["std_queue_depth"]

        # Avoid division by zero when all historical depths were identical
        if std == 0.0:
            z_score = 0.0 if current_depth == mean else float("inf")
        else:
            z_score = (current_depth - mean) / std

        is_anomalous = z_score > _ANOMALY_Z_THRESHOLD

        avg_duration = self._avg_consult_duration(doctor_id)
        excess = max(0.0, current_depth - mean)
        delay_estimate_mins = excess * avg_duration if is_anomalous else 0.0

        return {
            "doctor_id": doctor_id,
            "is_anomalous": is_anomalous,
            "z_score": round(z_score, 3),
            "current_depth": current_depth,
            "baseline_mean": round(mean, 2),
            "delay_estimate_mins": round(delay_estimate_mins, 1),
            "reason": None,
        }

    def run_check_all_doctors(self, db: Optional[Session] = None) -> list:
        """
        Check anomaly status for every doctor who has at least one
        non-completed appointment today.

        Parameters
        ----------
        db:
            Optional session override. Useful when called from a background
            task with its own session.

        Returns
        -------
        list of anomaly result dicts (one per active doctor today).
        """
        session = db if db is not None else self.db

        # Temporarily swap session if needed
        original_db = self.db
        if db is not None:
            self.db = db

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        active_doctor_ids = (
            session.query(Appointment.doctor_id)
            .filter(
                Appointment.scheduled_time >= today_start,
                Appointment.scheduled_time < today_end,
                Appointment.status.notin_(["completed", "cancelled", "no_show"]),
            )
            .distinct()
            .all()
        )

        results = []
        for (doctor_id,) in active_doctor_ids:
            result = self.check_anomaly(doctor_id)
            results.append(result)

        # Restore original session
        self.db = original_db
        return results


# Private helpers

def _appt_completed(appointment: Appointment) -> bool:
    """Return True if the appointment is in a terminal state."""
    return getattr(appointment, "status", "") in ("completed", "cancelled", "no_show")
