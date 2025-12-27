"""
Worker Pool for Job Execution
Handles HTTP calls to job endpoints with retry logic
"""
import time
import uuid
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from app.db.session import get_db
from app.models.execution import JobExecution
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class WorkerPool:
    """
    Thread pool for executing HTTP requests
    Implements AT_LEAST_ONCE semantics with retries
    """
    
    def __init__(self, max_workers: int = 20, timeout: int = 30, max_retries: int = 3):
        """
        Initialize worker pool
        
        Args:
            max_workers: Maximum number of concurrent workers
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.timeout = timeout
        self.max_retries = max_retries
        logger.info(f"Worker pool initialized with {max_workers} workers")
    
    def submit_job(self, job_id: str, api_url: str, scheduled_time: datetime):
        """
        Submit a job for execution
        
        Args:
            job_id: Unique job identifier
            api_url: URL to call
            scheduled_time: When the job was scheduled to run
        """
        self.executor.submit(self._execute_job, job_id, api_url, scheduled_time)
    
    def _execute_job(self, job_id: str, api_url: str, scheduled_time: datetime):
        """
        Execute a job with retry logic and record results
        
        This method implements AT_LEAST_ONCE semantics:
        - Retries on failure up to max_retries times
        - Records all execution attempts
        """
        execution_id = str(uuid.uuid4())
        actual_start_time = datetime.now()
        
        logger.info(f"Executing job {job_id} (execution_id={execution_id})")
        
        # Calculate drift
        drift_ms = int((actual_start_time - scheduled_time).total_seconds() * 1000)
        logger.debug(f"Job {job_id} drift: {drift_ms}ms")
        
        attempt = 0
        last_error = None
        
        while attempt <= self.max_retries:
            attempt += 1
            
            try:
                # Record start time for this attempt
                start_time = time.time()
                
                # Make HTTP POST request
                response = requests.post(
                    api_url,
                    json={
                        "job_id": job_id,
                        "execution_id": execution_id,
                        "scheduled_time": scheduled_time.isoformat(),
                        "actual_time": actual_start_time.isoformat()
                    },
                    timeout=self.timeout
                )
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Check response status
                if response.status_code >= 200 and response.status_code < 300:
                    # Success
                    self._record_execution(
                        execution_id=execution_id,
                        job_id=job_id,
                        scheduled_time=scheduled_time,
                        actual_start_time=actual_start_time,
                        status="SUCCESS",
                        http_status=response.status_code,
                        duration_ms=duration_ms,
                        error_message=None
                    )
                    logger.info(f"Job {job_id} executed successfully (attempt {attempt})")
                    return
                else:
                    # HTTP error status
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"Job {job_id} returned {response.status_code} (attempt {attempt})")
            
            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                logger.warning(f"Job {job_id} timed out (attempt {attempt})")
            
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(f"Job {job_id} request failed: {str(e)} (attempt {attempt})")
            
            except Exception as e:
                last_error = str(e)
                logger.error(f"Job {job_id} unexpected error: {str(e)} (attempt {attempt})")
            
            # Wait before retry (exponential backoff)
            if attempt <= self.max_retries:
                backoff = min(2 ** attempt, 30)  # Max 30 seconds
                time.sleep(backoff)
        
        # All retries exhausted
        self._record_execution(
            execution_id=execution_id,
            job_id=job_id,
            scheduled_time=scheduled_time,
            actual_start_time=actual_start_time,
            status="FAILED",
            http_status=None,
            duration_ms=None,
            error_message=last_error
        )
        logger.error(f"Job {job_id} failed after {self.max_retries + 1} attempts: {last_error}")
    
    def _record_execution(
        self,
        execution_id: str,
        job_id: str,
        scheduled_time: datetime,
        actual_start_time: datetime,
        status: str,
        http_status: Optional[int],
        duration_ms: Optional[int],
        error_message: Optional[str]
    ):
        """Record job execution in database"""
        try:
            with get_db() as db:
                execution = JobExecution(
                    execution_id=uuid.UUID(execution_id),
                    job_id=uuid.UUID(job_id),
                    scheduled_time=scheduled_time,
                    actual_start_time=actual_start_time,
                    status=status,
                    http_status=http_status,
                    duration_ms=duration_ms,
                    error_message=error_message
                )
                db.add(execution)
                db.commit()
                logger.debug(f"Recorded execution {execution_id}")
        except Exception as e:
            logger.error(f"Failed to record execution {execution_id}: {str(e)}")
    
    def is_active(self) -> bool:
        """Check if worker pool is active"""
        return not self.executor._shutdown
    
    def stop(self):
        """Shutdown worker pool gracefully"""
        logger.info("Shutting down worker pool...")
        self.executor.shutdown(wait=True)
        logger.info("Worker pool shut down")
    
    def start(self):
        """Start worker pool (initialization)"""
        logger.info("Worker pool ready")