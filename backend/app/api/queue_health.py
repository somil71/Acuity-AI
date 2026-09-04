from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.queue_health_service import get_dept_queue_health

router = APIRouter()

DEPARTMENTS = ['Cardiology', 'General Physician', 'Orthopedics', 'Pediatrics']

@router.get("/")
def get_all_queue_health(db: Session = Depends(get_db)):
    return [get_dept_queue_health(db, dept) for dept in DEPARTMENTS]

@router.get("/{department}")
def get_queue_health(department: str, db: Session = Depends(get_db)):
    return get_dept_queue_health(db, department)
