import pandas as pd
import lightgbm as lgb
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
import json
import os
import pickle

def train_congestion_models():
    df = pd.read_csv('data/training_snapshots.csv')
    
    feature_cols = ['current_active_census','arrivals_15m','arrivals_30m','arrivals_60m',
                    'arrivals_120m','departures_30m','departures_60m','net_flow_60m',
                    'high_acuity_ratio','mean_time_in_system','hour_of_day','day_of_week',
                    'month','arrival_rate_trend']
                    
    # Tier mapping
    tier_map = {'low': 0, 'moderate': 1, 'busy': 2, 'critical': 3}
    
    split_train = int(len(df) * 0.7)
    split_val = int(len(df) * 0.85)
    
    if not os.path.exists('ml/models'):
        os.makedirs('ml/models')
        
    thresholds = {}
    metadata = {'feature_names': feature_cols, 'metrics': {}}
    
    for h in [30, 60, 120]:
        print(f"\n--- Training {h}m horizon model ---")
        df[f'target_enc_{h}m'] = df[f'congestion_tier_{h}m'].map(tier_map)
        
        # Save thresholds (approximate from data)
        q25 = df[f'target_census_{h}m'].quantile(0.25)
        q50 = df[f'target_census_{h}m'].quantile(0.50)
        q75 = df[f'target_census_{h}m'].quantile(0.75)
        thresholds[f'{h}m'] = {'q25': q25, 'q50': q50, 'q75': q75}
        
        X_train = df[feature_cols].iloc[:split_train]
        y_train = df[f'target_enc_{h}m'].iloc[:split_train]
        
        X_val = df[feature_cols].iloc[split_train:split_val]
        y_val = df[f'target_enc_{h}m'].iloc[split_train:split_val]
        
        X_test = df[feature_cols].iloc[split_val:]
        y_test = df[f'target_enc_{h}m'].iloc[split_val:]
        
        model = lgb.LGBMClassifier(num_class=4, objective='multiclass', n_estimators=100)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(10)])
        
        model.booster_.save_model(f'ml/models/congestion_{h}m.txt')
        
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        cm = confusion_matrix(y_test, y_pred)
        
        metadata['metrics'][f'{h}m'] = {'accuracy': acc, 'f1': f1}
        
        print(f"Horizon {h}m Test Accuracy: {acc:.4f}, F1: {f1:.4f}")
        print("Confusion Matrix:")
        print(cm)
        
    with open('ml/models/congestion_label_encoder.pkl', 'wb') as f:
        pickle.dump(tier_map, f)
        
    with open('ml/models/congestion_tier_thresholds.json', 'w') as f:
        json.dump(thresholds, f, indent=2)
        
    with open('ml/models/congestion_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
        
if __name__ == '__main__':
    train_congestion_models()
