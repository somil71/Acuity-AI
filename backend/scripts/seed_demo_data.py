"""
Seed demo data for new PulsePredict tables: health_records, lab_results, 
prescriptions, notifications, invoices, reviews.
Run: python seed_demo_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db import SessionLocal
from app.models import schema
from datetime import datetime, timedelta
import uuid

db = SessionLocal()

def new_id():
    return str(uuid.uuid4())

# ── Get PAT_1's completed appointments ──────────────────────────────────────
patient_id = "PAT_1"
appts = (db.query(schema.Appointment)
         .filter(schema.Appointment.patient_id == patient_id)
         .join(schema.Consultation, isouter=True)
         .all())

completed = [a for a in appts if a.consultation and a.consultation.actual_end_time]
print(f"Found {len(completed)} completed appointments for PAT_1")

if not completed:
    print("No completed appointments found, exiting.")
    db.close()
    sys.exit(0)

# ── Seed Health Records + Lab Results ───────────────────────────────────────
for i, appt in enumerate(completed[:3]):
    record_id = new_id()
    rec = schema.HealthRecord(
        record_id=record_id,
        appointment_id=appt.appointment_id,
        patient_id=patient_id,
        doctor_id=appt.doctor_id,
        department=appt.department,
        visit_date=appt.scheduled_time,
        diagnosis=["Hypertension, Stage 1", "Seasonal Allergic Rhinitis", "Mild Knee Osteoarthritis"][i],
        doctor_notes=["Blood pressure elevated; recommended lifestyle changes and follow-up in 3 months.",
                      "Prescribed antihistamines; avoid known allergens.",
                      "X-ray shows mild joint space narrowing; physiotherapy recommended."][i],
        allergies="Penicillin" if i == 0 else None,
        created_at=appt.scheduled_time
    )
    db.add(rec)
    db.flush()

    # Add lab results for first record
    if i == 0:
        labs = [
            ("Blood Pressure Systolic", "148", "mmHg", "90-120", "high"),
            ("Blood Pressure Diastolic", "92", "mmHg", "60-80", "high"),
            ("Total Cholesterol", "215", "mg/dL", "<200", "high"),
            ("Blood Glucose (Fasting)", "98", "mg/dL", "70-100", "normal"),
            ("Hemoglobin", "13.8", "g/dL", "13.5-17.5", "normal"),
        ]
        for test_name, value, unit, ref_range, status in labs:
            db.add(schema.LabResult(
                result_id=new_id(),
                record_id=record_id,
                test_name=test_name,
                value=value,
                unit=unit,
                reference_range=ref_range,
                status=status,
                collected_at=appt.scheduled_time - timedelta(hours=2)
            ))

print("[OK] Seeded health records + lab results")

# ── Seed Prescriptions ───────────────────────────────────────────────────────
if completed:
    appt = completed[0]
    for drug in [
        ("Amlodipine", "5mg", "Once daily", 90, "Take in the morning with water"),
        ("Atorvastatin", "20mg", "Once nightly", 90, "Take at bedtime; avoid grapefruit"),
    ]:
        drug_name, dosage, frequency, days, instructions = drug
        db.add(schema.Prescription(
            prescription_id=new_id(),
            patient_id=patient_id,
            appointment_id=appt.appointment_id,
            prescribed_by=appt.doctor_id,
            drug_name=drug_name,
            dosage=dosage,
            frequency=frequency,
            duration_days=days,
            instructions=instructions,
            refill_status="none",
            prescribed_at=appt.scheduled_time,
            valid_until=appt.scheduled_time + timedelta(days=days)
        ))
print("[OK] Seeded prescriptions")

# ── Seed Notifications ───────────────────────────────────────────────────────
if completed:
    notifs = [
        ("lab_ready", "Lab Results Ready", "Your blood panel results from your Cardiology visit are now available in Health Records.", None),
        ("appointment_reminder", "Appointment Tomorrow", "Reminder: You have an Orthopedics appointment tomorrow. Your predicted wait window is 2:30–3:45 PM.", completed[0].appointment_id if len(completed) > 0 else None),
        ("refill_approved", "Prescription Refill Approved", "Your refill request for Amlodipine 5mg has been approved. Pick up at the pharmacy.", None),
    ]
    for i, (ntype, title, body, appt_id) in enumerate(notifs):
        db.add(schema.Notification(
            notification_id=new_id(),
            patient_id=patient_id,
            type=ntype,
            title=title,
            body=body,
            appointment_id=appt_id,
            is_read=(i == 2),  # last one is already read
            created_at=datetime.utcnow() - timedelta(hours=2 * i)
        ))
print("[OK] Seeded notifications")

# ── Seed Invoices ────────────────────────────────────────────────────────────
for i, appt in enumerate(completed[:3]):
    amounts = [(1200.0, 900.0), (450.0, 350.0), (3200.0, 2800.0)]
    total, adj = amounts[i]
    db.add(schema.Invoice(
        invoice_id=new_id(),
        patient_id=patient_id,
        appointment_id=appt.appointment_id,
        amount_total=total,
        amount_paid=total - adj if i < 2 else 0.0,
        insurance_adjustment=adj,
        status="paid" if i < 2 else "pending",
        due_date=appt.scheduled_time + timedelta(days=30),
        created_at=appt.scheduled_time,
        paid_at=appt.scheduled_time + timedelta(days=5) if i < 2 else None
    ))
print("[OK] Seeded invoices")

# ── Seed Reviews ─────────────────────────────────────────────────────────────
if len(completed) > 1:
    review_data = [
        (completed[0], 5, "Dr. was very thorough and explained everything clearly. The wait time prediction was spot on!", 4),
        (completed[1], 4, "Good visit overall, slight delay but staff were communicative.", 3),
    ]
    for appt, rating, comment, wt_rating in review_data:
        existing = db.query(schema.Review).filter(schema.Review.appointment_id == appt.appointment_id).first()
        if not existing:
            db.add(schema.Review(
                review_id=new_id(),
                appointment_id=appt.appointment_id,
                patient_id=patient_id,
                doctor_id=appt.doctor_id,
                rating=rating,
                comment=comment,
                wait_time_rating=wt_rating,
                created_at=appt.scheduled_time + timedelta(hours=3)
            ))
print("[OK] Seeded reviews")

db.commit()
db.close()
print("\n[OK] All demo data seeded successfully!")
