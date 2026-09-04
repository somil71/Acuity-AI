from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import HealthRecord, LabResult, User

router = APIRouter()

# --- Pydantic Schemas ---------------------------------------------------------

class HealthRecordCreate(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    department: str
    visit_date: datetime
    diagnosis: Optional[str] = None
    doctor_notes: Optional[str] = None
    allergies: Optional[str] = None

class LabResultCreate(BaseModel):
    test_name: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: str = "normal"  # normal, low, high, critical
    collected_at: Optional[datetime] = None

# --- Routes -------------------------------------------------------------------

@router.get("/", dependencies=[Depends(require_role(["patient"]))])
def get_my_health_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all health records for the currently authenticated patient."""
    records = (
        db.query(HealthRecord)
        .filter(HealthRecord.patient_id == current_user.id)
        .order_by(HealthRecord.visit_date.desc())
        .all()
    )
    return [
        {
            "record_id": r.record_id,
            "appointment_id": r.appointment_id,
            "patient_id": r.patient_id,
            "doctor_id": r.doctor_id,
            "department": r.department,
            "visit_date": r.visit_date,
            "diagnosis": r.diagnosis,
            "doctor_notes": r.doctor_notes,
            "allergies": r.allergies,
            "created_at": r.created_at,
            "lab_results": [
                {
                    "result_id": lr.result_id,
                    "test_name": lr.test_name,
                    "value": lr.value,
                    "unit": lr.unit,
                    "reference_range": lr.reference_range,
                    "status": lr.status,
                    "collected_at": lr.collected_at,
                }
                for lr in r.lab_results
            ],
        }
        for r in records
    ]


@router.post("/", dependencies=[Depends(require_role(["staff", "admin"]))])
def create_health_record(
    payload: HealthRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff or admin creates a health record linked to an appointment."""
    record_id = str(uuid.uuid4())
    record = HealthRecord(
        record_id=record_id,
        appointment_id=payload.appointment_id,
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        department=payload.department,
        visit_date=payload.visit_date,
        diagnosis=payload.diagnosis,
        doctor_notes=payload.doctor_notes,
        allergies=payload.allergies,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"msg": "Health record created", "record_id": record_id}


@router.get("/{record_id}")
def get_health_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single health record with nested lab results.
    Patients can only access their own records; staff/admin can access any.
    """
    record = db.query(HealthRecord).filter(HealthRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")

    if current_user.role == "patient" and record.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this record")

    labs = [
        {
            "result_id": lab.result_id,
            "test_name": lab.test_name,
            "value": lab.value,
            "unit": lab.unit,
            "reference_range": lab.reference_range,
            "status": lab.status,
            "collected_at": lab.collected_at,
        }
        for lab in record.lab_results
    ]

    return {
        "record_id": record.record_id,
        "appointment_id": record.appointment_id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "department": record.department,
        "visit_date": record.visit_date,
        "diagnosis": record.diagnosis,
        "doctor_notes": record.doctor_notes,
        "allergies": record.allergies,
        "created_at": record.created_at,
        "lab_results": labs,
    }


@router.post("/{record_id}/labs", dependencies=[Depends(require_role(["staff", "admin"]))])
def add_lab_result(
    record_id: str,
    payload: LabResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff adds a lab result to an existing health record."""
    record = db.query(HealthRecord).filter(HealthRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")

    result_id = str(uuid.uuid4())
    lab = LabResult(
        result_id=result_id,
        record_id=record_id,
        test_name=payload.test_name,
        value=payload.value,
        unit=payload.unit,
        reference_range=payload.reference_range,
        status=payload.status,
        collected_at=payload.collected_at or datetime.utcnow(),
    )
    db.add(lab)
    db.commit()
    return {"msg": "Lab result added", "result_id": result_id}
