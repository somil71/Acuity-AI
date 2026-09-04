from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import schema
from app.services.simulation import simulator
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from app.auth import get_current_user, require_role
from app.models.schema import User
from app.logger import log_prediction, log_event

router = APIRouter()

class EmergencyLogCreate(BaseModel):
    doctor_id: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    estimated_duration: int = Field(..., gt=0)

class AppointmentCreate(BaseModel):
    doctor_id: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    appointment_type: str = Field(..., min_length=1)
    scheduled_time: datetime

@router.post("/", dependencies=[Depends(require_role(["patient"]))])
def book_appointment(appt: AppointmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appt_id = str(uuid.uuid4())
    new_appt = schema.Appointment(
        appointment_id=appt_id,
        patient_id=current_user.id,
        doctor_id=appt.doctor_id,
        department=appt.department,
        scheduled_time=appt.scheduled_time,
        appointment_type=appt.appointment_type
    )
    db.add(new_appt)
    db.commit()
    return {"msg": "Appointment booked", "appointment_id": appt_id}

@router.get("/{appointment_id}/status")
def get_appointment_status(appointment_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appt = db.query(schema.Appointment).filter(schema.Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if current_user.role == "patient" and current_user.id != appt.patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this appointment")
        
    doctor_id = appt.doctor_id
    department = appt.department
    
    ahead = db.query(schema.Appointment).filter(
        schema.Appointment.doctor_id == doctor_id,
        schema.Appointment.scheduled_time < appt.scheduled_time
    ).all()
    
    patients_ahead = []
    for a in ahead:
        prev = db.query(schema.Consultation).join(schema.Appointment).filter(
            schema.Appointment.patient_id == a.patient_id,
            schema.Appointment.doctor_id == doctor_id,
            schema.Appointment.scheduled_time < a.scheduled_time
        ).order_by(schema.Appointment.scheduled_time.desc()).first()
        
        hist = None
        if prev and prev.actual_end_time and prev.actual_start_time:
            hist = (prev.actual_end_time - prev.actual_start_time).total_seconds() / 60.0
            
        p_dict = {
            'type': a.appointment_type, 
            'scheduled_time': a.scheduled_time,
        }
        if hist is not None:
            p_dict['pat_historical_dur'] = hist
        patients_ahead.append(p_dict)
    
    emergencies = db.query(schema.EmergencyEvent).filter(
        schema.EmergencyEvent.doctor_id == doctor_id,
        schema.EmergencyEvent.resolved_time == None
    ).all()
    
    known_emergencies_remaining = [30 for _ in emergencies]
    
    today = datetime.now().date()
    roster = db.query(schema.StaffRoster).filter(
        schema.StaffRoster.doctor_id == doctor_id,
        schema.StaffRoster.date == today
    ).first()
    staff_shortage = False
    if roster and roster.support_staff_present < roster.support_staff_rostered:
        staff_shortage = True
    
    current_time = datetime.now()
    
    p10, p50, p90, explanation = simulator.simulate_patient_wait(
        target_scheduled_time=appt.scheduled_time,
        doctor_id=doctor_id,
        department=department,
        current_time=current_time,
        patients_ahead=patients_ahead,
        known_emergencies_remaining=known_emergencies_remaining,
        staff_shortage=staff_shortage
    )
    
    log_prediction(
        doctor_id=doctor_id,
        department=department,
        current_time=current_time.isoformat(),
        patients_ahead=patients_ahead,
        p10=p10.isoformat() if isinstance(p10, datetime) else str(p10),
        p50=p50.isoformat() if isinstance(p50, datetime) else str(p50),
        p90=p90.isoformat() if isinstance(p90, datetime) else str(p90),
        trigger_event="user_polling"
    )
    
    return {
        "appointment_id": appt.appointment_id,
        "scheduled_time": appt.scheduled_time,
        "predicted_p10": p10,
        "predicted_p50": p50,
        "predicted_p90": p90,
        "queue_position": len(patients_ahead),
        "doctor_id": doctor_id,
        "department": department,
        "explanation": explanation
    }

@router.post("/emergency", dependencies=[Depends(require_role(["staff", "admin"]))])
def log_emergency(log: EmergencyLogCreate, db: Session = Depends(get_db)):
    new_event = schema.EmergencyEvent(
        event_id=str(uuid.uuid4()),
        doctor_id=log.doctor_id,
        department=log.department,
        logged_time=datetime.now()
    )
    db.add(new_event)
    db.commit()
    
    log_event("emergency_injected", {"doctor_id": log.doctor_id, "department": log.department, "event_id": new_event.event_id})
    return {"message": "Emergency logged successfully", "event_id": new_event.event_id}

@router.get("/doctor/{doctor_id}/queue", dependencies=[Depends(require_role(["staff", "admin"]))])
def get_doctor_queue(doctor_id: str, db: Session = Depends(get_db)):
    appointments = db.query(schema.Appointment).filter(
        schema.Appointment.doctor_id == doctor_id
    ).order_by(schema.Appointment.scheduled_time).all()
    
    res = []
    for appt in appointments:
        res.append({
            "appointment_id": appt.appointment_id,
            "patient_id": appt.patient_id,
            "scheduled_time": appt.scheduled_time,
            "appointment_type": appt.appointment_type
        })
    return res

@router.post("/{appointment_id}/checkout", dependencies=[Depends(require_role(["staff", "admin"]))])
def checkout_appointment(appointment_id: str, db: Session = Depends(get_db)):
    appt = db.query(schema.Appointment).with_for_update().filter(schema.Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    cons = db.query(schema.Consultation).with_for_update().filter(schema.Consultation.appointment_id == appointment_id).first()
    if not cons:
        cons = schema.Consultation(appointment_id=appointment_id, actual_start_time=appt.scheduled_time, actual_end_time=datetime.now())
        db.add(cons)
    else:
        # Idempotency check
        if cons.actual_end_time is not None:
            return {"message": "Already checked out"}
        cons.actual_end_time = datetime.now()
        
    db.commit()
    log_event("checkout_completed", {"appointment_id": appointment_id, "doctor_id": appt.doctor_id})
    return {"message": "Checkout complete"}


# ─── Waitlist & Reschedule additions ─────────────────────────────────────────

from app.models.schema import Waitlist
from app.api.notifications import create_notification

class CancelRequest(BaseModel):
    pass  # no body needed

class RescheduleRequest(BaseModel):
    new_scheduled_time: datetime

class WaitlistCreate(BaseModel):
    doctor_id: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    preferred_date: datetime = None


@router.patch("/{appointment_id}/cancel", dependencies=[Depends(require_role(["patient"]))])
def cancel_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient cancels their own appointment. Creates a waitlist notification."""
    appt = db.query(schema.Appointment).filter(
        schema.Appointment.appointment_id == appointment_id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appt.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    if appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")

    appt.status = "cancelled"
    db.commit()

    # Notify the patient and any waitlisted patients for this slot
    create_notification(
        db=db,
        patient_id=current_user.id,
        type="appointment_cancelled",
        title="Appointment Cancelled",
        body=f"Your appointment on {appt.scheduled_time.strftime('%Y-%m-%d %H:%M')} has been cancelled.",
        appointment_id=appointment_id,
    )

    # Notify waitlisted patients for the same doctor / department
    waitlisted = (
        db.query(Waitlist)
        .filter(
            Waitlist.doctor_id == appt.doctor_id,
            Waitlist.department == appt.department,
            Waitlist.status == "waiting",
        )
        .all()
    )
    for entry in waitlisted:
        create_notification(
            db=db,
            patient_id=entry.patient_id,
            type="eta_update",
            title="Appointment Slot Available",
            body=f"A slot has opened with Dr. {appt.doctor_id} in {appt.department}. Please book soon.",
            appointment_id=None,
        )
        entry.status = "notified"
    db.commit()

    return {"msg": "Appointment cancelled", "appointment_id": appointment_id}


@router.patch("/{appointment_id}/reschedule", dependencies=[Depends(require_role(["patient"]))])
def reschedule_appointment(
    appointment_id: str,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient reschedules their appointment to a future time."""
    if payload.new_scheduled_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="New scheduled time must be in the future")

    appt = db.query(schema.Appointment).filter(
        schema.Appointment.appointment_id == appointment_id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appt.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your appointment")

    if appt.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot reschedule a {appt.status} appointment")

    appt.scheduled_time = payload.new_scheduled_time
    db.commit()

    create_notification(
        db=db,
        patient_id=current_user.id,
        type="appointment_reminder",
        title="Appointment Rescheduled",
        body=f"Your appointment has been rescheduled to {payload.new_scheduled_time.strftime('%Y-%m-%d %H:%M')}.",
        appointment_id=appointment_id,
    )

    return {
        "msg": "Appointment rescheduled",
        "appointment_id": appointment_id,
        "new_scheduled_time": payload.new_scheduled_time,
    }


@router.post("/waitlist", dependencies=[Depends(require_role(["patient"]))])
def join_waitlist(
    payload: WaitlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient joins the waitlist for a doctor/department."""
    waitlist_id = str(uuid.uuid4())
    entry = Waitlist(
        waitlist_id=waitlist_id,
        patient_id=current_user.id,
        doctor_id=payload.doctor_id,
        department=payload.department,
        preferred_date=payload.preferred_date,
        created_at=datetime.utcnow(),
        status="waiting",
    )
    db.add(entry)
    db.commit()
    return {"msg": "Added to waitlist", "waitlist_id": waitlist_id}


@router.get("/waitlist/my", dependencies=[Depends(require_role(["patient"]))])
def get_my_waitlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient retrieves all their own waitlist entries."""
    entries = (
        db.query(Waitlist)
        .filter(Waitlist.patient_id == current_user.id)
        .order_by(Waitlist.created_at.desc())
        .all()
    )
    return [
        {
            "waitlist_id": e.waitlist_id,
            "doctor_id": e.doctor_id,
            "department": e.department,
            "preferred_date": e.preferred_date,
            "status": e.status,
            "created_at": e.created_at,
        }
        for e in entries
    ]
