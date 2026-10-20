import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import connect_db, close_db, ensure_indexes, client
from .logging_config import setup_logging
from .model_loader import load_model, get_model_info, model_status
from .routers import auth, llm, patients, predictions

setup_logging(debug=settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await ensure_indexes()
    load_model()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

logger = logging.getLogger("airway.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if settings.enforce_https:
        scheme = (
            request.headers.get("x-forwarded-proto")
            if settings.behind_proxy
            else request.url.scheme
        )
        if scheme != "https":
            return JSONResponse(status_code=403, content={"detail": "HTTPS required"})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    return response


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled %s %s", request.method, request.url.path,
            extra={"request_id": request_id},
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %s", request.method, request.url.path, response.status_code,
        extra={"request_id": request_id, "duration_ms": duration_ms},
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(llm.router)
app.include_router(patients.router)
app.include_router(predictions.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/live")
async def live():
    return {"status": "alive", "version": settings.app_version}


@app.get("/ready")
async def ready():
    checks: dict = {}
    try:
        await client.admin.command("ping")
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"fail: {exc.__class__.__name__}"
    checks["model"] = model_status()
    checks["model_info"] = get_model_info()
    ready_ok = checks["db"] == "ok" and checks["model"] == "ok"
    return JSONResponse(
        status_code=200 if ready_ok else 503,
        content={
            "status": "ready" if ready_ok else "not_ready",
            "checks": checks,
            "version": settings.app_version,
        },
    )
