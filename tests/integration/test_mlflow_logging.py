import pytest
import asyncio
from agents.agent_metrics import instrument_agent

@instrument_agent("TEST_AG")
async def dummy_agent_func(state):
    return {"status": "success", "confidence": 0.99}

@pytest.mark.asyncio
async def test_agent_logging_integration():
    try:
        res = await dummy_agent_func({"email_id": "integration_test"})
        assert res["status"] == "success"
    except Exception as e:
        pytest.fail(f"Logging integration failed: {str(e)}")
