"""
Debug API - Ad-hoc execution endpoints for testing
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
import uuid
from typing import Dict, Any
# Import worker_pool at runtime inside handlers to avoid importing a stale None value at module import time
import requests
from app.db.session import get_db
from app.models.job import Job

router = APIRouter()

class RunNowRequest(BaseModel):
    api_url: HttpUrl = Field(..., description="API endpoint to call immediately")

@router.post("/execute", status_code=202)
def run_now(request: RunNowRequest) -> Dict[str, Any]:
    """Trigger an immediate execution to test worker pool"""
    # Obtain worker_pool at runtime so we don't rely on a module-level snapshot
    from app import main as app_main
    if not hasattr(app_main, 'worker_pool') or not app_main.worker_pool:
        raise HTTPException(status_code=503, detail="Worker pool not available")

    job_id = str(uuid.uuid4())
    scheduled_time = datetime.now()

    # Create a temporary job DB record (inactive) so executions can be recorded (satisfy FK)
    try:
        with get_db() as db:
            temp_job = Job(
                job_id=uuid.UUID(job_id),
                schedule="0 * * * * *",
                api_url=str(request.api_url),
                execution_type="AT_LEAST_ONCE",
                active=False
            )
            db.add(temp_job)
            # commit handled by context manager
            logger = None
    except Exception:
        # If job creation fails, log but continue to submit execution (DB write will likely error)
        import logging
        logging.getLogger(__name__).exception("Failed to create temporary job for debug execution")

    # Submit job to worker pool for immediate execution
    app_main.worker_pool.submit_job(job_id=job_id, api_url=str(request.api_url), scheduled_time=scheduled_time)

    return {
        "job_id": job_id,
        "api_url": str(request.api_url),
        "scheduled_time": scheduled_time.isoformat(),
        "status": "SUBMITTED"
    }

@router.post("/execute_sync", status_code=200)
def run_now_sync(request: RunNowRequest) -> Dict[str, Any]:
    """Synchronously execute the POST so container network and TLS can be tested"""
    try:
        start = datetime.now()
        resp = requests.post(
            str(request.api_url),
            json={"test": "ping"},
            timeout=15
        )
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        snippet = None
        try:
            snippet = (resp.text or "")[:1000]
        except Exception:
            snippet = None

        return {
            "status": "OK",
            "http_status": resp.status_code,
            "duration_ms": duration_ms,
            "response_snippet": snippet
        }
    except requests.exceptions.SSLError as e:
        raise HTTPException(status_code=502, detail=f"SSL error: {str(e)}")
    except requests.exceptions.Timeout as e:
        raise HTTPException(status_code=504, detail=f"Timeout: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/refresh_schedule", status_code=200)
def refresh_schedule() -> dict:
    """Trigger scheduler to refresh its job schedule immediately (for testing)"""
    from app import main as app_main
    if not hasattr(app_main, 'scheduler') or not app_main.scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    try:
        app_main.scheduler.refresh_schedule()
        return {"status": "SCHEDULE_REFRESHED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh schedule: {str(e)}")
