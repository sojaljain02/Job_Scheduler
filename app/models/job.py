"""
Job Model - Database model for scheduled jobs
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class Job(Base):
    """Job model representing a scheduled job"""
    __tablename__ = "jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule = Column(Text, nullable=False)
    api_url = Column(Text, nullable=False)
    execution_type = Column(String(50), nullable=False, default="AT_LEAST_ONCE")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            "job_id": str(self.job_id),
            "schedule": self.schedule,
            "api_url": self.api_url,
            "execution_type": self.execution_type,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }