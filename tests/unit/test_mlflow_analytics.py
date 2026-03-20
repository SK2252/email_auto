import pytest
from unittest.mock import AsyncMock, MagicMock
from mlflow_ops.analytics_engine import AnalyticsEngine

@pytest.mark.asyncio
async def test_performance_summary_generation():
    engine = AnalyticsEngine()
    engine.aggregator.get_performance_summary = AsyncMock(return_value={"agents": []})
    engine._call_gemini = MagicMock(return_value={"executive_summary": "Test OK"})
    
    result = await engine.generate_performance_summary()
    assert result.get("executive_summary") == "Test OK"
    engine.aggregator.get_performance_summary.assert_called_once()

@pytest.mark.asyncio
async def test_anomaly_detection_generation():
    engine = AnalyticsEngine()
    engine.aggregator.get_anomaly_metrics = AsyncMock(return_value={"current_metrics": {}, "historical_baseline": {}})
    engine._call_gemini = MagicMock(return_value={"system_health": "degraded"})
    
    result = await engine.run_anomaly_detection()
    assert result.get("system_health") == "degraded"
    engine.aggregator.get_anomaly_metrics.assert_called_once()
