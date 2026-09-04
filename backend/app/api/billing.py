from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_db
from app.auth import get_current_user, require_role
from app.models.schema import Invoice, User

router = APIRouter()

# --- Pydantic Schemas ---------------------------------------------------------

class InvoiceCreate(BaseModel):
    appointment_id: str
    patient_id: str
    amount_total: float = Field(..., gt=0)
    insurance_adjustment: float = Field(default=0.0, ge=0)
    due_date: Optional[datetime] = None

# --- Routes -------------------------------------------------------------------

@router.get("/")
def list_my_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all invoices for the current patient (patients see only their own).
    Staff/admin can also call this but it still returns only invoices for the
    authenticated user; widen this filter if an admin list-all endpoint is needed.
    """
    invoices = (
        db.query(Invoice)
        .filter(Invoice.patient_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )
    return [
        {
            "invoice_id": inv.invoice_id,
            "patient_id": inv.patient_id,
            "appointment_id": inv.appointment_id,
            "amount_total": inv.amount_total,
            "amount_paid": inv.amount_paid,
            "insurance_adjustment": inv.insurance_adjustment,
            "status": inv.status,
            "due_date": inv.due_date,
            "created_at": inv.created_at,
            "paid_at": inv.paid_at,
        }
        for inv in invoices
    ]


@router.post("/", dependencies=[Depends(require_role(["staff", "admin"]))])
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff or admin creates an invoice for an appointment."""
    invoice_id = str(uuid.uuid4())
    invoice = Invoice(
        invoice_id=invoice_id,
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
        amount_total=payload.amount_total,
        amount_paid=0.0,
        insurance_adjustment=payload.insurance_adjustment,
        status="pending",
        due_date=payload.due_date,
        created_at=datetime.utcnow(),
        paid_at=None,
    )
    db.add(invoice)
    db.commit()
    return {"msg": "Invoice created", "invoice_id": invoice_id}


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single invoice detail.
    Patients can only view their own; staff/admin can view any.
    """
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role == "patient" and invoice.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this invoice")

    return {
        "invoice_id": invoice.invoice_id,
        "patient_id": invoice.patient_id,
        "appointment_id": invoice.appointment_id,
        "amount_total": invoice.amount_total,
        "amount_paid": invoice.amount_paid,
        "insurance_adjustment": invoice.insurance_adjustment,
        "status": invoice.status,
        "due_date": invoice.due_date,
        "created_at": invoice.created_at,
        "paid_at": invoice.paid_at,
    }


@router.post("/{invoice_id}/pay")
def pay_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mock payment: set status to 'paid', record paid_at, and compute amount_paid.

    amount_paid = amount_total - insurance_adjustment
    """
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role == "patient" and invoice.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this invoice")

    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()
    invoice.amount_paid = max(0.0, invoice.amount_total - invoice.insurance_adjustment)
    db.commit()

    return {
        "msg": "Payment processed",
        "invoice_id": invoice_id,
        "amount_paid": invoice.amount_paid,
        "paid_at": invoice.paid_at,
    }
