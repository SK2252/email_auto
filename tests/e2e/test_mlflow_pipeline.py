import pytest
from mlflow_ops.data_aggregator import DataAggregator

@pytest.mark.asyncio
async def test_e2e_data_aggregation_pipeline():
    aggregator = DataAggregator()
    try:
        data = await aggregator.get_performance_summary(1)
        assert isinstance(data, dict)
        assert "agents" in data
    except Exception as e:
        pytest.fail(f"Database E2E pipeline failed: {str(e)}")
