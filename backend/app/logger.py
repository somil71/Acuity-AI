import logging
import json
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'system_events.jsonl')

class JSONLFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

logger = logging.getLogger("hospital_ml")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(JSONLFormatter())
    logger.addHandler(file_handler)

def log_prediction(doctor_id, department, current_time, patients_ahead, p10, p50, p90, trigger_event=None):
    logger.info("Prediction recomputed", extra={'extra_data': {
        "event_type": "prediction_recompute",
        "doctor_id": doctor_id,
        "department": department,
        "queue_size": len(patients_ahead),
        "predicted_p10": p10,
        "predicted_p50": p50,
        "predicted_p90": p90,
        "trigger_event": trigger_event
    }})

def log_event(event_type, payload):
    logger.info(f"Event: {event_type}", extra={'extra_data': {
        "event_type": event_type,
        "payload": payload
    }})
