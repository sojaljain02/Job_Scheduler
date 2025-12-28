"""
FastAPI Job Scheduler - Main Application Entry Point
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import threading
from app.api.jobs import router as jobs_router
from app.api.executions import router as executions_router
from app.scheduler.scheduler import Scheduler
from app.executor.worker import WorkerPool
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global instances
scheduler = None
worker_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global scheduler, worker_pool
    
    # Startup
    logger.info("Starting Job Scheduler application...")
    
    # Initialize worker pool
    worker_pool = WorkerPool(max_workers=20)
    worker_pool.start()
    
    # Initialize scheduler
    scheduler = Scheduler(worker_pool)
    scheduler_thread = threading.Thread(target=scheduler.run, daemon=True)
    scheduler_thread.start()
    
    logger.info("Job Scheduler started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Job Scheduler...")
    if scheduler:
        scheduler.stop()
    if worker_pool:
        worker_pool.stop()
    logger.info("Job Scheduler stopped")

app = FastAPI(
    title="Job Scheduler",
    description="A distributed job scheduler with CRON support and execution tracking",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(executions_router, prefix="/api/v1/executions", tags=["Executions"])
# Debug endpoints (useful for testing in non-production environments)
try:
    from app.api.debug import router as debug_router
    app.include_router(debug_router, prefix="/api/v1/debug", tags=["Debug"])
except Exception:
    # Don't fail startup if debug router is missing
    pass

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "UP",
        "scheduler_running": scheduler.is_running if scheduler else False,
        "worker_pool_active": worker_pool.is_active() if worker_pool else False
    }

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Job Scheduler API",
        "docs": "/docs",
        "health": "/health"
    }