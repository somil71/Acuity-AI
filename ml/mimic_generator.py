import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import json

def generate_mimic_data(output_dir='data', start_date='2024-01-01', end_date='2025-12-31'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end - start).days + 1
    
    departments = ['Cardiology', 'General Physician', 'Orthopedics', 'Pediatrics']
    dispositions = ['DISCHARGED', 'ADMITTED', 'TRANSFERRED', 'LEFT_AMA']
    disp_probs = [0.65, 0.28, 0.04, 0.03]
    
    complaints = ['chest pain', 'shortness of breath', 'abdominal pain', 'fall', 
                  'headache', 'fever', 'knee pain', 'anxiety', 'laceration', 'back pain']
    
    edstays = []
    triage = []
    vitalsign = []
    
    stay_id_counter = 30000000
    subject_id_counter = 10000000
    
    current_time = start
    while current_time < end:
        # Poisson arrival: 10/hr daytime (8am-8pm), 3/hr overnight
        is_day = 8 <= current_time.hour < 20
        rate = 10.0 if is_day else 3.0
        
        # Inter-arrival time in minutes
        iat = np.random.exponential(60.0 / rate)
        current_time += timedelta(minutes=iat)
        
        if current_time >= end:
            break
            
        stay_id = stay_id_counter
        stay_id_counter += 1
        subject_id = subject_id_counter + random.randint(0, 10000)
        
        dept = random.choice(departments)
        if dept == 'Pediatrics':
            age = random.uniform(1, 17)
        else:
            age = np.clip(np.random.normal(45, 18), 1, 95)
            
        gender = random.choice(['M', 'F'])
        disp = np.random.choice(dispositions, p=disp_probs)
        
        # LOS lognormal mean 4.2h, sigma 0.65
        los_hours = np.random.lognormal(mean=np.log(4.2), sigma=0.65)
        outtime = current_time + timedelta(hours=los_hours)
        
        edstays.append({
            'stay_id': stay_id,
            'subject_id': subject_id,
            'intime': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'outtime': outtime.strftime('%Y-%m-%d %H:%M:%S'),
            'department': dept,
            'disposition': disp,
            'gender': gender,
            'age': round(age, 1)
        })
        
        # Triage
        esi = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.18, 0.52, 0.20, 0.05])
        hr = np.random.normal(85, 15)
        sbp = np.random.normal(125, 20)
        dbp = np.random.normal(80, 15)
        rr = np.random.normal(18, 4)
        o2 = np.clip(np.random.normal(97, 3), 50, 100)
        temp = np.random.normal(37, 0.8)
        
        if esi in [1, 2]:
            pain = random.randint(6, 10)
        else:
            pain = random.randint(0, 7)
            
        triage.append({
            'stay_id': stay_id,
            'acuity': esi,
            'chief_complaint': random.choice(complaints),
            'pain': pain,
            'heart_rate': round(hr),
            'sbp': round(sbp),
            'dbp': round(dbp),
            'resp_rate': round(rr),
            'o2sat': round(o2),
            'temperature': round(temp, 1)
        })
        
        # Vitals
        num_vitals = random.randint(2, 4)
        for j in range(num_vitals):
            v_time = current_time + timedelta(minutes=random.uniform(10, los_hours * 60 - 10))
            if v_time >= outtime:
                v_time = current_time + timedelta(minutes=5)
                
            hr_v = np.clip(np.random.normal(hr, 5), 30, 200)
            sbp_v = np.clip(np.random.normal(sbp, 10), 50, 250)
            dbp_v = np.clip(np.random.normal(dbp, 8), 30, 150)
            rr_v = np.clip(np.random.normal(rr, 2), 8, 40)
            o2_v = np.clip(np.random.normal(o2, 1), 50, 100)
            temp_v = np.clip(np.random.normal(temp, 0.2), 32, 42)
            
            vitalsign.append({
                'stay_id': stay_id,
                'charttime': v_time.strftime('%Y-%m-%d %H:%M:%S'),
                'heart_rate': round(hr_v),
                'sbp': round(sbp_v),
                'dbp': round(dbp_v),
                'resp_rate': round(rr_v),
                'o2sat': round(o2_v),
                'temperature': round(temp_v, 1)
            })
            
    df_edstays = pd.DataFrame(edstays)
    df_triage = pd.DataFrame(triage)
    df_vitals = pd.DataFrame(vitalsign)
    
    df_edstays.to_csv(f"{output_dir}/mimic_edstays.csv", index=False)
    df_triage.to_csv(f"{output_dir}/mimic_triage.csv", index=False)
    df_vitals.to_csv(f"{output_dir}/mimic_vitalsign.csv", index=False)
    
    stats = {
        'total_visits': len(df_edstays),
        'start_date': start_date,
        'end_date': end_date,
        'dept_distribution': df_edstays['department'].value_counts().to_dict(),
        'disp_distribution': df_edstays['disposition'].value_counts().to_dict(),
        'mean_los_hours': (pd.to_datetime(df_edstays['outtime']) - pd.to_datetime(df_edstays['intime'])).dt.total_seconds().mean() / 3600
    }
    
    with open(f"{output_dir}/mimic_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)
        
    print(f"Generated {len(df_edstays)} stays. Saved to {output_dir}")

if __name__ == '__main__':
    generate_mimic_data()
