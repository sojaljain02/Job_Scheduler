"""
Execution Service - Business logic for execution history
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import uuid
from app.models.execution import JobExecution
from datetime import datetime

class ExecutionService:
    """Service for execution history operations"""
    
    @staticmethod
    def get_job_executions(
        db: Session,
        job_id: str,
        limit: int = 5
    ) -> List[JobExecution]:
        """Get execution history for a job"""
        try:
            job_uuid = uuid.UUID(job_id)
            return (
                db.query(JobExecution)
                .filter(JobExecution.job_id == job_uuid)
                .order_by(desc(JobExecution.created_at))
                .limit(limit)
                .all()
            )
        except ValueError:
            return []
    
    @staticmethod
    def get_latest_execution(
        db: Session,
        job_id: str
    ) -> Optional[JobExecution]:
        """Get the most recent execution for a job"""
        try:
            job_uuid = uuid.UUID(job_id)
            return (
                db.query(JobExecution)
                .filter(JobExecution.job_id == job_uuid)
                .order_by(desc(JobExecution.created_at))
                .first()
            )
        except ValueError:
            return None
    
    @staticmethod
    def get_execution_stats(db: Session, job_id: str) -> dict:
        """Get aggregated execution statistics for a job"""
        try:
            job_uuid = uuid.UUID(job_id)
            
            # Get all executions for stats
            executions = (
                db.query(JobExecution)
                .filter(JobExecution.job_id == job_uuid)
                .all()
            )
            
            if not executions:
                return {
                    "job_id": job_id,
                    "total_executions": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 0.0,
                    "avg_duration_ms": None,
                    "avg_drift_ms": None
                }
            
            # Calculate statistics
            total = len(executions)
            success = sum(1 for e in executions if e.status == "SUCCESS")
            failed = total - success
            
            # Calculate average duration (only for successful executions)
            durations = [e.duration_ms for e in executions if e.duration_ms is not None]
            avg_duration = sum(durations) / len(durations) if durations else None
            
            # Calculate average drift
            drifts = []
            for e in executions:
                if e.scheduled_time and e.actual_start_time:
                    drift = (e.actual_start_time - e.scheduled_time).total_seconds() * 1000
                    drifts.append(drift)
            avg_drift = sum(drifts) / len(drifts) if drifts else None
            
            return {
                "job_id": job_id,
                "total_executions": total,
                "success_count": success,
                "failure_count": failed,
                "success_rate": round(success / total * 100, 2),
                "avg_duration_ms": int(avg_duration) if avg_duration else None,
                "avg_drift_ms": int(avg_drift) if avg_drift else None
            }
        except ValueError:
            return {
                "job_id": job_id,
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": None,
                "avg_drift_ms": None
            }