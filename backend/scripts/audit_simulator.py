import datetime
from app.services.simulation import simulator

def audit_simulator():
    print("--- Component 4: Queue Simulation Engine Audit ---")
    
    # Test MC nature
    doc_id = 'DOC_CAR_1'
    dept = 'Cardiology'
    current_time = datetime.datetime.now()
    
    patients = [{'type': 'new', 'scheduled_time': current_time + datetime.timedelta(minutes=i*20)} for i in range(6)]
    
    print("Testing Monte Carlo randomness (2 runs, same state):")
    r1 = simulator.simulate_patient_wait(doc_id, dept, current_time, patients, [])
    r2 = simulator.simulate_patient_wait(doc_id, dept, current_time, patients, [])
    print(f"Run 1: {r1}")
    print(f"Run 2: {r2}")
    
    print("\nTesting queue position uncertainty spread:")
    # Patient 1
    p1 = simulator.simulate_patient_wait(doc_id, dept, current_time, patients[:1], [])
    p1_spread = (p1[2] - p1[0]).total_seconds() / 60.0
    # Patient 3
    p3 = simulator.simulate_patient_wait(doc_id, dept, current_time, patients[:3], [])
    p3_spread = (p3[2] - p3[0]).total_seconds() / 60.0
    # Patient 6
    p6 = simulator.simulate_patient_wait(doc_id, dept, current_time, patients[:6], [])
    p6_spread = (p6[2] - p6[0]).total_seconds() / 60.0
    
    print(f"P1 spread: {p1_spread:.1f}m, P3 spread: {p3_spread:.1f}m, P6 spread: {p6_spread:.1f}m")
    
    print("\nTesting live recompute on emergency:")
    print(f"P6 Baseline: {p6}")
    p6_em = simulator.simulate_patient_wait(doc_id, dept, current_time, patients[:6], [30])
    print(f"P6 with 30m emergency injected: {p6_em}")
    delay_diff = (p6_em[1] - p6[1]).total_seconds() / 60.0
    print(f"P50 shifted by: {delay_diff:.1f}m")

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    audit_simulator()
