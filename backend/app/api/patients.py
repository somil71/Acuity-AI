from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db import get_db
from app.models import schema
from app.auth import get_current_user
from app.models.schema import User
from datetime import datetime

router = APIRouter()

def generate_mock_shap_explanation(patients_ahead: int, doctor_id: str, 
                                    department: str, hour: int,
                                    visit_type: str, predicted_minutes: float) -> dict:
    factors = []
    base_value = 12.0  # global average
    
    if patients_ahead > 0:
        impact = round(patients_ahead * 2.8, 1)
        factors.append({'feature': f'{patients_ahead} Patient(s) Ahead', 
                        'impact_minutes': impact, 'direction': 'increases_wait'})
    
    # Hour of day effect
    if 11 <= hour <= 14:
        factors.append({'feature': 'Peak Hours (11am-2pm)', 
                        'impact_minutes': 4.2, 'direction': 'increases_wait'})
    elif hour < 9 or hour > 17:
        factors.append({'feature': 'Off-Peak Hours', 
                        'impact_minutes': -3.1, 'direction': 'decreases_wait'})
    
    # Visit type
    if visit_type == 'new':
        factors.append({'feature': 'New Patient Visit', 
                        'impact_minutes': 3.5, 'direction': 'increases_wait'})
    else:
        factors.append({'feature': 'Follow-up Visit', 
                        'impact_minutes': -2.0, 'direction': 'decreases_wait'})
    
    # Department effect
    dept_impacts = {'Cardiology': 2.1, 'Orthopedics': 1.5, 
                    'General Physician': -1.0, 'Pediatrics': 0.5}
    dept_impact = dept_impacts.get(department, 0)
    if dept_impact != 0:
        factors.append({'feature': f'{department} Dept Avg',
                        'impact_minutes': dept_impact,
                        'direction': 'increases_wait' if dept_impact > 0 else 'decreases_wait'})
    
    # Sort by abs impact
    factors.sort(key=lambda x: abs(x['impact_minutes']), reverse=True)
    return {
        'base_value_minutes': base_value,
        'predicted_minutes': round(predicted_minutes, 1),
        'factors': factors[:4],
        'source': 'rule_based'  # will be 'shap' once ML model loads
    }

@router.get("/{patient_id}")
def get_patient_history(patient_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Role-based access control
    if current_user.role == "patient" and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this patient's records")
        
    patient = db.query(schema.Patient).filter(schema.Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    history = []
    for appt in patient.appointments:
        if appt.consultation:
            history.append({
                "appointment_id": appt.appointment_id,
                "doctor_id": appt.doctor_id,
                "department": appt.department,
                "scheduled_time": appt.scheduled_time,
                "actual_start_time": appt.consultation.actual_start_time,
                "actual_end_time": appt.consultation.actual_end_time,
                "appointment_type": appt.appointment_type
            })
        else:
            history.append({
                "appointment_id": appt.appointment_id,
                "doctor_id": appt.doctor_id,
                "department": appt.department,
                "scheduled_time": appt.scheduled_time,
                "actual_start_time": None,
                "actual_end_time": None,
                "appointment_type": appt.appointment_type
            })
            
    def parse_dt(dt_val):
        if isinstance(dt_val, str):
            try:
                dt = datetime.fromisoformat(dt_val.replace('Z', '+00:00'))
                return dt.replace(tzinfo=None)
            except:
                dt = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S.%f")
                return dt.replace(tzinfo=None)
        if isinstance(dt_val, datetime):
            return dt_val.replace(tzinfo=None)
        return dt_val
        
    history.sort(key=lambda x: parse_dt(x['scheduled_time']), reverse=True)
    
    # Generate mock SHAP explanation for the most recent appointment (if any)
    shap_explanation = None
    if history:
        most_recent = history[0]
        dt = parse_dt(most_recent['scheduled_time'])
        shap_explanation = generate_mock_shap_explanation(
            patients_ahead=2,  # mock data
            doctor_id=most_recent['doctor_id'],
            department=most_recent['department'],
            hour=dt.hour if dt else 12,
            visit_type=most_recent['appointment_type'],
            predicted_minutes=25.0
        )
    
    return {
        "patient_id": patient.patient_id,
        "age": patient.age,
        "gender": patient.gender,
        "visit_history": history,
        "shap_explanation": shap_explanation
    }
