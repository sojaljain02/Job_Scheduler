# Job Scheduler System

A distributed, scalable job scheduler with CRON support (second-level precision), built with FastAPI, PostgreSQL, and Python.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Start services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f scheduler
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up postgres -d

# Run migrations
psql -h localhost -U postgres -d job_scheduler -f migrations/001_init.sql

# Set environment
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/job_scheduler"

# Start application
uvicorn app.main:app --reload
```

API available at: http://localhost:8000

## 📡 API Examples

### Create a Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": "0 */5 * * * *",
    "api_url": "https://httpbin.org/post",
    "execution_type": "AT_LEAST_ONCE"
  }'
```

### List Jobs

```bash
curl http://localhost:8000/api/v1/jobs
```

### Get Execution History

```bash
curl http://localhost:8000/api/v1/executions/{job_id}?limit=10
```

### Get Execution Stats

```bash
curl http://localhost:8000/api/v1/executions/{job_id}/stats
```

## 🎯 Features

- ✅ **CRON with seconds** - 6-part expressions (e.g., `0 */5 * * * *`)
- ✅ **Priority queue scheduling** - O(log n) performance using min-heap
- ✅ **AT_LEAST_ONCE semantics** - Automatic retries with exponential backoff
- ✅ **Drift tracking** - Monitors scheduling accuracy
- ✅ **Execution history** - Complete audit trail with statistics
- ✅ **Thread pool execution** - Concurrent job processing
- ✅ **Health monitoring** - Built-in health check endpoint

## 📊 CRON Expression Format

```
second minute hour day month weekday

Examples:
0 * * * * *         → Every minute
0 */5 * * * *       → Every 5 minutes
*/30 * * * * *      → Every 30 seconds
0 0 9 * * 1-5       → 9 AM on weekdays
0 0 0 * * *         → Daily at midnight
```

## 🗂️ Project Structure

```
job-scheduler/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── api/
│   │   ├── jobs.py          # Jobs CRUD endpoints
│   │   └── executions.py    # Execution history endpoints
│   ├── scheduler/
│   │   ├── scheduler.py     # Priority queue scheduler
│   │   └── cron_utils.py    # CRON parsing utilities
│   ├── executor/
│   │   └── worker.py        # Worker pool with HTTP execution
│   ├── models/
│   │   ├── job.py           # Job database model
│   │   └── execution.py     # Execution database model
│   ├── db/
│   │   ├── base.py          # SQLAlchemy base
│   │   └── session.py       # Database session management
│   ├── services/
│   │   ├── job_service.py   # Job business logic
│   │   └── execution_service.py  # Execution business logic
│   └── utils/
│       └── logger.py        # Logging configuration
├── migrations/
│   └── 001_init.sql         # Database schema
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🏗️ System Design

**Overview:** The system is composed of a small set of cooperating components that provide scheduling, execution, and observability for HTTP-based jobs.

- **API (FastAPI)** — Job CRUD, executions queries, debug endpoints.
- **Scheduler** — Priority queue (min-heap) that computes next run times using croniter and submits work to the WorkerPool.
- **WorkerPool** — ThreadPoolExecutor executing HTTP requests (configurable `MAX_WORKERS`).
- **Database (Postgres)** — Stores `jobs` and `job_executions` for audit and stats.
- **Monitoring / Observability** — Prometheus metrics, Postgres exporter, and Grafana dashboards for RPS, latency, success rate and queue depth.

**Architectural flow (text):**

API → JobService → Postgres  
Scheduler (refreshes from Postgres or notified by JobService) → Priority Queue → WorkerPool → HTTP Target → Execution recorded in Postgres

---

## 🔁 Data Flow

1. **Create job:** Client POSTs to `/api/v1/jobs`; `JobService` validates and inserts a `jobs` row (`job_id`, `schedule`, `api_url`, `active`, ...).
2. **Discover & materialize:** Scheduler refreshes active jobs (startup / interval / notification) and materializes required fields in-memory.
3. **Compute next run:** Scheduler uses `croniter` to compute the next execution time and pushes an entry onto the priority queue.
4. **Dispatch:** When due, scheduler pops the job and submits it to the `WorkerPool`. A `job_executions` row is created with `PENDING` and `started_at` on dispatch.
5. **Execute & record:** Worker performs the HTTP request, captures HTTP status, latency and response (truncated) and updates the execution row with `SUCCESS`/`FAILED`, `attempts`, `finished_at`.
6. **Retries:** On failure, worker retries using exponential backoff (controlled by `MAX_RETRIES` and `REQUEST_TIMEOUT`).

**Schema highlights:**
- `jobs` (job_id, schedule, api_url, execution_type, active, created_at)
- `job_executions` (execution_id, job_id, status, http_status, attempt, started_at, finished_at, response)

---

## 🧭 API Design

**Principles:** RESTful, predictable responses, asynchronous execution semantics, use of `202 Accepted` for queued ops, and clear error codes for validation and server errors.

**Key endpoints:**
- `POST /api/v1/jobs` — Create a job. Returns `201 Created` with job JSON.
- `GET /api/v1/jobs` — List jobs (pagination supported).
- `GET /api/v1/jobs/{job_id}` — Retrieve a single job (`200` or `404`).
- `PUT /api/v1/jobs/{job_id}` — Update job (`200`, `400`, or `404`).
- `DELETE /api/v1/jobs/{job_id}` — Delete job (`204` or `404`).
- `POST /api/v1/debug/execute` — Trigger immediate one-off execution (`202 Accepted` with execution id).
- `POST /api/v1/debug/refresh_schedule` — Force scheduler to reload active jobs (`200 OK`).
- `GET /api/v1/executions/{job_id}` — List executions for a job (`200 OK`).
- `GET /api/v1/executions/{job_id}/latest` — Latest execution for job (`200` or `404`).

**Errors & retry semantics:**
- Validation errors: `400` with JSON details.
- Execution semantics are **AT_LEAST_ONCE** for retryable jobs; for high-throughput tests set `MAX_RETRIES=0` to avoid amplifying load.

---

## 🔧 Configuration

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Tuning Parameters

Edit in code:
- `MAX_WORKERS=20` - Concurrent job execution threads
- `REQUEST_TIMEOUT=30` - HTTP request timeout (seconds)
- `MAX_RETRIES=3` - Retry attempts on failure
- `REFRESH_INTERVAL=60` - Job refresh from DB (seconds)

## 📈 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Key Metrics to Monitor

1. **Success rate** - % of successful executions
2. **Average drift** - Scheduling accuracy (should be <1s)
3. **Execution duration** - HTTP response times
4. **Failed jobs** - Jobs requiring attention

### Logs

```bash
# View real-time logs
docker-compose logs -f scheduler

# Filter by level
docker-compose logs scheduler | grep ERROR
```

## 🎨 Design Decisions

### Priority Queue vs Polling

**✅ Chosen: Priority Queue (min-heap)**
- O(log n) insertion/extraction
- Sleep until next job (efficient)
- Deterministic ordering

### Thread Pool vs Process Pool

**✅ Chosen: ThreadPoolExecutor**
- Lower overhead
- Perfect for I/O-bound HTTP requests
- Easy state sharing

### Retry Strategy

**Exponential backoff with max 3 retries:**
- Attempt 1: Immediate
- Attempt 2: +2s
- Attempt 3: +4s  
- Attempt 4: +8s

Prevents thundering herd, gives services time to recover.

### Drift Tracking

Tracks `scheduled_time` vs `actual_start_time`:
- <1s: Excellent
- 1-5s: Good
- >10s: Investigate system load

## 🧪 Testing

```bash
# Create test job (every minute)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": "0 * * * * *",
    "api_url": "https://httpbin.org/post"
  }'

# Watch executions
JOB_ID="<job_id_from_response>"
watch -n 5 curl http://localhost:8000/api/v1/executions/$JOB_ID
```

## 🚧 Scaling Considerations

**Current:** Single scheduler instance

**For horizontal scaling:**
- Add distributed lock (Redis/etcd)
- Use leader election (Consul/ZooKeeper)
- Or consider: Kubernetes CronJobs, Celery Beat, Temporal

**Vertical scaling:**
- Increase `MAX_WORKERS`
- Tune PostgreSQL connection pool
- Add read replicas for execution queries

## 📝 Common Issues

### Job not executing
- Check job is `active=true`
- Verify CRON expression is valid
- Check scheduler logs for errors

### High drift
- System overloaded (reduce MAX_WORKERS)
- Database slow (check query performance)
- Target API slow (check timeouts)

### Retries exhausted
- Target API down (check URL)
- Network issues
- Timeout too short

## 🤝 Contributing

1. Follow existing code structure
2. Add tests for new features
3. Update README with changes
4. Use conventional commits

## 📄 License

MIT License

---

**Built with FastAPI + PostgreSQL + Python**