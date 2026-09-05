import pandas as pd
import numpy as np
import json
import os

def build_emergency_lookup(data_dir='data', output_dir='models'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        events = pd.read_csv(f"{data_dir}/emergency_events.csv")
    except FileNotFoundError:
        print("No emergency events found, building empty lookup.")
        events = pd.DataFrame(columns=['logged_time', 'department'])
        
    if not events.empty:
        events['logged_time'] = pd.to_datetime(events['logged_time'])
        events['hour'] = events['logged_time'].dt.hour
        events['day_of_week'] = events['logged_time'].dt.dayofweek
        
        # Calculate rates (events per day/hour)
        # Simplified: just count and average across num_days
        # For a robust lookup, we'd divide by total days tracked
        # Here we just use a basic empirical probability
        counts = events.groupby(['department', 'day_of_week', 'hour']).size().reset_index(name='count')
        # Assuming 30 days of data
        counts['rate'] = counts['count'] / 30.0
        
        lookup = {}
        for _, row in counts.iterrows():
            dept = row['department']
            if dept not in lookup:
                lookup[dept] = {}
            day = str(int(row['day_of_week']))
            if day not in lookup[dept]:
                lookup[dept][day] = {}
            hour = str(int(row['hour']))
            lookup[dept][day][hour] = row['rate']
    else:
        lookup = {}
        
    with open(os.path.join(output_dir, 'emergency_rates.json'), 'w') as f:
        json.dump(lookup, f)
    
    print("Emergency arrival rates lookup built.")

if __name__ == "__main__":
    build_emergency_lookup()
