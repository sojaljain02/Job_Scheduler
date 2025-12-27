"""
Jobs API Endpoints
Handles job creation, modification, and retrieval
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from app.db.session import get_db_session
from app.services.job_service import JobService
from app.scheduler.cron_utils import CronUtils

router = APIRouter()

class CreateJobRequest(BaseModel):
    """Request model for creating a job"""
    schedule: str = Field(..., description="CRON expression with seconds (6 parts)")
    api_url: HttpUrl = Field(..., description="API endpoint to call")
    execution_type: str = Field(default="AT_LEAST_ONCE", description="Execution semantics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "schedule": "0 */5 * * * *",
                "api_url": "https://api.example.com/webhook",
                "execution_type": "AT_LEAST_ONCE"
            }
        }

class UpdateJobRequest(BaseModel):
    """Request model for updating a job"""
    schedule: Optional[str] = Field(None, description="CRON expression with seconds")
    api_url: Optional[HttpUrl] = Field(None, description="API endpoint to call")
    active: Optional[bool] = Field(None, description="Whether the job is active")

class JobResponse(BaseModel):
    """Response model for job data"""
    job_id: str
    schedule: str
    api_url: str
    execution_type: str
    active: bool
    created_at: str
    updated_at: str
    next_run_time: Optional[str] = None

@router.post("/", response_model=JobResponse, status_code=201)
def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db_session)
):
    """
    Create a new scheduled job
    
    - **schedule**: CRON expression with seconds (e.g., "0 */5 * * * *" for every 5 minutes)
    - **api_url**: The HTTP endpoint to call when the job executes
    - **execution_type**: Execution semantics (default: AT_LEAST_ONCE)
    """
    # Validate CRON expression
    if not CronUtils.validate_cron(request.schedule):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CRON expression: {request.schedule}. Expected format: 'second minute hour day month weekday'"
        )
    
    # Create job
    job = JobService.create_job(
        db=db,
        schedule=request.schedule,
        api_url=str(request.api_url),
        execution_type=request.execution_type
    )
    
    # Calculate next run time
    try:
        next_run = CronUtils.get_next_run_time(job.schedule)
        next_run_str = next_run.isoformat()
    except Exception:
        next_run_str = None
    
    return JobResponse(
        **job.to_dict(),
        next_run_time=next_run_str
    )

@router.get("/", response_model=List[JobResponse])
def list_jobs(
    active: Optional[bool] = None,
    db: Session = Depends(get_db_session)
):
    """
    List all jobs with optional filtering
    
    - **active**: Filter by active status (optional)
    """
    jobs = JobService.list_jobs(db, active=active)
    
    result = []
    for job in jobs:
        try:
            next_run = CronUtils.get_next_run_time(job.schedule)
            next_run_str = next_run.isoformat()
        except Exception:
            next_run_str = None
        
        result.append(JobResponse(
            **job.to_dict(),
            next_run_time=next_run_str
        ))
    
    return result

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific job by ID"""
    job = JobService.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        next_run = CronUtils.get_next_run_time(job.schedule)
        next_run_str = next_run.isoformat()
    except Exception:
        next_run_str = None
    
    return JobResponse(
        **job.to_dict(),
        next_run_time=next_run_str
    )

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: str,
    request: UpdateJobRequest,
    db: Session = Depends(get_db_session)
):
    """
    Update an existing job
    
    - **schedule**: New CRON expression (optional)
    - **api_url**: New API endpoint (optional)
    - **active**: Enable/disable the job (optional)
    """
    # Validate CRON if provided
    if request.schedule and not CronUtils.validate_cron(request.schedule):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CRON expression: {request.schedule}"
        )
    
    # Update job
    job = JobService.update_job(
        db=db,
        job_id=job_id,
        schedule=request.schedule,
        api_url=str(request.api_url) if request.api_url else None,
        active=request.active
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        next_run = CronUtils.get_next_run_time(job.schedule)
        next_run_str = next_run.isoformat()
    except Exception:
        next_run_str = None
    
    return JobResponse(
        **job.to_dict(),
        next_run_time=next_run_str
    )

@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Delete a job (soft delete by setting active=False)
    """
    success = JobService.delete_job(db, job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return None