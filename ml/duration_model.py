import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

def prepare_data(data_dir='data'):
    appointments = pd.read_csv(f"{data_dir}/appointments.csv")
    consultations = pd.read_csv(f"{data_dir}/consultations.csv")
    staff = pd.read_csv(f"{data_dir}/staff_roster.csv")
    
    df = pd.merge(appointments, consultations, on='appointment_id')
    df['scheduled_time'] = pd.to_datetime(df['scheduled_time'])
    df['actual_start_time'] = pd.to_datetime(df['actual_start_time'])
    df['actual_end_time'] = pd.to_datetime(df['actual_end_time'])
    df['duration'] = (df['actual_end_time'] - df['actual_start_time']).dt.total_seconds() / 60.0
    
    # Compute staff shortage multiplier
    df['date'] = df['scheduled_time'].dt.strftime("%Y-%m-%d")
    df_staff = pd.merge(df, staff, on=['doctor_id', 'date'])
    df_staff['shortage'] = df_staff['support_staff_present'] < df_staff['support_staff_rostered']
    shortage_means = df_staff.groupby('shortage')['duration'].mean()
    # Handle case if there's no shortage ever
    if True in shortage_means and False in shortage_means:
        staff_multiplier = shortage_means[True] / shortage_means[False]
    else:
        staff_multiplier = 1.2
        
    print(f"Empirically computed staff shortage multiplier: {staff_multiplier:.3f}")
    
    # Sort chronologically first!
    df = df.sort_values(by='scheduled_time').reset_index(drop=True)
    
    # Compute rolling stats strictly BEFORE current row to prevent leakage
    k = 20.0
    
    # We can compute expanding mean shifted by 1 row
    # Department rolling average
    df['dept_avg_historical'] = df.groupby('department')['duration'].apply(lambda x: x.shift(1).expanding().mean()).reset_index(level=0, drop=True)
    df['dept_avg_historical'] = df['dept_avg_historical'].fillna(15.0) # Global fallback
    
    # Doctor rolling average and count
    grouped_doc = df.groupby('doctor_id')['duration']
    df['doc_mean_historical'] = grouped_doc.apply(lambda x: x.shift(1).expanding().mean()).reset_index(level=0, drop=True)
    df['doc_count_historical'] = grouped_doc.apply(lambda x: x.shift(1).expanding().count()).reset_index(level=0, drop=True)
    
    df['doc_mean_historical'] = df['doc_mean_historical'].fillna(df['dept_avg_historical'])
    df['doc_count_historical'] = df['doc_count_historical'].fillna(0)
    
    # Compute shrinkage using ONLY historical expanding stats
    df['doc_shrunk_avg'] = (df['doc_count_historical'] * df['doc_mean_historical'] + k * df['dept_avg_historical']) / (df['doc_count_historical'] + k)
    
    df['pat_historical_dur'] = df.groupby(['patient_id', 'doctor_id'])['duration'].shift(1).fillna(df['dept_avg_historical'])

    # We still need global dept_avg and doc_stats for inference time (serving live traffic)
    dept_avg = df.groupby('department')['duration'].mean().to_dict()
    doc_stats = df.groupby('doctor_id')['duration'].agg(['mean', 'count']).to_dict(orient='index')
    df['hour'] = df['scheduled_time'].dt.hour
    df['day_of_week'] = df['scheduled_time'].dt.dayofweek
    
    return df, dept_avg, doc_stats, staff_multiplier

def train_quantile_model(data_dir='data', model_dir='models'):
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    df, dept_avg, doc_stats, staff_multiplier = prepare_data(data_dir)
    
    le_dept = LabelEncoder()
    le_doc = LabelEncoder()
    le_type = LabelEncoder()
    
    df['department_encoded'] = le_dept.fit_transform(df['department'])
    df['doctor_encoded'] = le_doc.fit_transform(df['doctor_id'])
    df['type_encoded'] = le_type.fit_transform(df['appointment_type'])
    
    features = ['department_encoded', 'type_encoded', 'hour', 'day_of_week', 'doc_shrunk_avg', 'pat_historical_dur']
    X = df[features]
    y = df['duration']
    
    print(f"Final feature set used for model training: {features}")
    
    import json
    # Chronological Split (Train 60%, Val 20%, Test 20%)
    n = len(df)
    train_idx = int(n * 0.6)
    val_idx = int(n * 0.8)
    
    X_train, y_train = X.iloc[:train_idx], y.iloc[:train_idx]
    X_val, y_val = X.iloc[train_idx:val_idx], y.iloc[train_idx:val_idx]
    X_test, y_test = X.iloc[val_idx:], y.iloc[val_idx:]
    
    print(f"Chronological split: Train to {train_idx}, Val to {val_idx}, Test to {n}")
    
    # Train P10, P50, P90 models to get nominal 80% coverage
    quantiles = [0.1, 0.5, 0.9]
    models = {}
    
    for alpha in quantiles:
        print(f"Training LightGBM for quantile {alpha}...")
        model = lgb.LGBMRegressor(
            objective='quantile',
            alpha=alpha,
            n_estimators=100,
            learning_rate=0.05,
            min_child_samples=100,
            reg_lambda=1.0
        )
        model.fit(X_train, y_train)
        models[f'q_{alpha}'] = model
        
        # Save model
        model_path = os.path.join(model_dir, f'lgbm_duration_q{alpha}.txt')
        model.booster_.save_model(model_path)
        
    joblib.dump({
        'dept': le_dept, 'doc': le_doc, 'type': le_type,
        'dept_avg': dept_avg, 'doc_stats': doc_stats,
        'staff_multiplier': staff_multiplier
    }, os.path.join(model_dir, 'label_encoders.pkl'))
    print("Models and encoders saved.\n")
    
    # Conformal Calibration on Val set
    print("Running Conformal Calibration on Val Set...")
    q50_pred_val = models['q_0.5'].predict(X_val)
    residuals = np.abs(y_val - q50_pred_val)
    
    alpha_conf = 0.10
    n_val = len(y_val)
    q_level = (1 - alpha_conf) * (1 + 1 / n_val)
    
    if q_level > 1.0: q_level = 1.0
    global_residual_q90 = np.quantile(residuals, q_level)
    
    calibration_data = {
        "global": {
            "residual_q90": float(global_residual_q90),
            "n_calibration": int(n_val)
        }
    }
    
    # Per department conformal
    df_val = df.iloc[train_idx:val_idx].copy()
    df_val['residual'] = residuals
    
    for dept in df_val['department'].unique():
        dept_res = df_val[df_val['department'] == dept]['residual']
        n_dept = len(dept_res)
        if n_dept > 10:
            q_level_dept = (1 - alpha_conf) * (1 + 1 / n_dept)
            if q_level_dept > 1.0: q_level_dept = 1.0
            calibration_data[dept] = {
                "residual_q90": float(np.quantile(dept_res, q_level_dept)),
                "n_calibration": int(n_dept)
            }
        else:
            calibration_data[dept] = {
                "residual_q90": float(global_residual_q90),
                "n_calibration": int(n_dept)
            }
    
    # Evaluate on true chronological test set
    print("Evaluating Calibration of legacy intervals and Conformal intervals on Test Set...")
    df_test = df.iloc[val_idx:].copy()
    y_test_actual = y_test
    
    p10_pred = models['q_0.1'].predict(X_test)
    p50_pred = models['q_0.5'].predict(X_test)
    p90_pred = models['q_0.9'].predict(X_test)
    
    # Legacy coverage
    within_legacy = (y_test_actual >= p10_pred) & (y_test_actual <= p90_pred)
    legacy_coverage = within_legacy.mean() * 100
    print(f"Legacy [P10, P90] Coverage: {legacy_coverage:.2f}% (Expected ~80%)")
    
    # Conformal coverage
    df_test['p50_pred'] = p50_pred
    df_test['y_actual'] = y_test_actual
    
    conformal_within = []
    for idx, row in df_test.iterrows():
        dept = row['department']
        res_q90 = calibration_data.get(dept, calibration_data["global"])["residual_q90"]
        lower = max(0, row['p50_pred'] - res_q90)
        upper = row['p50_pred'] + res_q90
        conformal_within.append((row['y_actual'] >= lower) and (row['y_actual'] <= upper))
        
    conformal_coverage = np.mean(conformal_within) * 100
    calibration_data["global"]["actual_coverage"] = float(conformal_coverage / 100.0)
    
    with open(os.path.join(model_dir, 'conformal_calibration.json'), 'w') as f:
        json.dump(calibration_data, f, indent=2)
        
    print(f"Conformal Calibration Coverage: {conformal_coverage:.2f}% (Must be >= 90%)")
    
    df_test['p50_mae'] = (y_test_actual - p50_pred).abs()
    overall_mae = df_test['p50_mae'].mean()
    print(f"Mean Absolute Error (P50 vs Actual): {overall_mae:.2f} mins")
    
    print("\nCalibration by Department (Conformal):")
    df_test['conformal_within'] = conformal_within
    for dept in df_test['department'].unique():
        dept_mask = df_test['department'] == dept
        coverage = df_test['conformal_within'][dept_mask].mean() * 100
        dept_mae = df_test['p50_mae'][dept_mask].mean()
        print(f" - {dept}: {coverage:.2f}% coverage, MAE: {dept_mae:.2f} mins")

if __name__ == "__main__":
    train_quantile_model()
