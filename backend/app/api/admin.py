from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user, require_role
from app.logger import LOG_FILE
import os
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/logs", dependencies=[Depends(require_role(["admin"]))])
def get_recent_logs(limit: int = 100):
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    # Simple tailing for demo (not optimal for massive files, but works here)
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
        for line in reversed(lines[-limit:]):
            try:
                logs.append(json.loads(line))
            except:
                pass
    return logs
