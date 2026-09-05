# Deployment and Operations Guide

## Backups
Since this MVP uses SQLite as its primary persistent store (configured via `DATABASE_URL=sqlite:///./hospital.db`), a full data backup is as simple as copying the file from the volume.

**To perform a backup on a live system:**
```bash
# 1. Ensure any running writes flush or pause if possible (SQLite locks handles writes, but file copy might catch it mid-transaction. Better to use the built-in backup CLI for safety)
sqlite3 hospital.db ".backup 'hospital_backup_$(date +%Y%m%d).db'"
```

**To restore a backup:**
```bash
# 1. Stop the backend service
docker-compose stop backend
# 2. Replace the DB file
cp hospital_backup_20260904.db hospital.db
# 3. Restart the service
docker-compose start backend
```

## Security & PII
- User accounts (including patients) use strict bcrypt hashing.
- **Sensitive Demographics/Notes:** Currently, patient demographics (Age, Gender) are grouped in `schema.Patient`. In a larger system, these would be logically separated or encrypted at rest via PostgreSQL's `pgcrypto` or application-level AES encryption before writing to disk.
- Logs (`system_events.jsonl`) intentionally do *not* contain patient names or contact info, relying solely on UUID `patient_id`s to ensure GDPR/HIPAA compliance in telemetry.
