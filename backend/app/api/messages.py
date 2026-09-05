from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import MessageThread, Message, User

router = APIRouter()

# --- Pydantic Schemas ---------------------------------------------------------

class ThreadCreate(BaseModel):
    doctor_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    first_message: str = Field(..., min_length=1)

class ReplyCreate(BaseModel):
    body: str = Field(..., min_length=1)

# --- Routes -------------------------------------------------------------------

@router.get("/threads")
def list_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all message threads for the current user.
    Patients see threads where they are the patient.
    Staff/admin see threads where they are the doctor participant.
    """
    if current_user.role == "patient":
        threads = (
            db.query(MessageThread)
            .filter(MessageThread.patient_id == current_user.id)
            .order_by(MessageThread.last_message_at.desc())
            .all()
        )
    else:
        # staff or admin: show threads where they are the doctor
        threads = (
            db.query(MessageThread)
            .filter(MessageThread.doctor_id == current_user.id)
            .order_by(MessageThread.last_message_at.desc())
            .all()
        )

    return [
        {
            "thread_id": t.thread_id,
            "patient_id": t.patient_id,
            "doctor_id": t.doctor_id,
            "subject": t.subject,
            "created_at": t.created_at,
            "last_message_at": t.last_message_at,
        }
        for t in threads
    ]


@router.post("/threads", dependencies=[Depends(require_role(["patient"]))])
def create_thread(
    payload: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patient creates a new message thread with a doctor, including the opening message."""
    thread_id = str(uuid.uuid4())
    now = datetime.utcnow()

    thread = MessageThread(
        thread_id=thread_id,
        patient_id=current_user.id,
        doctor_id=payload.doctor_id,
        subject=payload.subject,
        created_at=now,
        last_message_at=now,
    )
    db.add(thread)

    # Add the first message immediately
    message = Message(
        message_id=str(uuid.uuid4()),
        thread_id=thread_id,
        sender_id=current_user.id,
        sender_role="patient",
        body=payload.first_message,
        sent_at=now,
        is_read=False,
    )
    db.add(message)
    db.commit()

    return {"msg": "Thread created", "thread_id": thread_id}


@router.get("/threads/{thread_id}")
def get_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a thread with all its messages. Only participants (patient or doctor) can access it."""
    thread = db.query(MessageThread).filter(MessageThread.thread_id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Authorisation: must be the patient or the doctor in this thread
    if current_user.id not in (thread.patient_id, thread.doctor_id):
        raise HTTPException(status_code=403, detail="Not a participant in this thread")

    messages = [
        {
            "message_id": m.message_id,
            "sender_id": m.sender_id,
            "sender_role": m.sender_role,
            "body": m.body,
            "sent_at": m.sent_at,
            "is_read": m.is_read,
        }
        for m in thread.messages
    ]

    return {
        "thread_id": thread.thread_id,
        "patient_id": thread.patient_id,
        "doctor_id": thread.doctor_id,
        "subject": thread.subject,
        "created_at": thread.created_at,
        "last_message_at": thread.last_message_at,
        "messages": messages,
    }


@router.post("/threads/{thread_id}/reply")
def reply_to_thread(
    thread_id: str,
    payload: ReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a reply to an existing thread. Only participants can reply."""
    thread = db.query(MessageThread).filter(MessageThread.thread_id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if current_user.id not in (thread.patient_id, thread.doctor_id):
        raise HTTPException(status_code=403, detail="Not a participant in this thread")

    now = datetime.utcnow()
    sender_role = current_user.role if current_user.role in ("patient", "staff", "admin") else "staff"

    message = Message(
        message_id=str(uuid.uuid4()),
        thread_id=thread_id,
        sender_id=current_user.id,
        sender_role=sender_role,
        body=payload.body,
        sent_at=now,
        is_read=False,
    )
    db.add(message)
    thread.last_message_at = now
    db.commit()

    # NLP Auto-Responder: Real Machine Learning Intent Classification
    if current_user.role == "patient":
        from datetime import timedelta
        import joblib
        import os
        import numpy as np
        
        try:
            # Load the trained scikit-learn NLP pipeline
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            model_path = os.path.join(base, 'ml', 'models', 'chat_intent_model.pkl')
            
            nlp_model = joblib.load(model_path)
            
            # Predict probability of each intent
            probs = nlp_model.predict_proba([payload.body])[0]
            best_idx = np.argmax(probs)
            predicted_intent = nlp_model.classes_[best_idx]
            confidence = probs[best_idx]
            
            # If the model isn't confident, fallback to general
            if confidence < 0.35:
                predicted_intent = 'general'
            
            responses = {
                'refill': "I've received your prescription refill request. I will review your file and send the authorization to your pharmacy shortly.",
                'symptoms': "I'm sorry to hear you're experiencing these symptoms. Please monitor them closely. If they worsen rapidly, please head to the ER or book an urgent walk-in.",
                'scheduling': "Regarding your schedule: our front desk can help adjust your appointment times. Feel free to use the booking portal on your dashboard as well.",
                'billing': "For billing and insurance questions, our finance department has been notified and will review your invoice. You can also view your balances in the Billing tab.",
                'records': "Your recent lab and test results are being processed. Once reviewed, they will appear directly in the Health Records tab of your portal.",
                'general': "Thank you for reaching out. I have noted this in your file. We can discuss this in more detail at your next visit."
            }
            
            bot_reply = responses.get(predicted_intent, responses['general'])
            
        except Exception as e:
            # Fallback if model fails to load
            bot_reply = "Thank you for the message. I will review your file shortly."

        auto_msg = Message(
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            sender_id=thread.doctor_id,
            sender_role="staff",
            body=bot_reply,
            sent_at=now + timedelta(seconds=2),
            is_read=False,
        )
        db.add(auto_msg)
        thread.last_message_at = auto_msg.sent_at
        db.commit()

    return {"msg": "Reply sent", "message_id": message.message_id}
