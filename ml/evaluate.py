import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os

def evaluate_calibration(data_dir='data', model_dir='models'):
    print("Loading test data (using synthetic data for eval)...")
    appointments = pd.read_csv(f"{data_dir}/appointments.csv")
    consultations = pd.read_csv(f"{data_dir}/consultations.csv")
    
    df = pd.merge(appointments, consultations, on='appointment_id')
    df['scheduled_time'] = pd.to_datetime(df['scheduled_time'])
    df['actual_start_time'] = pd.to_datetime(df['actual_start_time'])
    df['actual_end_time'] = pd.to_datetime(df['actual_end_time'])
    
    df['duration'] = (df['actual_end_time'] - df['actual_start_time']).dt.total_seconds() / 60.0
    
    df['hour'] = df['scheduled_time'].dt.hour
    df['day_of_week'] = df['scheduled_time'].dt.dayofweek
    
    encoders = joblib.load(os.path.join(model_dir, 'label_encoders.pkl'))
    
    k = 5.0
    dept_avg = encoders.get('dept_avg', {})
    doc_stats = encoders.get('doc_stats', {})
    
    def calculate_shrinkage(row):
        d_avg = dept_avg.get(row['department'], 15.0)
        doc = doc_stats.get(row['doctor_id'], {'mean': d_avg, 'count': 0})
        return (doc['count'] * doc['mean'] + k * d_avg) / (doc['count'] + k)
        
    df['doc_shrunk_avg'] = df.apply(calculate_shrinkage, axis=1)

    df['pat_historical_dur'] = df.groupby(['patient_id', 'doctor_id'])['duration'].shift(1).fillna(df['department'].map(dept_avg).fillna(15.0))

    df['department_encoded'] = encoders['dept'].transform(df['department'])
    df['doctor_encoded'] = encoders['doc'].transform(df['doctor_id'])
    df['type_encoded'] = encoders['type'].transform(df['appointment_type'])
    
    features = ['department_encoded', 'type_encoded', 'hour', 'day_of_week', 'doc_shrunk_avg', 'pat_historical_dur']
    X = df[features]
    y = df['duration']
    
    print("Evaluating Calibration of P10 and P90 intervals...")
    p10_model = lgb.Booster(model_file=os.path.join(model_dir, 'lgbm_duration_q0.1.txt'))
    p50_model = lgb.Booster(model_file=os.path.join(model_dir, 'lgbm_duration_q0.5.txt'))
    p90_model = lgb.Booster(model_file=os.path.join(model_dir, 'lgbm_duration_q0.9.txt'))
    
    df['p10_pred'] = p10_model.predict(X)
    df['p50_pred'] = p50_model.predict(X)
    df['p90_pred'] = p90_model.predict(X)
    
    # Calibration check
    within_interval = (df['duration'] >= df['p10_pred']) & (df['duration'] <= df['p90_pred'])
    overall_coverage = within_interval.mean() * 100
    
    df['p50_mae'] = (df['duration'] - df['p50_pred']).abs()
    overall_mae = df['p50_mae'].mean()
    
    print(f"Percentage of actual durations falling within the [P10, P90] interval: {overall_coverage:.2f}%")
    print("Expected: ~80%")
    print(f"Mean Absolute Error (P50 vs Actual): {overall_mae:.2f} mins")
    
    print("\nCalibration by Department:")
    for dept in df['department'].unique():
        dept_mask = df['department'] == dept
        coverage = within_interval[dept_mask].mean() * 100
        dept_mae = df['p50_mae'][dept_mask].mean()
        print(f" - {dept}: {coverage:.2f}% coverage, MAE: {dept_mae:.2f} mins")
        
if __name__ == "__main__":
    evaluate_calibration()
