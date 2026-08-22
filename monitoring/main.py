import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from monitoring.service import availability_monitor_loop, get_drift_report, get_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(availability_monitor_loop(stop_event))

    try:
        yield
    finally:
        stop_event.set()
        task.cancel()

        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="MLOps Monitoring Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "monitoring",
    }


@app.get("/metrics")
def metrics():
    return get_metrics()


@app.get("/drift")
def drift():
    return get_drift_report()
