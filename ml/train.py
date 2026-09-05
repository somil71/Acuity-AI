import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import LabelEncoder
import joblib
import os

def train_model(data_path='data/synthetic_appointments.csv', model_dir='models'):
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Feature engineering
    df['scheduled_hour'] = pd.to_datetime(df['scheduled_time']).dt.hour
    
    # Encode categorical features
    le = LabelEncoder()
    df['department_encoded'] = le.fit_transform(df['department'])
    
    features = [
        'department_encoded',
        'queue_position',
        'emergencies_logged_today',
        'day_of_week',
        'is_follow_up',
        'scheduled_hour'
    ]
    
    X = df[features]
    y = df['delay_minutes']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost model...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5
    )
    
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"Model trained! Mean Absolute Error on test set: {mae:.2f} minutes")
    
    model_path = os.path.join(model_dir, 'xgboost_wait_time_model.json')
    model.save_model(model_path)
    joblib.dump(le, os.path.join(model_dir, 'label_encoder.pkl'))
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
