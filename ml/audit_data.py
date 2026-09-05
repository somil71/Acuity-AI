import pandas as pd
import numpy as np

def audit_synthetic_data(data_dir='data'):
    print("--- Component 1: Synthetic Data Generator Audit ---")
    try:
        appts = pd.read_csv(f"{data_dir}/appointments.csv")
        cons = pd.read_csv(f"{data_dir}/consultations.csv")
        em = pd.read_csv(f"{data_dir}/emergency_events.csv")
        staff = pd.read_csv(f"{data_dir}/staff_roster.csv")
        
        df = pd.merge(appts, cons, on='appointment_id')
        df['actual_start_time'] = pd.to_datetime(df['actual_start_time'])
        df['actual_end_time'] = pd.to_datetime(df['actual_end_time'])
        df['duration'] = (df['actual_end_time'] - df['actual_start_time']).dt.total_seconds() / 60.0
        
        # 1. Departments differ
        dept_stats = df.groupby('department')['duration'].agg(['mean', 'var', 'count'])
        print("\nDepartment Duration Stats:")
        print(dept_stats)
        
        # 2. Doctors differ
        doc_stats = df.groupby(['department', 'doctor_id'])['duration'].agg(['mean', 'var'])
        print("\nDoctor Duration Stats:")
        print(doc_stats)
        
        # 3. Emergency time-varying
        em['logged_time'] = pd.to_datetime(em['logged_time'])
        em['hour'] = em['logged_time'].dt.hour
        print("\nEmergency Counts by Hour:")
        print(em['hour'].value_counts().sort_index())
        
        # 4. Staff shortage degradation
        # We need to join df with staff based on doctor_id and date
        df['date'] = df['scheduled_time'].str[:10]
        staff_joined = pd.merge(df, staff, left_on=['doctor_id', 'date'], right_on=['doctor_id', 'date'])
        staff_joined['shortage'] = staff_joined['support_staff_present'] < staff_joined['support_staff_rostered']
        shortage_stats = staff_joined.groupby('shortage')['duration'].mean()
        print("\nDuration by Staff Shortage:")
        print(shortage_stats)
        
        # 5. Follow-ups shorter
        type_stats = df.groupby('appointment_type')['duration'].mean()
        print("\nDuration by Appointment Type:")
        print(type_stats)
        
        # 6. Scenario injection
        # The script injects emergencies for DOC_CAR_1 on the last day
        last_day = em['logged_time'].dt.date.max()
        car1_em = em[(em['doctor_id'] == 'DOC_CAR_1') & (em['logged_time'].dt.date == last_day)]
        print(f"\nEmergencies for DOC_CAR_1 on last day (Scenario Mode): {len(car1_em)}")
        
    except Exception as e:
        print(f"Error auditing data: {e}")

if __name__ == "__main__":
    audit_synthetic_data()
