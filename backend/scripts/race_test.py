import asyncio
import httpx
import sqlite3
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

async def race_checkout():
    appt_id = str(uuid.uuid4())
    conn = sqlite3.connect('hospital.db')
    conn.execute(f"INSERT INTO appointments (appointment_id, patient_id, doctor_id, department, scheduled_time, appointment_type) VALUES ('{appt_id}', 'PAT_1', 'DOC_CAR_1', 'Cardiology', '{datetime.now().isoformat()}', 'new')")
    conn.commit()
    conn.close()
    
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BASE_URL}/auth/token", data={"username": "DOC_CAR_1", "password": "doc"})
        token = res.json().get("access_token")
        print(f"Testing race condition on checkout for fresh appointment: {appt_id}")
        
        url = f"{BASE_URL}/appointments/{appt_id}/checkout"
        headers = {"Authorization": f"Bearer {token}"}
        
        res1, res2 = await asyncio.gather(
            client.post(url, headers=headers),
            client.post(url, headers=headers)
        )
        
        print(f"Request 1: {res1.status_code} - {res1.json()}")
        print(f"Request 2: {res2.status_code} - {res2.json()}")
        
        conn = sqlite3.connect('hospital.db')
        rows = conn.execute(f"SELECT * FROM consultations WHERE appointment_id = '{appt_id}'").fetchall()
        print(f"Consultation rows in DB for {appt_id}:")
        for row in rows:
            print(row)
        conn.close()

if __name__ == "__main__":
    asyncio.run(race_checkout())
