import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

from mcp_tools.llm_client import LLMProvider, call_llm
from mlflow_ops.data_aggregator import DataAggregator

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    def __init__(self, prompts_file: str = "d:/email_auto/mlflow_ops/prompts.yaml"):
        self.aggregator = DataAggregator()
        with open(prompts_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
            self.prompts = yaml_data.get("prompts", {})

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        try:
            response = call_llm(
                provider=LLMProvider.GEMINI,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # Keep temperature low for structured JSON output
                max_tokens=1024,
                model_override="gemini-2.5-flash"
            )
            # Find JSON block if backticks exist, else parse directly
            text = response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Failed to generate analytics insights: {e}")
            return {"error": str(e), "raw_response": response if 'response' in locals() else ""}

    async def generate_performance_summary(self) -> Dict[str, Any]:
        data = await self.aggregator.get_performance_summary(hours=24)
        prompt_config = self.prompts.get("performance_summary", {})
        sys_prompt = prompt_config.get("system_prompt", "")
        usr_prompt = prompt_config.get("user_prompt", "").format(
            time_period="24h",
            input_data_json=json.dumps(data, indent=2)
        )
        return self._call_gemini(sys_prompt, usr_prompt)

    async def run_anomaly_detection(self) -> Dict[str, Any]:
        data = await self.aggregator.get_anomaly_metrics()
        prompt_config = self.prompts.get("anomaly_detection", {})
        sys_prompt = prompt_config.get("system_prompt", "")
        usr_prompt = prompt_config.get("user_prompt", "").format(
            current_metrics_json=json.dumps(data.get("current_metrics", {}), indent=2),
            historical_baseline_json=json.dumps(data.get("historical_baseline", {}), indent=2)
        )
        return self._call_gemini(sys_prompt, usr_prompt)

    async def generate_dashboard_insights(self) -> Dict[str, Any]:
        data = await self.aggregator.get_dashboard_snapshot()
        prompt_config = self.prompts.get("dashboard_insights", {})
        sys_prompt = prompt_config.get("system_prompt", "")
        usr_prompt = prompt_config.get("user_prompt", "").format(
            metrics_snapshot_json=json.dumps(data, indent=2)
        )
        return self._call_gemini(sys_prompt, usr_prompt)
