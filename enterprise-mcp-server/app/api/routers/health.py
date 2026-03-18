"""
Health check endpoints: /health/live and /health/ready.
Used by Kubernetes probes and monitoring systems.
"""

from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.core.health_checks import check_liveness, check_readiness

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness():
    """
    Liveness probe — is the process alive?
    Returns 200 as long as the server is responding.
    """
    result = await check_liveness()
    return JSONResponse(status_code=200, content=result)


@router.get("/ready")
async def readiness():
    """
    Readiness probe — can the server accept traffic?
    Checks Redis and Firestore connectivity.
    """
    result = await check_readiness()
    status_code = 200 if result["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=result)
