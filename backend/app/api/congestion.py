from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.congestion_service import get_congestion_forecast
from pydantic import BaseModel

router = APIRouter()

class ForecastRequest(BaseModel):
    features: dict

@router.get("/live")
def get_live_congestion(db: Session = Depends(get_db)):
    return get_congestion_forecast(db)

@router.get("/live/{department}")
def get_live_congestion_dept(department: str, db: Session = Depends(get_db)):
    res = get_congestion_forecast(db, department)
    return res[0] if res else None

@router.post("/forecast")
def post_forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    # ML inference not fully implemented yet
    return {"message": "Not implemented"}
