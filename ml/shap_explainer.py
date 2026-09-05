import shap
import lightgbm as lgb
import numpy as np
import json
import os

class DurationShapExplainer:
    def __init__(self, model_path, feature_names, label_encoders, dept_avg, doc_stats):
        self.booster = lgb.Booster(model_file=model_path)
        self.explainer = shap.TreeExplainer(self.booster)
        self.feature_names = feature_names
        self.label_encoders = label_encoders
        self.dept_avg = dept_avg
        self.doc_stats = doc_stats
        
    def explain(self, X_row: dict) -> dict:
        # X_row is a dict of feature names to values
        X_arr = np.array([[X_row[f] for f in self.feature_names]])
        shap_values = self.explainer.shap_values(X_arr)
        
        # TreeExplainer might return list or array depending on objective. For regression, array.
        if isinstance(shap_values, list):
            shap_vals = shap_values[0][0]
        else:
            shap_vals = shap_values[0]
            
        base_value = self.explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[0]
            
        features = []
        for i, f in enumerate(self.feature_names):
            features.append({
                'feature': f,
                'value': X_row[f],
                'display_name': self._feature_display_name(f, X_row[f]),
                'impact': float(shap_vals[i])
            })
            
        # Top 5 by absolute impact
        features.sort(key=lambda x: abs(x['impact']), reverse=True)
        top_5 = features[:5]
        
        return {
            'base_value': float(base_value),
            'top_factors': top_5
        }
    
    def _feature_display_name(self, feature_name, feature_value):
        if feature_name == 'department_encoded':
            try:
                dept = self.label_encoders['dept'].inverse_transform([int(feature_value)])[0]
                return f'Department: {dept}'
            except:
                return 'Department'
        elif feature_name == 'doctor_encoded':
            return 'Doctor Specifics'
        elif feature_name == 'type_encoded':
            try:
                t = self.label_encoders['type'].inverse_transform([int(feature_value)])[0]
                return f'Appointment Type: {t}'
            except:
                return 'Appointment Type'
        elif feature_name == 'hour':
            return f'Time of Day: {int(feature_value)}:00'
        elif feature_name == 'day_of_week':
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            return f'Day of Week: {days[int(feature_value)]}'
        elif feature_name == 'doc_shrunk_avg':
            return 'Doctor Historical Avg'
        elif feature_name == 'pat_historical_dur':
            return 'Patient History'
        return feature_name

if __name__ == '__main__':
    # Just save config
    config = {
        'feature_names': ['department_encoded', 'type_encoded', 'hour', 'day_of_week', 'doc_shrunk_avg', 'pat_historical_dur'],
        'display_mappings': {
            'department_encoded': 'Department',
            'type_encoded': 'Appointment Type',
            'hour': 'Time of Day',
            'day_of_week': 'Day of Week',
            'doc_shrunk_avg': 'Doctor Historical Avg',
            'pat_historical_dur': 'Patient History'
        }
    }
    os.makedirs('ml/models', exist_ok=True)
    with open('ml/models/shap_config.json', 'w') as f:
        json.dump(config, f, indent=2)
