from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.mlflow_service import MLFlowService
from app.models.mlflow_schemas import (
    PerformanceSummaryResponse,
    AnomalyDetectionResponse,
    CostOptimizationResponse,
    ModelComparisonResponse,
    DashboardInsightsResponse
)
import logging
import time

router = APIRouter(prefix="/mlflow", tags=["mlflow"])
logger = logging.getLogger(__name__)

# Simple in-memory cache and rate limiter for Phase 4
class SimpleCacheRateLimiter:
    def __init__(self):
        self.cache = {}
        self.rate_limit = {} 

    def check_rate_limit(self, ip: str):
        now = time.time()
        if ip not in self.rate_limit:
            self.rate_limit[ip] = []
        self.rate_limit[ip] = [t for t in self.rate_limit[ip] if now - t < 60]
        if len(self.rate_limit[ip]) >= 20: # 20 req/min
            raise HTTPException(status_code=429, detail="Too many requests")
        self.rate_limit[ip].append(now)

    async def get_cached(self, key: str, ttl: int, func):
        now = time.time()
        if key in self.cache:
            val, ext = self.cache[key]
            if now < ext:
                return val
        val = await func()
        self.cache[key] = (val, now + ttl)
        return val

cache_limiter = SimpleCacheRateLimiter()

def get_mlflow_service():
    return MLFlowService()

def apply_rate_limit(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    cache_limiter.check_rate_limit(ip)

@router.get("/performance", response_model=PerformanceSummaryResponse, dependencies=[Depends(apply_rate_limit)])
async def get_performance_summary(service: MLFlowService = Depends(get_mlflow_service)):
    try:
        return await cache_limiter.get_cached("performance", 60, service.get_performance_summary)
    except Exception as e:
        logger.error(f"Error fetching performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies", response_model=AnomalyDetectionResponse, dependencies=[Depends(apply_rate_limit)])
async def get_anomaly_detection(service: MLFlowService = Depends(get_mlflow_service)):
    try:
        # Anomalies should be real-time, short TTL
        return await cache_limiter.get_cached("anomalies", 10, service.get_anomaly_detection)
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost", response_model=CostOptimizationResponse, dependencies=[Depends(apply_rate_limit)])
async def get_cost_optimization(service: MLFlowService = Depends(get_mlflow_service)):
    try:
        return await cache_limiter.get_cached("cost", 3600, service.get_cost_optimization)
    except Exception as e:
        logger.error(f"Error fetching cost optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-compare", response_model=ModelComparisonResponse, dependencies=[Depends(apply_rate_limit)])
async def get_model_comparison(service: MLFlowService = Depends(get_mlflow_service)):
    try:
        return await cache_limiter.get_cached("model-compare", 3600, service.get_model_comparison)
    except Exception as e:
        logger.error(f"Error fetching model comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_model=DashboardInsightsResponse, dependencies=[Depends(apply_rate_limit)])
async def get_dashboard_insights(service: MLFlowService = Depends(get_mlflow_service)):
    try:
        # Dashboard is real-time, 15s cache
        return await cache_limiter.get_cached("dashboard", 15, service.get_dashboard_insights)
    except Exception as e:
        logger.error(f"Error fetching dashboard insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
