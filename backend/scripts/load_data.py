import pandas as pd
from app.db import SessionLocal, engine, Base
from app.models import schema
import sys
import os

def load_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    
    # Patients
    patients = pd.read_csv(f"{data_dir}/patients.csv")
    for _, row in patients.iterrows():
        p = schema.Patient(
            patient_id=row['patient_id'],
            age=row['age'],
            gender=row['gender']
        )
        db.merge(p)
        
    # Appointments
    appointments = pd.read_csv(f"{data_dir}/appointments.csv")
    for _, row in appointments.iterrows():
        a = schema.Appointment(
            appointment_id=row['appointment_id'],
            patient_id=row['patient_id'],
            doctor_id=row['doctor_id'],
            department=row['department'],
            scheduled_time=pd.to_datetime(row['scheduled_time']),
            appointment_type=row['appointment_type']
        )
        db.merge(a)
        
    # Consultations
    consultations = pd.read_csv(f"{data_dir}/consultations.csv")
    for _, row in consultations.iterrows():
        c = schema.Consultation(
            appointment_id=row['appointment_id'],
            actual_start_time=pd.to_datetime(row['actual_start_time']),
            actual_end_time=pd.to_datetime(row['actual_end_time'])
        )
        db.merge(c)
        
    # Emergency Events
    emergencies = pd.read_csv(f"{data_dir}/emergency_events.csv")
    for _, row in emergencies.iterrows():
        e = schema.EmergencyEvent(
            event_id=row['event_id'],
            doctor_id=row['doctor_id'],
            department=row['department'],
            logged_time=pd.to_datetime(row['logged_time']),
            resolved_time=pd.to_datetime(row['resolved_time'])
        )
        db.merge(e)
        
    db.commit()
    print("Data loaded into database successfully!")
    db.close()

if __name__ == "__main__":
    # Ensure correct working directory context
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_data()
