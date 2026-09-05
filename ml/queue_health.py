from datetime import datetime, timedelta
from sqlalchemy import func

def calculate_queue_health(active_census, arrivals_60m, high_acuity_ratio,
                           capacity_reference=50, baseline_arrival_rate=8.0):
    census_pressure = min(1.0, active_census / capacity_reference)
    arrival_velocity = min(1.0, arrivals_60m / (baseline_arrival_rate * 1.0))
    acuity_load = min(1.0, high_acuity_ratio / 0.25)
    
    raw = 0.50 * census_pressure + 0.30 * arrival_velocity + 0.20 * acuity_load
    score = round(min(100.0, raw * 100), 1)
    
    if score < 30: state = 'HEALTHY'
    elif score < 55: state = 'MODERATE'
    elif score < 75: state = 'BUSY'
    else: state = 'CRITICAL'
    
    factors = {'census': census_pressure, 'arrivals': arrival_velocity, 'acuity': acuity_load}
    dominant = max(factors, key=factors.get)
    
    return {
        'score': score,
        'state': state,
        'components': {
            'census_pressure': round(census_pressure * 100, 1),
            'arrival_velocity': round(arrival_velocity * 100, 1),
            'acuity_load': round(acuity_load * 100, 1)
        },
        'dominant_factor': dominant,
        'capacity_reference': capacity_reference
    }

def calculate_dept_health_from_db(db_session, department):
    # This imports the models from schema.py
    # sys.path hacking might be needed if run directly, but this runs in app context
    import sys
    import os
    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'app'))
    if backend_path not in sys.path:
        sys.path.append(backend_path)
        
    try:
        from models.schema import Appointment, Consultation
        
        now = datetime.utcnow()
        sixty_mins_ago = now - timedelta(minutes=60)
        
        # Arrivals in last 60m: Consultations where actual_start_time >= sixty_mins_ago
        arrivals = db_session.query(Consultation).join(Appointment).filter(
            Appointment.department == department,
            Consultation.actual_start_time >= sixty_mins_ago,
            Consultation.actual_start_time <= now
        ).count()
        
        # Active census: Consultations started but not ended, or ended in future (if simulated)
        active_census = db_session.query(Consultation).join(Appointment).filter(
            Appointment.department == department,
            Consultation.actual_start_time <= now,
            (Consultation.actual_end_time == None) | (Consultation.actual_end_time > now)
        ).count()
        
        # High acuity ratio - dummy for now as no acuity in db schema currently
        high_acuity_ratio = 0.15 
        
        return calculate_queue_health(active_census, arrivals, high_acuity_ratio)
    except Exception as e:
        return {"error": str(e)}
