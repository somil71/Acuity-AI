import requests
import time
import os

BASE_URL = "http://localhost:8000/api"

def print_step(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def run_e2e():
    print_step("1. Seed Demo Users")
    res = requests.post(f"{BASE_URL}/auth/demo/seed")
    print(f"Seed Users Response: {res.json()}")
    
    print_step("2. Authenticate as PAT_1")
    res = requests.post(f"{BASE_URL}/auth/token", data={"username": "PAT_1", "password": "pat"})
    pat0_token = res.json().get("access_token")
    print(f"PAT_1 Token Acquired: {pat0_token[:20]}...")
    
    print_step("3. Attempt unauthorized access (PAT_1 trying to read PAT_2)")
    res = requests.get(f"{BASE_URL}/patients/PAT_2", headers={"Authorization": f"Bearer {pat0_token}"})
    print(f"Fetch PAT_2 Status Code: {res.status_code}")
    print(f"Fetch PAT_2 Response: {res.json()}")
    
    print_step("4. Fetch PAT_1 Record and live status")
    res = requests.get(f"{BASE_URL}/patients/PAT_1", headers={"Authorization": f"Bearer {pat0_token}"})
    pat_data = res.json()
    if 'visit_history' not in pat_data or not pat_data['visit_history']:
        print("No visit history found. Exiting.")
        return
        
    appt_id = pat_data['visit_history'][0]['appointment_id']
    print(f"Found upcoming appointment for PAT_1: {appt_id}")
    
    res = requests.get(f"{BASE_URL}/appointments/{appt_id}/status", headers={"Authorization": f"Bearer {pat0_token}"})
    status_before = res.json()
    print(f"Status BEFORE emergency:")
    print(f" - Explanation: {status_before['explanation']}")
    print(f" - P50 Prediction: {status_before['predicted_p50']}")
    
    print_step("5. Authenticate as Staff (DOC_CAR_1)")
    res = requests.post(f"{BASE_URL}/auth/token", data={"username": "DOC_CAR_1", "password": "doc"})
    doc_token = res.json().get("access_token")
    print(f"DOC_CAR_1 Token Acquired: {doc_token[:20]}...")
    
    print_step("6. Inject Emergency as Staff")
    res = requests.post(
        f"{BASE_URL}/appointments/emergency",
        headers={"Authorization": f"Bearer {doc_token}"},
        json={"doctor_id": status_before["doctor_id"], "department": status_before["department"], "estimated_duration": 45}
    )
    print(f"Emergency injected: {res.json()}")
    
    print_step("7. Check Patient View again (Live update verification)")
    res = requests.get(f"{BASE_URL}/appointments/{appt_id}/status", headers={"Authorization": f"Bearer {pat0_token}"})
    status_after = res.json()
    print(f"Status AFTER emergency:")
    print(f" - Explanation: {status_after['explanation']}")
    print(f" - P50 Prediction: {status_after['predicted_p50']}")
    
    print_step("8. Check Logs")
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'system_events.jsonl')
    with open(log_file, 'r') as f:
        lines = f.readlines()
        print(f"Found {len(lines)} log entries. Last 2 entries:")
        print(lines[-2].strip())
        print(lines[-1].strip())

if __name__ == "__main__":
    run_e2e()
