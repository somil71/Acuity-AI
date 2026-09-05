import numpy as np
from datetime import datetime, timedelta
import joblib
import os
import json
import lightgbm as lgb
import pandas as pd

class QueueSimulator:
    def __init__(self, model_dir=None):
        if model_dir is None:
            # backend/app/services -> backend/app -> backend -> root -> models
            self.model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'models')
        else:
            self.model_dir = model_dir
        self.models = {}
        self.encoders = None
        self.emergency_rates = {}
        self.is_loaded = False
        self.load_models()
        
    def load_models(self):
        try:
            self.models['q_0.1'] = lgb.Booster(model_file=os.path.join(self.model_dir, 'lgbm_duration_q0.1.txt'))
            self.models['q_0.5'] = lgb.Booster(model_file=os.path.join(self.model_dir, 'lgbm_duration_q0.5.txt'))
            self.models['q_0.9'] = lgb.Booster(model_file=os.path.join(self.model_dir, 'lgbm_duration_q0.9.txt'))
            
            self.encoders = joblib.load(os.path.join(self.model_dir, 'label_encoders.pkl'))
            
            with open(os.path.join(self.model_dir, 'emergency_rates.json'), 'r') as f:
                self.emergency_rates = json.load(f)
                
            self.staff_multiplier = self.encoders.get('staff_multiplier', 1.2)
            self.is_loaded = True
        except Exception as e:
            print(f"Failed to load models: {e}")

    def simulate_patient_wait(self, target_scheduled_time, doctor_id, department, current_time, patients_ahead, known_emergencies_remaining, staff_shortage=False, num_simulations=500):
        if not self.is_loaded:
            # Fallback to scheduled time
            return [target_scheduled_time] * 3, "Model unavailable. Displaying scheduled time."
            
        results = []
        
        # Pre-compute quantile predictions for patients ahead to save time in loop
        # patients_ahead is a list of dicts: {'type': 'new'/'follow_up', 'scheduled_time': dt, 'pat_historical_dur': float}
        ahead_quantiles = []
        for p in patients_ahead:
            try:
                d_enc = self.encoders['dept'].transform([department])[0]
                t_enc = self.encoders['type'].transform([p['type']])[0]
            except:
                d_enc, t_enc = 0, 0
            
            k = 5.0
            dept_avg = self.encoders.get('dept_avg', {})
            doc_stats = self.encoders.get('doc_stats', {})
            d_avg = dept_avg.get(department, 15.0)
            doc_data = doc_stats.get(doctor_id, {'mean': d_avg, 'count': 0})
            doc_shrunk_avg = (doc_data['count'] * doc_data['mean'] + k * d_avg) / (doc_data['count'] + k)
            
            hour = p['scheduled_time'].hour
            dow = p['scheduled_time'].weekday()
            
            pat_hist = p.get('pat_historical_dur', d_avg)
            
            # Predict P10, P50, P90
            features = np.array([[d_enc, t_enc, hour, dow, doc_shrunk_avg, pat_hist]])
            p10 = self.models['q_0.1'].predict(features)[0]
            p50 = self.models['q_0.5'].predict(features)[0]
            p90 = self.models['q_0.9'].predict(features)[0]
            ahead_quantiles.append((p10, p50, p90))
        
        # Explainability strings
        ahead_median_total = sum(q[1] for q in ahead_quantiles)
        em_total = sum(known_emergencies_remaining)
        staff_str = f"Staffing is short (throughput degraded {self.staff_multiplier:.2f}x)." if staff_shortage else "Staffing is normal."
        explanation = f"{len(patients_ahead)} patient(s) ahead taking ~{ahead_median_total:.0f} mins total. {len(known_emergencies_remaining)} active emergency(s) causing ~{em_total} mins delay. {staff_str}"

        # Monte Carlo
        for _ in range(num_simulations):
            sim_time = current_time
            
            # Add known emergencies
            for em_dur in known_emergencies_remaining:
                sim_time += timedelta(minutes=em_dur)
            
            # Walk the queue
            for q_vals in ahead_quantiles:
                p10, p50, p90 = q_vals
                # Draw from a simplified piece-wise uniform based on quantiles
                # 10% chance < p10, 40% p10-p50, 40% p50-p90, 10% > p90
                r = np.random.rand()
                if r < 0.1:
                    dur = max(1, p10 - np.random.uniform(0, 5))
                elif r < 0.5:
                    dur = np.random.uniform(p10, p50)
                elif r < 0.9:
                    dur = np.random.uniform(p50, p90)
                else:
                    dur = p90 + np.random.uniform(0, 15)
                
                if staff_shortage:
                    dur *= self.staff_multiplier
                    
                sim_time += timedelta(minutes=dur)
                
                # Check for new emergencies occurring in this interval
                hour = str(sim_time.hour)
                dow = str(sim_time.weekday())
                rate = self.emergency_rates.get(department, {}).get(dow, {}).get(hour, 0.0)
                
                # If rate > 0, Poisson draw
                new_em = np.random.poisson(rate)
                if new_em > 0:
                    sim_time += timedelta(minutes=new_em * 30) # Assuming 30 min per em
            
            results.append(sim_time)
            
        results.sort()
        p10_res = results[int(num_simulations * 0.1)]
        p50_res = results[int(num_simulations * 0.5)]
        p90_res = results[int(num_simulations * 0.9)]
        
        return p10_res, p50_res, p90_res, explanation

simulator = QueueSimulator()
