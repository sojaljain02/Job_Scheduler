"""
Executions API Endpoints
Handles retrieval of job execution history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.db.session import get_db_session
from app.services.execution_service import ExecutionService

router = APIRouter()

class ExecutionResponse(BaseModel):
    """Response model for execution data"""
    execution_id: str
    job_id: str
    scheduled_time: str
    actual_start_time: Optional[str]
    status: str
    http_status: Optional[int]
    duration_ms: Optional[int]
    drift_ms: Optional[int]
    error_message: Optional[str]
    created_at: str

@router.get("/{job_id}", response_model=List[ExecutionResponse])
def get_job_executions(
    job_id: str,
    limit: int = Query(default=5, ge=1, le=100, description="Number of executions to return"),
    db: Session = Depends(get_db_session)
):
    """
    Get execution history for a specific job
    
    Returns the most recent executions sorted by creation time (newest first)
    
    - **job_id**: The job ID to get executions for
    - **limit**: Maximum number of executions to return (default: 5, max: 100)
    """
    executions = ExecutionService.get_job_executions(db, job_id, limit=limit)
    
    if not executions:
        # Check if job exists
        from app.services.job_service import JobService
        job = JobService.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    return [ExecutionResponse(**exec.to_dict()) for exec in executions]

@router.get("/{job_id}/latest", response_model=ExecutionResponse)
def get_latest_execution(
    job_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get the most recent execution for a job
    
    - **job_id**: The job ID to get the latest execution for
    """
    execution = ExecutionService.get_latest_execution(db, job_id)
    
    if not execution:
        # Check if job exists
        from app.services.job_service import JobService
        job = JobService.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=404, detail="No executions found for this job")
    
    return ExecutionResponse(**execution.to_dict())

@router.get("/{job_id}/stats")
def get_execution_stats(
    job_id: str,
    db: Session = Depends(get_db_session)
):
    """
    Get execution statistics for a job
    
    Returns aggregated stats including success rate, average duration, and average drift
    
    - **job_id**: The job ID to get statistics for
    """
    stats = ExecutionService.get_execution_stats(db, job_id)
    
    if stats["total_executions"] == 0:
        # Check if job exists
        from app.services.job_service import JobService
        job = JobService.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    return stats