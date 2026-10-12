"""Validated API with startup readiness and privacy-preserving request logs."""
import json
import logging
import secrets
import time
import uuid
import threading
import os
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict, model_validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from src.config import Settings
from src.predict import PredictionService

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("risk_api")
REQUESTS = Counter("risk_requests_total", "API requests", ["route", "status"])
LATENCY = Histogram("risk_request_seconds", "API latency", ["route"])
FALLBACKS = Counter("risk_explanation_fallback_total", "Explanation fallbacks")

class CustomerData(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    age: int = Field(ge=18, le=100)
    income: float = Field(ge=0, le=1e12)
    loan_amount: float = Field(ge=0, le=1e12)
    credit_score: int = Field(ge=300, le=900)
    num_previous_defaults: int = Field(ge=0, le=10)
    employment_years: float = Field(ge=0, le=50)
    @model_validator(mode="after")
    def consistent_employment(self):
        if self.employment_years > self.age - 18:
            raise ValueError("Employment years cannot exceed years since age 18")
        return self

def create_app(settings=None):
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        app.state.predictor = None
        try:
            app.state.predictor = PredictionService(settings)
        except Exception as error:
            logger.error(json.dumps({"event": "model_load_failed", "error_type": type(error).__name__}))
        yield
    admission_lock = threading.Lock()
    recent_requests = deque()
    max_requests = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
    inference_slots = threading.BoundedSemaphore(int(os.getenv("MAX_CONCURRENT_PREDICTIONS", "4")))
    app = FastAPI(title="Risk Insights", version="2.0.0", lifespan=lifespan)

    def authorize(request: Request):
        if settings.api_key and not secrets.compare_digest(request.headers.get("X-API-Key", ""), settings.api_key):
            raise HTTPException(401, "Invalid API key")

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        # Pydantic errors normally echo customer values; omit them.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in error.errors()]})

    @app.middleware("http")
    async def observe(request, call_next):
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        response = await call_next(request)
        route = request.scope.get("route")
        route = route.path if route else "unmatched"
        elapsed = time.monotonic() - started
        REQUESTS.labels(route, str(response.status_code)).inc()
        LATENCY.labels(route).observe(elapsed)
        predictor = getattr(app.state, "predictor", None)
        logger.info(json.dumps({"request_id": request_id, "route": route,
            "status": response.status_code, "latency_ms": round(elapsed * 1000, 2),
            "model_version": predictor.version if predictor else None}))
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health")
    def health():
        predictor = getattr(app.state, "predictor", None)
        if predictor is None:
            raise HTTPException(503, "Model unavailable")
        return {"status": "ready", "model_version": predictor.version}

    @app.get("/metrics", dependencies=[Depends(authorize)])
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/predict", dependencies=[Depends(authorize)])
    def predict(customer: CustomerData):
        predictor = getattr(app.state, "predictor", None)
        if predictor is None:
            raise HTTPException(503, "Model unavailable")
        with admission_lock:
            now = time.monotonic()
            while recent_requests and recent_requests[0] <= now - 60:
                recent_requests.popleft()
            if len(recent_requests) >= max_requests:
                raise HTTPException(429, "Request limit exceeded", headers={"Retry-After": "60"})
            recent_requests.append(now)
        if not inference_slots.acquire(blocking=False):
            raise HTTPException(429, "Prediction service busy", headers={"Retry-After": "1"})
        try:
            result = predictor.predict(customer.model_dump())
        except Exception as error:
            logger.error(json.dumps({"event": "prediction_failed", "error_type": type(error).__name__}))
            raise HTTPException(500, "Prediction unavailable") from None
        finally:
            inference_slots.release()
        if result["explanation_fallback"]:
            FALLBACKS.inc()
        return result
    return app

app = create_app()
