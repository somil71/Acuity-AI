from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.db import engine, Base
from app.models import schema
from app.api import (
    appointments,
    patients,
    auth_routes,
    admin,
    records,
    prescriptions,
    notifications,
    messages,
    reviews,
    billing,
    triage,
    noshowrisk,
    anomaly,
    queue_health,
    congestion,
    bottleneck,
)
from app.api.auth_routes import limiter

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Wait Time Prediction API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Existing routers ---------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(admin.router)
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])

# --- New feature routers ------------------------------------------------------
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(prescriptions.router, prefix="/api/prescriptions", tags=["prescriptions"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])

# --- Analytics & Operational Intelligence -------------------------------------
app.include_router(queue_health.router, prefix="/api/queue-health", tags=["queue-health"])
app.include_router(congestion.router, prefix="/api/congestion", tags=["congestion"])
app.include_router(bottleneck.router, prefix="/api/bottleneck", tags=["bottleneck"])

# --- ML routers ---------------------------------------------------------------
app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
app.include_router(noshowrisk.router, prefix="/api/appointments", tags=["noshowrisk"])
app.include_router(anomaly.router, prefix="/api/anomaly", tags=["anomaly"])
