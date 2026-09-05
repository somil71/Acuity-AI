import datetime
import time
from app.services.simulation import simulator
import joblib
import os

def run_tests():
    doc_a = 'DOC_CAR_1'
    doc_b = 'DOC_GEN_1'
    dept_a = 'Cardiology'
    dept_b = 'General Physician'
    current_time = datetime.datetime(2026, 9, 4, 10, 0, 0)
    
    # 1. Staff shortage multiplier test
    print("\n--- 1. Staff Shortage Multiplier ---")
    enc = joblib.load(os.path.join(simulator.model_dir, 'label_encoders.pkl'))
    multiplier = enc.get('staff_multiplier', 1.0)
    print(f"Empirical Multiplier loaded: {multiplier:.3f}")
    
    pat_a = [{'type': 'new', 'scheduled_time': current_time + datetime.timedelta(minutes=i*20)} for i in range(3)]
    res_normal = simulator.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [])
    res_short = simulator.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [], staff_shortage=True)
    norm_p50 = (res_normal[1] - current_time).total_seconds() / 60.0
    short_p50 = (res_short[1] - current_time).total_seconds() / 60.0
    print(f"Normal P50 Wait: {norm_p50:.1f}m")
    print(f"Shortage P50 Wait: {short_p50:.1f}m")
    print(f"Measured Impact Ratio: {short_p50 / norm_p50:.3f}")
    
    # 2. Degradation Fallback
    print("\n--- 2. Degradation Fallback ---")
    sim2 = type(simulator)(model_dir='fake_dir')
    res_fail = sim2.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [])
    print(f"Fallback response: {res_fail}")
    
    # 3. Explainability Output
    print("\n--- 4. Explainability ---")
    print(f"Explanation for Doc A with 3 patients and 1 emergency (30m):")
    print(simulator.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [30])[3])
    
    # 4. Cross-Doctor Leakage
    print("\n--- 5a. Cross-Doctor Leakage ---")
    pat_b = [{'type': 'new', 'scheduled_time': current_time + datetime.timedelta(minutes=i*10)} for i in range(2)]
    res_b_before = simulator.simulate_patient_wait(pat_b[-1]['scheduled_time'], doc_b, dept_b, current_time, pat_b, [])
    
    # Inject emergency for doc A
    res_a_em = simulator.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [45])
    
    res_b_after = simulator.simulate_patient_wait(pat_b[-1]['scheduled_time'], doc_b, dept_b, current_time, pat_b, [])
    print(f"Doc B P50 BEFORE Doc A emergency: {res_b_before[1]}")
    print(f"Doc B P50 AFTER Doc A emergency: {res_b_after[1]}")
    
    # 5. Live Recompute Latency
    print("\n--- 5c. Live Recompute Latency ---")
    pat_c = [{'type': 'new', 'scheduled_time': current_time + datetime.timedelta(minutes=i*15)} for i in range(8)]
    start_time = time.time()
    simulator.simulate_patient_wait(pat_c[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_c, [30])
    latency = time.time() - start_time
    print(f"Latency for 8 patients + 1 emergency: {latency:.4f} seconds")
    
    # 6. Monte Carlo Convergence
    print("\n--- 5d. Monte Carlo Convergence ---")
    runs = []
    for _ in range(100):
        res = simulator.simulate_patient_wait(pat_a[-1]['scheduled_time'], doc_a, dept_a, current_time, pat_a, [30])
        runs.append((res[1] - current_time).total_seconds() / 60.0)
    runs = np.array(runs)
    print(f"Mean P50 over 100 runs: {runs.mean():.2f}m")
    print(f"Std Dev of P50 over 100 runs: {runs.std():.2f}m")

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    run_tests()
