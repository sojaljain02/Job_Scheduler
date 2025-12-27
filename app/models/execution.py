"""
Job Execution Model - Database model for execution history
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class JobExecution(Base):
    """Job execution record"""
    __tablename__ = "job_executions"
    
    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.job_id"), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    actual_start_time = Column(DateTime(timezone=True))
    status = Column(String(50))
    http_status = Column(Integer)
    duration_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        drift_ms = None
        if self.scheduled_time and self.actual_start_time:
            drift_ms = int((self.actual_start_time - self.scheduled_time).total_seconds() * 1000)
        
        return {
            "execution_id": str(self.execution_id),
            "job_id": str(self.job_id),
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "actual_start_time": self.actual_start_time.isoformat() if self.actual_start_time else None,
            "status": self.status,
            "http_status": self.http_status,
            "duration_ms": self.duration_ms,
            "drift_ms": drift_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }