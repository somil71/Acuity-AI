from sqlalchemy.orm import Session
from app.models.schema import Appointment, Consultation

def get_dept_queue_health(db: Session, department: str) -> dict:
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    sixty_min_ago = now - timedelta(minutes=60)
    
    # Active = started but not ended
    active = db.query(Appointment).join(Consultation, Appointment.appointment_id == Consultation.appointment_id).filter(
        Appointment.department == department,
        Consultation.actual_start_time != None,
        Consultation.actual_end_time == None
    ).count()
    
    arrivals_60m = db.query(Appointment).filter(
        Appointment.department == department,
        Appointment.scheduled_time >= sixty_min_ago,
        Appointment.scheduled_time <= now
    ).count()
    
    emergency_count = db.query(Appointment).filter(
        Appointment.department == department,
        Appointment.appointment_type == 'emergency',
        Appointment.scheduled_time >= sixty_min_ago
    ).count()
    
    high_acuity_ratio = emergency_count / max(arrivals_60m, 1)
    
    census_pressure = min(1.0, active / 15.0)  # capacity_reference=15 per dept
    arrival_velocity = min(1.0, arrivals_60m / 8.0)
    acuity_load = min(1.0, high_acuity_ratio / 0.20)
    raw = 0.50 * census_pressure + 0.30 * arrival_velocity + 0.20 * acuity_load
    score = round(min(100.0, raw * 100), 1)
    
    if score < 30: state = 'HEALTHY'
    elif score < 55: state = 'MODERATE'  
    elif score < 75: state = 'BUSY'
    else: state = 'CRITICAL'
    
    return {
        'department': department,
        'score': score,
        'state': state,
        'active_count': active,
        'arrivals_60m': arrivals_60m,
        'high_acuity_ratio': round(high_acuity_ratio, 3),
        'components': {
            'census_pressure': round(census_pressure * 100, 1),
            'arrival_velocity': round(arrival_velocity * 100, 1),
            'acuity_load': round(acuity_load * 100, 1)
        },
        'dominant_factor': max(
            ['census','arrivals','acuity'],
            key=lambda k: {'census':census_pressure,'arrivals':arrival_velocity,'acuity':acuity_load}[k]
        ),
        'computed_at': now.isoformat()
    }
