from fastapi import FastAPI, Request
from uvicorn import run

app = FastAPI()

@app.post("/ok")
async def ok(req: Request):
    # Return immediately with 200 to simulate fast webhook receiver
    return {"status": "ok"}

if __name__ == "__main__":
    run("test_receiver:app", host="0.0.0.0", port=9000, log_level="warning")