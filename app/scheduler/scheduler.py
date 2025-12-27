"""
Priority Queue Based Job Scheduler
Manages job scheduling using a heap-based priority queue
"""
import heapq
import time
import threading
from datetime import datetime
from typing import List, Tuple
from app.db.session import get_db
from app.models.job import Job
from app.scheduler.cron_utils import CronUtils
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ScheduledJob:
    """Represents a job with its next scheduled time"""
    def __init__(self, job_id: str, next_run: datetime, schedule: str, api_url: str):
        self.job_id = job_id
        self.next_run = next_run
        self.schedule = schedule
        self.api_url = api_url
    
    def __lt__(self, other):
        """Comparison for heap ordering (earliest time first)"""
        return self.next_run < other.next_run
    
    def __repr__(self):
        return f"ScheduledJob(job_id={self.job_id}, next_run={self.next_run})"


class Scheduler:
    """
    Core scheduler using priority queue (min-heap)
    Continuously loads jobs, schedules them, and dispatches to worker pool
    """
    
    def __init__(self, worker_pool, refresh_interval: int = 60):
        """
        Initialize scheduler
        
        Args:
            worker_pool: WorkerPool instance for job execution
            refresh_interval: How often to reload jobs from DB (seconds)
        """
        self.worker_pool = worker_pool
        self.refresh_interval = refresh_interval
        self.priority_queue: List[ScheduledJob] = []
        self.is_running = False
        self.lock = threading.Lock()
        logger.info("Scheduler initialized")
    
    def load_active_jobs(self) -> List[Job]:
        """Load all active jobs from database"""
        with get_db() as db:
            jobs = db.query(Job).filter(Job.active == True).all()
            logger.info(f"Loaded {len(jobs)} active jobs from database")
            return jobs
    
    def refresh_schedule(self):
        """Reload jobs and rebuild priority queue"""
        logger.info("Refreshing job schedule...")
        jobs = self.load_active_jobs()
        
        with self.lock:
            self.priority_queue.clear()
            
            now = datetime.now()
            for job in jobs:
                try:
                    # Calculate next run time for each job
                    next_run = CronUtils.get_next_run_time(job.schedule, now)
                    scheduled_job = ScheduledJob(
                        job_id=str(job.job_id),
                        next_run=next_run,
                        schedule=job.schedule,
                        api_url=job.api_url
                    )
                    heapq.heappush(self.priority_queue, scheduled_job)
                    logger.debug(f"Scheduled job {job.job_id} for {next_run}")
                except Exception as e:
                    logger.error(f"Error scheduling job {job.job_id}: {str(e)}")
            
            logger.info(f"Schedule refreshed with {len(self.priority_queue)} jobs")
    
    def run(self):
        """Main scheduler loop"""
        self.is_running = True
        logger.info("Scheduler started")
        
        last_refresh = time.time()
        
        while self.is_running:
            try:
                # Refresh jobs periodically
                if time.time() - last_refresh >= self.refresh_interval:
                    self.refresh_schedule()
                    last_refresh = time.time()
                
                # Check if there are jobs to process
                with self.lock:
                    if not self.priority_queue:
                        time.sleep(1)
                        continue
                    
                    # Peek at the next job (don't pop yet)
                    next_job = self.priority_queue[0]
                
                now = datetime.now()
                
                # If the job is due, execute it
                if next_job.next_run <= now:
                    with self.lock:
                        # Pop the job from queue
                        job = heapq.heappop(self.priority_queue)
                    
                    logger.info(f"Dispatching job {job.job_id} to worker pool")
                    
                    # Submit to worker pool for execution
                    self.worker_pool.submit_job(
                        job_id=job.job_id,
                        api_url=job.api_url,
                        scheduled_time=job.next_run
                    )
                    
                    # Calculate and reschedule for next run
                    try:
                        next_run = CronUtils.get_next_run_time(job.schedule, now)
                        rescheduled_job = ScheduledJob(
                            job_id=job.job_id,
                            next_run=next_run,
                            schedule=job.schedule,
                            api_url=job.api_url
                        )
                        with self.lock:
                            heapq.heappush(self.priority_queue, rescheduled_job)
                        logger.debug(f"Rescheduled job {job.job_id} for {next_run}")
                    except Exception as e:
                        logger.error(f"Error rescheduling job {job.job_id}: {str(e)}")
                else:
                    # Sleep until next job or for a max of 1 second
                    sleep_time = min((next_job.next_run - now).total_seconds(), 1.0)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}", exc_info=True)
                time.sleep(1)
        
        logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler...")
        self.is_running = False