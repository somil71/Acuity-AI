from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import Notification, User

router = APIRouter()

# --- Helper -------------------------------------------------------------------

def create_notification(
    db: Session,
    patient_id: str,
    type: str,
    title: str,
    body: str,
    appointment_id: Optional[str] = None,
    scheduled_for: Optional[datetime] = None,
) -> Notification:
    """Create and persist a notification record.  Returns the new Notification object.

    Import this helper in other modules to fire notifications without
    duplicating DB logic::

        from app.api.notifications import create_notification
        create_notification(db, patient_id=..., type="lab_ready",
                            title="Lab results available", body="Your results are ready.")
    """
    notification = Notification(
        notification_id=str(uuid.uuid4()),
        patient_id=patient_id,
        type=type,
        title=title,
        body=body,
        appointment_id=appointment_id,
        is_read=False,
        created_at=datetime.utcnow(),
        scheduled_for=scheduled_for,
        sent_at=None,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

# --- Routes -------------------------------------------------------------------

# NOTE: /unread-count is declared BEFORE /{notification_id}/read so FastAPI
# does not mistake the literal "unread-count" for a path parameter.

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the count of unread notifications for the current user."""
    count = (
        db.query(Notification)
        .filter(
            Notification.patient_id == current_user.id,
            Notification.is_read == False,
        )
        .count()
    )
    return {"unread_count": count}


@router.get("/")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all notifications for the current user, sorted newest first."""
    notifications = (
        db.query(Notification)
        .filter(Notification.patient_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [
        {
            "notification_id": n.notification_id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "appointment_id": n.appointment_id,
            "is_read": n.is_read,
            "created_at": n.created_at,
            "scheduled_for": n.scheduled_for,
            "sent_at": n.sent_at,
        }
        for n in notifications
    ]


@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    notification = (
        db.query(Notification)
        .filter(Notification.notification_id == notification_id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    notification.is_read = True
    db.commit()
    return {"msg": "Notification marked as read", "notification_id": notification_id}


@router.delete("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications for the current user as read."""
    unread = (
        db.query(Notification)
        .filter(
            Notification.patient_id == current_user.id,
            Notification.is_read == False,
        )
        .all()
    )
    for n in unread:
        n.is_read = True
    db.commit()
    return {"msg": f"{len(unread)} notifications marked as read"}
