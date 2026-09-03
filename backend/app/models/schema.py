from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Date, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)  # user_id
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # 'patient', 'staff', 'admin'
    name = Column(String)

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    
    appointments = relationship("Appointment", back_populates="patient")
    health_records = relationship("HealthRecord", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    notifications = relationship("Notification", back_populates="patient")
    reviews = relationship("Review", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    waitlist_entries = relationship("Waitlist", back_populates="patient")
    message_threads = relationship("MessageThread", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    doctor_id = Column(String, index=True)
    department = Column(String, index=True)
    scheduled_time = Column(DateTime, index=True)
    appointment_type = Column(String)  # new, follow_up
    status = Column(String, default="scheduled")  # scheduled, cancelled, completed, no_show
    noshowrisk_score = Column(Float, nullable=True)  # ML-B: 0.0-1.0 risk score

    patient = relationship("Patient", back_populates="appointments")
    consultation = relationship("Consultation", back_populates="appointment", uselist=False)
    health_record = relationship("HealthRecord", back_populates="appointment", uselist=False)
    review = relationship("Review", back_populates="appointment", uselist=False)
    invoice = relationship("Invoice", back_populates="appointment", uselist=False)

class Consultation(Base):
    __tablename__ = "consultations"

    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), primary_key=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    appointment = relationship("Appointment", back_populates="consultation")

class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    event_id = Column(String, primary_key=True, index=True)
    doctor_id = Column(String, index=True)
    department = Column(String)
    logged_time = Column(DateTime, index=True)
    resolved_time = Column(DateTime, nullable=True)

class StaffRoster(Base):
    __tablename__ = "staff_roster"
    
    date = Column(Date, primary_key=True)
    doctor_id = Column(String, primary_key=True)
    shift_start = Column(DateTime)
    shift_end = Column(DateTime)
    support_staff_present = Column(Integer)
    support_staff_rostered = Column(Integer)

# ─── Feature 1: Health Records & Lab Results ────────────────────────────────

class HealthRecord(Base):
    __tablename__ = "health_records"

    record_id = Column(String, primary_key=True, index=True)
    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), unique=True, nullable=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    doctor_id = Column(String, index=True)
    department = Column(String)
    visit_date = Column(DateTime, index=True)
    diagnosis = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="health_record")
    patient = relationship("Patient", back_populates="health_records")
    lab_results = relationship("LabResult", back_populates="health_record")

class LabResult(Base):
    __tablename__ = "lab_results"

    result_id = Column(String, primary_key=True, index=True)
    record_id = Column(String, ForeignKey("health_records.record_id"), index=True)
    test_name = Column(String)
    value = Column(String)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    status = Column(String, default="normal")  # normal, low, high, critical
    collected_at = Column(DateTime, nullable=True)

    health_record = relationship("HealthRecord", back_populates="lab_results")

# ─── Feature 2: Prescriptions ────────────────────────────────────────────────

class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), nullable=True)
    prescribed_by = Column(String)   # doctor_id
    drug_name = Column(String)
    dosage = Column(String)
    frequency = Column(String)
    duration_days = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)
    refill_status = Column(String, default="none")  # none, requested, approved, dispensed
    prescribed_at = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="prescriptions")

# ─── Feature 3: Notifications ─────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    type = Column(String)            # appointment_reminder, eta_update, lab_ready, refill_approved, message_received
    title = Column(String)
    body = Column(Text)
    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="notifications")

# ─── Feature 4: Secure Messaging ──────────────────────────────────────────────

class MessageThread(Base):
    __tablename__ = "message_threads"

    thread_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    doctor_id = Column(String, index=True)
    subject = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="message_threads")
    messages = relationship("Message", back_populates="thread", order_by="Message.sent_at")

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("message_threads.thread_id"), index=True)
    sender_id = Column(String)       # patient_id or doctor_id
    sender_role = Column(String)     # patient or staff
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

    thread = relationship("MessageThread", back_populates="messages")

# ─── Feature 5: Billing & Payments ────────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), unique=True, nullable=True)
    amount_total = Column(Float)
    amount_paid = Column(Float, default=0.0)
    insurance_adjustment = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, paid, overdue, waived
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="invoices")
    appointment = relationship("Appointment", back_populates="invoice")

# ─── Feature 7: Reviews & Ratings ─────────────────────────────────────────────

class Review(Base):
    __tablename__ = "reviews"

    review_id = Column(String, primary_key=True, index=True)
    appointment_id = Column(String, ForeignKey("appointments.appointment_id"), unique=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    doctor_id = Column(String, index=True)
    rating = Column(Integer)         # 1-5
    comment = Column(Text, nullable=True)
    wait_time_rating = Column(Integer, nullable=True)  # 1-5 specifically for wait time
    created_at = Column(DateTime, default=datetime.utcnow)

    appointment = relationship("Appointment", back_populates="review")
    patient = relationship("Patient", back_populates="reviews")

# ─── Feature 8: Waitlist ───────────────────────────────────────────────────────

class Waitlist(Base):
    __tablename__ = "waitlist"

    waitlist_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), index=True)
    doctor_id = Column(String, index=True)
    department = Column(String)
    preferred_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="waiting")  # waiting, notified, booked, expired

    patient = relationship("Patient", back_populates="waitlist_entries")
