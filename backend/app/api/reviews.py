from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import Review, Appointment, User

router = APIRouter()

# --- Pydantic Schemas ---------------------------------------------------------

class ReviewCreate(BaseModel):
    appointment_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    wait_time_rating: Optional[int] = Field(default=None, ge=1, le=5)

# --- Routes -------------------------------------------------------------------

@router.post("/", dependencies=[Depends(require_role(["patient"]))])
def submit_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient submits a review for a completed appointment.
    - Appointment must be 'completed'.
    - No duplicate review per appointment.
    - Rating must be 1-5.
    """
    appointment = (
        db.query(Appointment)
        .filter(Appointment.appointment_id == payload.appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    # Check appointment is completed via consultation (not status field which may be null)
    if not appointment.consultation or not appointment.consultation.actual_end_time:
        raise HTTPException(status_code=400, detail="Can only review completed appointments")

    existing = (
        db.query(Review)
        .filter(Review.appointment_id == payload.appointment_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Review already submitted for this appointment")

    review_id = str(uuid.uuid4())
    review = Review(
        review_id=review_id,
        appointment_id=payload.appointment_id,
        patient_id=current_user.id,
        doctor_id=appointment.doctor_id,
        rating=payload.rating,
        comment=payload.comment,
        wait_time_rating=payload.wait_time_rating,
        created_at=datetime.utcnow(),
    )
    db.add(review)
    db.commit()
    return {"msg": "Review submitted", "review_id": review_id}


@router.get("/doctor/{doctor_id}")
def get_doctor_reviews(
    doctor_id: str,
    db: Session = Depends(get_db),
):
    """Public endpoint: return average rating and all reviews for a doctor."""
    reviews = (
        db.query(Review)
        .filter(Review.doctor_id == doctor_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    if not reviews:
        return {"doctor_id": doctor_id, "average_rating": None, "total_reviews": 0, "reviews": []}

    avg_rating = sum(r.rating for r in reviews) / len(reviews)

    return {
        "doctor_id": doctor_id,
        "average_rating": round(avg_rating, 2),
        "total_reviews": len(reviews),
        "reviews": [
            {
                "review_id": r.review_id,
                "appointment_id": r.appointment_id,
                "patient_id": r.patient_id,
                "rating": r.rating,
                "comment": r.comment,
                "wait_time_rating": r.wait_time_rating,
                "created_at": r.created_at,
            }
            for r in reviews
        ],
    }


@router.get("/my", dependencies=[Depends(require_role(["patient"]))])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return {pending_visits: [...], submitted_reviews: [...]} for the current patient.
    pending_visits = completed appointments (have a consultation) with no review yet.
    submitted_reviews = all submitted reviews.
    """
    from app.models.schema import Consultation
    # All appointments that have a completed consultation
    completed_appts = (
        db.query(Appointment)
        .join(Consultation, Appointment.appointment_id == Consultation.appointment_id)
        .filter(
            Appointment.patient_id == current_user.id,
            Consultation.actual_end_time != None,
        )
        .all()
    )

    # Reviewed appointment IDs
    reviewed_ids = {
        r.appointment_id
        for r in db.query(Review.appointment_id).filter(Review.patient_id == current_user.id).all()
    }

    pending_visits = [
        {
            "appointment_id": a.appointment_id,
            "doctor_id": a.doctor_id,
            "department": a.department,
            "scheduled_time": a.scheduled_time,
            "appointment_type": a.appointment_type,
        }
        for a in completed_appts
        if a.appointment_id not in reviewed_ids
    ]

    submitted_reviews = [
        {
            "review_id": r.review_id,
            "appointment_id": r.appointment_id,
            "doctor_id": r.doctor_id,
            "rating": r.rating,
            "comment": r.comment,
            "wait_time_rating": r.wait_time_rating,
            "created_at": r.created_at,
        }
        for r in (
            db.query(Review)
            .filter(Review.patient_id == current_user.id)
            .order_by(Review.created_at.desc())
            .all()
        )
    ]

    return {"pending_visits": pending_visits, "submitted_reviews": submitted_reviews}
