"""Load test script to hit /api/v1/debug/execute at a target rate per second.
Usage: python tools/load_test.py --rate 1000 --duration 10 --receiver http://receiver:9000/ok

Notes:
- Use host.docker.internal or receiver (docker service name) depending on where you run the script.
"""
import asyncio
import aiohttp
import time
import argparse

async def send(session, url, receiver, sem):
    payload = {"api_url": receiver}
    async with sem:
        try:
            async with session.post(url, json=payload, timeout=10) as resp:
                return resp.status
        except Exception as e:
            return f"ERR:{e}"

async def run(rate, duration, url, receiver, concurrency):
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as sess:
        start = time.time()
        total = rate * duration
        sent = 0
        for sec in range(duration):
            tasks = [asyncio.create_task(send(sess, url, receiver, sem)) for _ in range(rate)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            sent += len(results)
            ok = sum(1 for r in results if r == 202 or r == 200)
            errs = len(results) - ok
            print(f"Second {sec+1}: sent={len(results)} ok={ok} errors={errs}")
        elapsed = time.time() - start
        print(f"Finished: sent={sent} target={total} elapsed={elapsed:.2f}s rps={sent/elapsed:.2f}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rate", type=int, default=1000, help="Requests per second")
    p.add_argument("--duration", type=int, default=10, help="Duration in seconds")
    p.add_argument("--url", type=str, default="http://localhost:8000/api/v1/debug/execute", help="Scheduler debug execute URL")
    p.add_argument("--receiver", type=str, default="http://receiver:9000/ok", help="Receiver URL to send as api_url payload")
    p.add_argument("--concurrency", type=int, default=500, help="Max concurrent in-flight requests")
    args = p.parse_args()

    asyncio.run(run(args.rate, args.duration, args.url, args.receiver, args.concurrency))