import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def build_training_dataset(edstays_df, triage_df, vitalsign_df, snapshot_interval_minutes=30):
    print("Converting datetimes...", flush=True)
    edstays_df['intime'] = pd.to_datetime(edstays_df['intime'])
    edstays_df['outtime'] = pd.to_datetime(edstays_df['outtime'])
    
    triage_df = triage_df.set_index('stay_id')
    edstays_df = edstays_df.set_index('stay_id')
    
    # Pre-calculate high acuity
    triage_df['is_high_acuity'] = triage_df['acuity'].isin([1, 2])
    edstays_df = edstays_df.join(triage_df[['is_high_acuity']])
    
    intimes = edstays_df['intime'].values.astype('datetime64[s]').astype(np.int64)
    outtimes = edstays_df['outtime'].values.astype('datetime64[s]').astype(np.int64)
    high_acuities = edstays_df['is_high_acuity'].values.astype(bool)
    
    min_time = edstays_df['intime'].min()
    max_time = edstays_df['outtime'].max()
    
    # Create snapshot times
    snapshots_dt = pd.date_range(start=min_time + timedelta(hours=24), 
                                 end=max_time - timedelta(hours=2), 
                                 freq=f'{snapshot_interval_minutes}min')
    
    snapshot_times = snapshots_dt.values.astype('datetime64[s]').astype(np.int64)
    print(f"Building {len(snapshot_times)} snapshots...", flush=True)
    
    results = []
    
    # Sort intimes and outtimes for binary search
    sort_idx_in = np.argsort(intimes)
    intimes_sorted = intimes[sort_idx_in]
    
    sort_idx_out = np.argsort(outtimes)
    outtimes_sorted = outtimes[sort_idx_out]
    
    for i, st in enumerate(snapshot_times):
        if i % 5000 == 0:
            print(f"Processed {i} snapshots", flush=True)
            
        # Mask of active patients at st
        active_mask = (intimes <= st) & (outtimes > st)
        active_census = active_mask.sum()
        
        # Arrivals
        arr_15m = np.sum((intimes <= st) & (intimes >= st - 15*60))
        arr_30m = np.sum((intimes <= st) & (intimes >= st - 30*60))
        arr_60m = np.sum((intimes <= st) & (intimes >= st - 60*60))
        arr_120m = np.sum((intimes <= st) & (intimes >= st - 120*60))
        
        # Departures
        dep_15m = np.sum((outtimes <= st) & (outtimes >= st - 15*60))
        dep_30m = np.sum((outtimes <= st) & (outtimes >= st - 30*60))
        dep_60m = np.sum((outtimes <= st) & (outtimes >= st - 60*60))
        
        net_flow = arr_60m - dep_60m
        
        if active_census > 0:
            high_ac = high_acuities[active_mask].sum()
            ha_ratio = high_ac / active_census
            mean_tis = (st - intimes[active_mask]).mean() / 60.0
        else:
            ha_ratio = 0.0
            mean_tis = 0.0
            
        arr_trend = arr_30m / (arr_60m / 2.0) if arr_60m > 0 else 1.0
        
        dt = pd.to_datetime(st, unit='s')
        
        res = {
            'snapshot_time': dt,
            'current_active_census': active_census,
            'arrivals_15m': arr_15m,
            'arrivals_30m': arr_30m,
            'arrivals_60m': arr_60m,
            'arrivals_120m': arr_120m,
            'departures_15m': dep_15m,
            'departures_30m': dep_30m,
            'departures_60m': dep_60m,
            'net_flow_60m': net_flow,
            'high_acuity_ratio': ha_ratio,
            'mean_time_in_system': mean_tis,
            'hour_of_day': dt.hour,
            'day_of_week': dt.dayofweek,
            'month': dt.month,
            'arrival_rate_trend': arr_trend
        }
        
        # Targets
        for h in [30, 60, 120]:
            t_st = st + h * 60
            tc = np.sum((intimes <= t_st) & (outtimes > t_st))
            res[f'target_census_{h}m'] = tc
            
        results.append(res)
        
    df_snapshots = pd.DataFrame(results)
    
    for h in [30, 60, 120]:
        q25 = df_snapshots[f'target_census_{h}m'].quantile(0.25)
        q50 = df_snapshots[f'target_census_{h}m'].quantile(0.50)
        q75 = df_snapshots[f'target_census_{h}m'].quantile(0.75)
        
        def assign_tier(val):
            if val <= q25: return 'low'
            elif val <= q50: return 'moderate'
            elif val <= q75: return 'busy'
            else: return 'critical'
            
        df_snapshots[f'congestion_tier_{h}m'] = df_snapshots[f'target_census_{h}m'].apply(assign_tier)
        
    if not os.path.exists('data'):
        os.makedirs('data')
    df_snapshots.to_csv('data/training_snapshots.csv', index=False)
    print(f"Saved {len(df_snapshots)} snapshots to data/training_snapshots.csv", flush=True)
    return df_snapshots

if __name__ == '__main__':
    print("Loading MIMIC data...", flush=True)
    ed = pd.read_csv('data/mimic_edstays.csv')
    tr = pd.read_csv('data/mimic_triage.csv')
    vi = pd.read_csv('data/mimic_vitalsign.csv')
    build_training_dataset(ed, tr, vi)
