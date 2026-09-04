from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import Prescription, User

router = APIRouter()

# --- Pydantic Schemas ---------------------------------------------------------

class PrescriptionCreate(BaseModel):
    appointment_id: str
    patient_id: str
    drug_name: str = Field(..., min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration_days: Optional[int] = None
    instructions: Optional[str] = None
    valid_until: Optional[datetime] = None

class RefillStatusUpdate(BaseModel):
    refill_status: str = Field(..., pattern="^(none|requested|approved|dispensed)$")

# --- Routes -------------------------------------------------------------------

@router.get("/", dependencies=[Depends(require_role(["patient"]))])
def list_my_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all prescriptions for the currently authenticated patient."""
    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.patient_id == current_user.id)
        .order_by(Prescription.prescribed_at.desc())
        .all()
    )
    return [
        {
            "prescription_id": p.prescription_id,
            "appointment_id": p.appointment_id,
            "patient_id": p.patient_id,
            "prescribed_by": p.prescribed_by,
            "drug_name": p.drug_name,
            "dosage": p.dosage,
            "frequency": p.frequency,
            "duration_days": p.duration_days,
            "instructions": p.instructions,
            "refill_status": p.refill_status,
            "prescribed_at": p.prescribed_at,
            "valid_until": p.valid_until,
        }
        for p in prescriptions
    ]


@router.post("/", dependencies=[Depends(require_role(["staff", "admin"]))])
def create_prescription(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff or admin creates a new prescription for a patient."""
    prescription_id = str(uuid.uuid4())
    prescription = Prescription(
        prescription_id=prescription_id,
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
        prescribed_by=current_user.id,
        drug_name=payload.drug_name,
        dosage=payload.dosage,
        frequency=payload.frequency,
        duration_days=payload.duration_days,
        instructions=payload.instructions,
        refill_status="none",
        prescribed_at=datetime.utcnow(),
        valid_until=payload.valid_until,
    )
    db.add(prescription)
    db.commit()
    return {"msg": "Prescription created", "prescription_id": prescription_id}


@router.post("/{prescription_id}/refill", dependencies=[Depends(require_role(["patient"]))])
def request_refill(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient requests a refill for one of their prescriptions."""
    prescription = (
        db.query(Prescription)
        .filter(Prescription.prescription_id == prescription_id)
        .first()
    )
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    if prescription.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refill this prescription")

    if prescription.refill_status == "requested":
        raise HTTPException(status_code=400, detail="Refill already requested")

    prescription.refill_status = "requested"
    db.commit()
    return {
        "msg": "Refill requested",
        "prescription_id": prescription_id,
        "refill_status": "requested",
    }


@router.patch("/{prescription_id}/status", dependencies=[Depends(require_role(["staff", "admin"]))])
def update_refill_status(
    prescription_id: str,
    payload: RefillStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff approves or marks a refill as dispensed."""
    prescription = (
        db.query(Prescription)
        .filter(Prescription.prescription_id == prescription_id)
        .first()
    )
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")

    prescription.refill_status = payload.refill_status
    db.commit()
    return {
        "msg": "Refill status updated",
        "prescription_id": prescription_id,
        "refill_status": payload.refill_status,
    }
