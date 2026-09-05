import xgboost as xgb
import joblib
import os
import pandas as pd
from datetime import datetime, timedelta

class WaitTimePredictor:
    def __init__(self, model_path='../ml/models/xgboost_wait_time_model.json', encoder_path='../ml/models/label_encoder.pkl'):
        self.model = xgb.XGBRegressor()
        try:
            self.model.load_model(model_path)
            self.le = joblib.load(encoder_path)
            self.is_loaded = True
        except Exception as e:
            print(f"Warning: Could not load model. Provide path correctly or train model first. Error: {e}")
            self.is_loaded = False

    def predict_delay(self, department: str, queue_position: int, emergencies: int, scheduled_time: datetime, is_follow_up: bool):
        if not self.is_loaded:
            return 0 # fallback to 0 delay if no model
            
        try:
            dept_encoded = self.le.transform([department])[0]
        except:
            dept_encoded = 0 # fallback
            
        features = pd.DataFrame([{
            'department_encoded': dept_encoded,
            'queue_position': queue_position,
            'emergencies_logged_today': emergencies,
            'day_of_week': scheduled_time.weekday(),
            'is_follow_up': 1 if is_follow_up else 0,
            'scheduled_hour': scheduled_time.hour
        }])
        
        delay_minutes = self.model.predict(features)[0]
        return max(0, float(delay_minutes)) # No negative delays

predictor = WaitTimePredictor()
