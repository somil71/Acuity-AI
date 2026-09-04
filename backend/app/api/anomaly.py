from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth import require_role
from app.services.anomaly import QueueAnomalyDetector

router = APIRouter()


@router.get("/check", dependencies=[Depends(require_role(["staff", "admin"]))])
def check_all_doctors(db: Session = Depends(get_db)):
    """
    Run the queue anomaly detector across all doctors who have active
    appointments today.

    Access: staff and admin only.

    Returns
    -------
    List of anomaly result objects, one per active doctor.
    Each object contains:
        doctor_id           : str
        is_anomalous        : bool
        z_score             : float | null
        current_depth       : int
        baseline_mean       : float | null
        delay_estimate_mins : float
        reason              : str | null  -- "insufficient_history" when applicable
    """
    detector = QueueAnomalyDetector(db)
    results = detector.run_check_all_doctors()
    return {"anomalies_checked": len(results), "results": results}


@router.get("/check/{doctor_id}", dependencies=[Depends(require_role(["staff", "admin"]))])
def check_single_doctor(doctor_id: str, db: Session = Depends(get_db)):
    """
    Run the queue anomaly detector for a single doctor.

    Access: staff and admin only.

    Returns
    -------
    Single anomaly result object containing:
        doctor_id           : str
        is_anomalous        : bool
        z_score             : float | null
        current_depth       : int
        baseline_mean       : float | null
        delay_estimate_mins : float
        reason              : str | null  -- "insufficient_history" when applicable
    """
    detector = QueueAnomalyDetector(db)
    result = detector.check_anomaly(doctor_id)
    return result
