from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.schema import Appointment, Consultation
from datetime import datetime

router = APIRouter()

DEPARTMENTS = ['Cardiology', 'General Physician', 'Orthopedics', 'Pediatrics']

def compute_bottlenecks(db: Session, department: str = None):
    now = datetime.utcnow()
    
    doc_query = db.query(Appointment).join(Consultation, Appointment.appointment_id == Consultation.appointment_id).filter(
        Consultation.actual_start_time != None,
        Consultation.actual_end_time != None
    )
    
    if department:
        doc_query = doc_query.filter(Appointment.department == department)
        
    past_appts = doc_query.all()
    
    doc_stats = {}
    for appt in past_appts:
        doc = appt.doctor_id
        if doc not in doc_stats:
            doc_stats[doc] = {"durations": [], "dept": appt.department}
        
        dur = (appt.consultation.actual_end_time - appt.consultation.actual_start_time).total_seconds() / 60.0
        if dur > 0:
            doc_stats[doc]["durations"].append(dur)
            
    doctor_bottlenecks = []
    for doc, data in doc_stats.items():
        if not data["durations"]: continue
        avg_actual_duration = sum(data["durations"]) / len(data["durations"])
        avg_scheduled_slot = 20.0
        overrun_ratio = avg_actual_duration / avg_scheduled_slot
        
        queue_behind = db.query(Appointment).filter(
            Appointment.doctor_id == doc,
            Appointment.scheduled_time <= now,
            Appointment.appointment_id.not_in(
                db.query(Consultation.appointment_id).filter(Consultation.actual_start_time != None)
            )
        ).count()
        
        if overrun_ratio > 1.3 or queue_behind > 3:
            doctor_bottlenecks.append({
                "doctor_id": doc,
                "department": data["dept"],
                "overrun_ratio": round(overrun_ratio, 2),
                "queue_behind": queue_behind,
                "avg_actual_minutes": round(avg_actual_duration, 1)
            })
            
    department_bottlenecks = []
    depts = [department] if department else DEPARTMENTS
    for dept in depts:
        waiting_appts = db.query(Appointment).filter(
            Appointment.department == dept,
            Appointment.scheduled_time <= now,
            Appointment.appointment_id.not_in(
                db.query(Consultation.appointment_id).filter(Consultation.actual_start_time != None)
            )
        ).all()
        
        patients_waiting = len(waiting_appts)
        wait_breaches = []
        for a in waiting_appts:
            dt = a.scheduled_time.replace(tzinfo=None) if hasattr(a.scheduled_time, 'replace') else a.scheduled_time
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00')).replace(tzinfo=None)
            breach = (now - dt).total_seconds() / 60.0
            wait_breaches.append(breach)
            
        avg_wait_breach = sum(wait_breaches) / len(wait_breaches) if wait_breaches else 0
        
        if patients_waiting > 5:
            severity = "high"
        elif patients_waiting >= 3:
            severity = "medium"
        else:
            severity = "low"
            
        if severity in ["medium", "high"] or avg_wait_breach > 15:
            department_bottlenecks.append({
                "department": dept,
                "patients_waiting": patients_waiting,
                "avg_wait_breach_minutes": round(avg_wait_breach, 1),
                "severity": severity
            })
            
    return {
        "computed_at": now.isoformat(),
        "department_bottlenecks": department_bottlenecks,
        "doctor_bottlenecks": doctor_bottlenecks,
        "total_alerts": len(department_bottlenecks) + len(doctor_bottlenecks)
    }

@router.get("/now")
def get_bottlenecks_now(db: Session = Depends(get_db)):
    return compute_bottlenecks(db)

@router.get("/{department}")
def get_bottlenecks_dept(department: str, db: Session = Depends(get_db)):
    return compute_bottlenecks(db, department)
