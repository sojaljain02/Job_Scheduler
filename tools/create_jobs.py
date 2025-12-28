"""Utility to create many scheduled jobs via the scheduler API.
Usage: python tools/create_jobs.py --count 1000 --receiver http://receiver:9000/ok
"""
import requests
import argparse

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--receiver", type=str, default="http://receiver:9000/ok")
    p.add_argument("--url", type=str, default="http://localhost:8000/api/v1/jobs")
    args = p.parse_args()

    created = []
    for i in range(args.count):
        payload = {
            "schedule": "*/1 * * * * *",
            "api_url": args.receiver,
            "execution_type": "AT_LEAST_ONCE"
        }
        try:
            r = requests.post(args.url, json=payload, timeout=5)
            if r.status_code == 201:
                job = r.json()
                created.append(job["job_id"])
            else:
                print(f"Create failed {i}: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"Exception creating job {i}: {e}")
    print(f"Created {len(created)} jobs")