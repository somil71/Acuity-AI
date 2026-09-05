import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import uuid

def generate_synthetic_data(num_days=30, output_dir='data', scenario_mode=False):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    departments = {
        'General Physician': {'base_dur': 10, 'var': 2},
        'Cardiology': {'base_dur': 25, 'var': 10},
        'Orthopedics': {'base_dur': 20, 'var': 5},
        'Pediatrics': {'base_dur': 15, 'var': 5}
    }
    
    # 2 doctors per department
    doctors = []
    for dept in departments.keys():
        for i in range(2):
            doc_id = f"DOC_{dept[:3].upper()}_{i+1}"
            doctors.append({'doctor_id': doc_id, 'department': dept, 'offset': random.uniform(-2, 3)})

    # Generate Patients
    patients = []
    for i in range(1000):
        patients.append({
            'patient_id': f"PAT_{i+1}",
            'age': random.randint(1, 90),
            'gender': random.choice(['M', 'F', 'O'])
        })
    pd.DataFrame(patients).to_csv(f"{output_dir}/patients.csv", index=False)

    appointments = []
    consultations = []
    emergency_events = []
    staff_roster = []
    
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=num_days)
    
    for day_offset in range(num_days):
        current_date = start_date + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5
        if is_weekend: continue
        
        # Staff roster per doctor
        for doc in doctors:
            shift_start = current_date.replace(hour=9, minute=0)
            shift_end = current_date.replace(hour=17, minute=0)
            rostered = random.randint(2, 4)
            present = rostered if random.random() > 0.1 else rostered - 1
            
            staff_roster.append({
                'date': current_date.strftime("%Y-%m-%d"),
                'doctor_id': doc['doctor_id'],
                'shift_start': shift_start,
                'shift_end': shift_end,
                'support_staff_present': present,
                'support_staff_rostered': rostered
            })
            
            # Daily load
            num_appointments = random.randint(10, 20)
            current_time = shift_start
            
            # Poisson emergencies
            emergencies_today = np.random.poisson(0.5 if doc['department'] == 'General Physician' else 0.2)
            if scenario_mode and day_offset == num_days - 1 and doc['doctor_id'] == 'DOC_CAR_1':
                emergencies_today = 3 # Inject disruption for demo
                
            emergency_times = sorted([shift_start + timedelta(hours=random.uniform(1, 7)) for _ in range(emergencies_today)])
            
            for e_time in emergency_times:
                resolved_time = e_time + timedelta(minutes=random.uniform(20, 60))
                emergency_events.append({
                    'event_id': str(uuid.uuid4()),
                    'doctor_id': doc['doctor_id'],
                    'department': doc['department'],
                    'logged_time': e_time,
                    'resolved_time': resolved_time
                })
            
            for i in range(num_appointments):
                appt_type = random.choice(['new', 'follow_up'])
                pat = random.choice(patients)
                
                # Model the duration
                base_d = departments[doc['department']]['base_dur']
                var_d = departments[doc['department']]['var']
                actual_duration = max(5, np.random.normal(base_d, var_d) + doc['offset'])
                if appt_type == 'follow_up':
                    actual_duration *= 0.7 # Follow-ups are shorter
                
                # Penalty for understaffing
                if present < rostered:
                    actual_duration *= 1.2
                    
                scheduled_time = shift_start + timedelta(minutes=i * base_d)
                
                # Check if an emergency happened before this consult started
                delay = 0
                for e_time, r_time in zip(emergency_times, [e['resolved_time'] for e in emergency_events[-emergencies_today:] if emergencies_today > 0]):
                    if current_time < r_time and current_time >= e_time:
                        delay += (r_time - current_time).total_seconds() / 60.0
                        current_time = r_time
                
                # Queue drift
                actual_start_time = max(scheduled_time, current_time)
                actual_end_time = actual_start_time + timedelta(minutes=actual_duration)
                
                appt_id = str(uuid.uuid4())
                appointments.append({
                    'appointment_id': appt_id,
                    'patient_id': pat['patient_id'],
                    'doctor_id': doc['doctor_id'],
                    'department': doc['department'],
                    'scheduled_time': scheduled_time,
                    'appointment_type': appt_type
                })
                
                consultations.append({
                    'appointment_id': appt_id,
                    'actual_start_time': actual_start_time,
                    'actual_end_time': actual_end_time
                })
                
                current_time = actual_end_time

    pd.DataFrame(appointments).to_csv(f"{output_dir}/appointments.csv", index=False)
    pd.DataFrame(consultations).to_csv(f"{output_dir}/consultations.csv", index=False)
    pd.DataFrame(emergency_events).to_csv(f"{output_dir}/emergency_events.csv", index=False)
    pd.DataFrame(staff_roster).to_csv(f"{output_dir}/staff_roster.csv", index=False)

    print(f"Generated synthetic data in {output_dir}")

if __name__ == "__main__":
    generate_synthetic_data(scenario_mode=True)
