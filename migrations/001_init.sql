-- Initial database schema for job scheduler

-- Jobs table: stores scheduled jobs
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY,
    schedule TEXT NOT NULL,
    api_url TEXT NOT NULL,
    execution_type TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Job executions table: stores execution history
CREATE TABLE job_executions (
    execution_id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(job_id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP NOT NULL,
    actual_start_time TIMESTAMP,
    status TEXT,
    http_status INTEGER,
    duration_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_jobs_active ON jobs(active) WHERE active = TRUE;
CREATE INDEX idx_job_exec_job_time ON job_executions(job_id, created_at DESC);
CREATE INDEX idx_job_exec_status ON job_executions(status);
CREATE INDEX idx_job_exec_scheduled ON job_executions(scheduled_time);

-- Comments for documentation
COMMENT ON TABLE jobs IS 'Scheduled jobs configuration';
COMMENT ON TABLE job_executions IS 'Job execution history and results';
COMMENT ON COLUMN jobs.schedule IS 'CRON expression with seconds (6 parts): second minute hour day month weekday';
COMMENT ON COLUMN jobs.execution_type IS 'Execution semantics: AT_LEAST_ONCE guarantees retry on failure';
COMMENT ON COLUMN job_executions.scheduled_time IS 'Originally scheduled time (for drift calculation)';
COMMENT ON COLUMN job_executions.actual_start_time IS 'Actual execution start time';
COMMENT ON COLUMN job_executions.duration_ms IS 'HTTP request duration in milliseconds';