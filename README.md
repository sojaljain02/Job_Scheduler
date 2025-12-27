# Job Scheduler System

A distributed, scalable job scheduler with CRON support (second-level precision), built with FastAPI, PostgreSQL, and Python.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FastAPI App                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │  Jobs API   │  │Executions   │  │  Health Check    │   │
│  │  Endpoints  │  │    API      │  │                  │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┴──────────────────┐
        │                                       │
┌───────▼────────┐                   ┌─────────▼────────┐
│   Scheduler    │                   │   Worker Pool    │
│  (Priority Q)  │──────────────────▶│  (Thread Pool)   │
│                │   Submit Jobs     │                  │
└───────┬────────┘                   └─────────┬────────┘
        │                                      │
        │ Load Jobs                            │ Execute & Record
        │                                      │
┌───────▼──────────────────────────────────────▼────────┐
│              PostgreSQL Database                      │
│  ┌──────────┐              ┌──────────────────┐     │
│  │   Jobs   │              │  Job Executions  │     │
│  │  Table   │              │      Table       │     │
│  └──────────┘              └──────────────────┘     │
└───────────────────────────────────────────────────────┘
```

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