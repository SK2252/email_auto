from pydantic import BaseModel
from typing import Dict, Any, List

class PerformanceSummaryResponse(BaseModel):
    executive_summary: str = ""
    key_findings: List[str] = []
    alerts: List[Dict[str, str]] = []
    recommendations: List[str] = []
    performance_score: float = 0.0

class AnomalyDetectionResponse(BaseModel):
    anomalies_detected: List[Dict[str, Any]] = []
    system_health: str = "healthy"
    confidence_level: float = 1.0

class CostOptimizationResponse(BaseModel):
    current_monthly_cost: float = 0.0
    optimization_opportunities: List[Dict[str, Any]] = []
    estimated_monthly_savings: float = 0.0
    roi_timeline_days: int = 0
    overall_efficiency_score: float = 100.0

class ModelComparisonResponse(BaseModel):
    winner: str = ""
    comparison_summary: str = ""
    detailed_comparison: List[Dict[str, Any]] = []
    recommendation: str = ""
    migration_effort: str = ""
    expected_impact: str = ""

class DashboardInsightsResponse(BaseModel):
    health_status: str = "🟢 Healthy"
    headline: str = ""
    key_metrics: List[Dict[str, str]] = []
    trending: str = ""
    next_steps: List[str] = []
