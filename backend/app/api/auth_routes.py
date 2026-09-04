from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db import get_db
from app.models.schema import User
from app.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_password_hash

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.post("/token")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role, "user_id": user.id}

@router.post("/demo/seed")
def seed_demo_users(db: Session = Depends(get_db)):
    """Seed demo users for the synthetic demo."""
    if db.query(User).first():
        return {"msg": "Users already seeded"}
    
    users = [
        User(id="admin1", email="admin@test.com", hashed_password=get_password_hash("admin"), role="admin", name="Admin"),
        User(id="DOC_CAR_1", email="doc_car@test.com", hashed_password=get_password_hash("doc"), role="staff", name="Dr. Heart"),
        User(id="DOC_GEN_1", email="doc_gen@test.com", hashed_password=get_password_hash("doc"), role="staff", name="Dr. Gen"),
        User(id="PAT_0", email="pat0@test.com", hashed_password=get_password_hash("pat"), role="patient", name="Patient Zero"),
        User(id="PAT_1", email="pat1@test.com", hashed_password=get_password_hash("pat"), role="patient", name="Patient One"),
    ]
    db.add_all(users)
    db.commit()
    return {"msg": "Demo users seeded"}
