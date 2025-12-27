"""
Job Service - Business logic for job management
"""
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from app.models.job import Job
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class JobService:
    """Service for job management operations"""
    
    @staticmethod
    def create_job(
        db: Session,
        schedule: str,
        api_url: str,
        execution_type: str = "AT_LEAST_ONCE"
    ) -> Job:
        """Create a new job"""
        job = Job(
            job_id=uuid.uuid4(),
            schedule=schedule,
            api_url=api_url,
            execution_type=execution_type,
            active=True
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Created job {job.job_id}")
        return job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        try:
            job_uuid = uuid.UUID(job_id)
            return db.query(Job).filter(Job.job_id == job_uuid).first()
        except ValueError:
            return None
    
    @staticmethod
    def list_jobs(db: Session, active: Optional[bool] = None) -> List[Job]:
        """List all jobs with optional filtering"""
        query = db.query(Job)
        
        if active is not None:
            query = query.filter(Job.active == active)
        
        return query.order_by(Job.created_at.desc()).all()
    
    @staticmethod
    def update_job(
        db: Session,
        job_id: str,
        schedule: Optional[str] = None,
        api_url: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Optional[Job]:
        """Update an existing job"""
        job = JobService.get_job(db, job_id)
        
        if not job:
            return None
        
        if schedule is not None:
            job.schedule = schedule
        if api_url is not None:
            job.api_url = api_url
        if active is not None:
            job.active = active
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Updated job {job.job_id}")
        return job
    
    @staticmethod
    def delete_job(db: Session, job_id: str) -> bool:
        """Delete a job (soft delete by setting active=False)"""
        job = JobService.get_job(db, job_id)
        
        if not job:
            return False
        
        job.active = False
        db.commit()
        
        logger.info(f"Deleted job {job.job_id}")
        return True