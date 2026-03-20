import asyncio
import json
import os
from config.settings import settings
from mlflow_ops.data_aggregator import DataAggregator
from mlflow_ops.analytics_engine import AnalyticsEngine

async def main():
    engine = AnalyticsEngine()
    
    print("Fetching aggregated data from Supabase...")
    data = await engine.aggregator.get_dashboard_snapshot()
    print("Aggregated data:", json.dumps(data, indent=2))
    
    print("Running Analytics Engine Gemini Call...")
    insights = await engine.generate_dashboard_insights()
    print("Dashboard Insights:", json.dumps(insights, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
