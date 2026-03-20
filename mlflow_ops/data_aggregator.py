import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import asyncpg
from config.settings import settings

logger = logging.getLogger(__name__)

class DataAggregator:
    def __init__(self):
        self.db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    
    async def get_db_connection(self):
        return await asyncpg.connect(self.db_url)

    async def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Gathers performance data for PROMPT-A1 (Performance Summary).
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        since_ms = int(since.timestamp() * 1000)

        # We query the mlflow tables directly as requested by the plan.
        query = """
        SELECT
            p_agent.value AS agent_id,
            COUNT(DISTINCT r.run_uuid) AS total_runs,
            AVG(m_time.value) AS avg_duration_ms,
            SUM(CASE WHEN m_succ.value = 1 THEN 1 ELSE 0 END)::float / COUNT(DISTINCT r.run_uuid) AS success_rate,
            AVG(m_conf.value) AS avg_confidence
        FROM runs r
        JOIN params p_agent ON r.run_uuid = p_agent.run_uuid AND p_agent.key = 'agent_id'
        LEFT JOIN metrics m_time ON r.run_uuid = m_time.run_uuid AND m_time.key LIKE '%/execution_time_ms'
        LEFT JOIN metrics m_succ ON r.run_uuid = m_succ.run_uuid AND m_succ.key LIKE '%/success'
        LEFT JOIN metrics m_conf ON r.run_uuid = m_conf.run_uuid AND m_conf.key = 'confidence'
        WHERE r.start_time >= $1
        GROUP BY p_agent.value
        """
        
        conn = await self.get_db_connection()
        try:
            rows = await conn.fetch(query, since_ms)
            agents_data = []
            total_processed = 0
            for r in rows:
                agents_data.append({
                    "agent_id": r["agent_id"],
                    "total_runs": r["total_runs"],
                    "avg_duration_ms": float(r["avg_duration_ms"]) if r["avg_duration_ms"] is not None else 0.0,
                    "success_rate": float(r["success_rate"]) if r["success_rate"] is not None else 0.0,
                    "avg_confidence": float(r["avg_confidence"]) if r["avg_confidence"] is not None else 0.0,
                })
                total_processed += r["total_runs"]
            
            return {
                "agents": agents_data,
                "time_period": f"{hours}h",
                "llm_models": ["groq", "gemini"], # Simplified
                "total_emails_processed": total_processed,
                "critical_alerts": [] 
            }
        except Exception as e:
            logger.error(f"Failed to aggregate performance data: {e}")
            return {}
        finally:
            await conn.close()

    async def get_anomaly_metrics(self) -> Dict[str, Any]:
        """
        Gathers anomaly data for PROMPT-A2.
        Current (last 5 mins) vs Baseline (last 30 days)
        """
        now = datetime.now(timezone.utc)
        five_mins_ago = int((now - timedelta(minutes=5)).timestamp() * 1000)
        thirty_days_ago = int((now - timedelta(days=30)).timestamp() * 1000)

        query = """
        SELECT
            p_agent.value AS agent_id,
            COUNT(DISTINCT r.run_uuid) AS total_runs,
            AVG(m_time.value) AS avg_duration_ms,
            SUM(CASE WHEN m_succ.value = 1 THEN 1 ELSE 0 END)::float / GREATEST(COUNT(DISTINCT r.run_uuid), 1) AS success_rate,
            AVG(m_conf.value) AS avg_confidence,
            SUM(CASE WHEN m_succ.value = 0 THEN 1 ELSE 0 END) AS error_count
        FROM runs r
        JOIN params p_agent ON r.run_uuid = p_agent.run_uuid AND p_agent.key = 'agent_id'
        LEFT JOIN metrics m_time ON r.run_uuid = m_time.run_uuid AND m_time.key LIKE '%/execution_time_ms'
        LEFT JOIN metrics m_succ ON r.run_uuid = m_succ.run_uuid AND m_succ.key LIKE '%/success'
        LEFT JOIN metrics m_conf ON r.run_uuid = m_conf.run_uuid AND m_conf.key = 'confidence'
        WHERE r.start_time >= $1 AND r.start_time <= $2
        GROUP BY p_agent.value
        """
        
        conn = await self.get_db_connection()
        try:
            current_rows = await conn.fetch(query, five_mins_ago, int(now.timestamp() * 1000))
            baseline_rows = await conn.fetch(query, thirty_days_ago, five_mins_ago)
            
            current_metrics = {}
            for r in current_rows:
                current_metrics[r["agent_id"]] = {
                    "avg_latency_ms": float(r["avg_duration_ms"]) if r["avg_duration_ms"] else 0.0,
                    "success_rate": float(r["success_rate"]) if r["success_rate"] else 0.0,
                    "confidence": float(r["avg_confidence"]) if r["avg_confidence"] else 0.0,
                    "error_count": r["error_count"]
                }
            
            baseline_metrics = {}
            for r in baseline_rows:
                baseline_metrics[r["agent_id"]] = {
                    "avg_latency_ms": float(r["avg_duration_ms"]) if r["avg_duration_ms"] else 0.0,
                    "success_rate": float(r["success_rate"]) if r["success_rate"] else 0.0,
                    "confidence": float(r["avg_confidence"]) if r["avg_confidence"] else 0.0,
                    "error_count": r["error_count"]
                }

            return {
                "current_metrics": current_metrics,
                "historical_baseline": baseline_metrics
            }
        except Exception as e:
            logger.error(f"Failed to aggregate anomaly data: {e}")
            return {"current_metrics": {}, "historical_baseline": {}}
        finally:
            await conn.close()

    async def get_dashboard_snapshot(self) -> Dict[str, Any]:
        """
        Gathers snapshot data for PROMPT-A5.
        Similar to performance summary but for the immediate overarching timeframe (e.g. 24h).
        """
        summary = await self.get_performance_summary(hours=24)
        
        # We need mock or aggregate sentiment/escalation metrics since they aren't directly in MLflow yet
        # or we fetch from emails table
        # Simplified for now
        return {
            "agents": summary.get("agents", []),
            "sentiment_avg": -0.1, 
            "low_confidence_count": sum(1 for a in summary.get("agents", []) if a.get("avg_confidence", 1.0) < 0.8),
            "escalated_count": 0,
            "total_processed": summary.get("total_emails_processed", 0)
        }
