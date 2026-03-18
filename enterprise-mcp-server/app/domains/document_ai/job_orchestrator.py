
from typing import Dict, Any, Optional
from app.core.job_queue import job_queue
from app.core.logging import get_logger

logger = get_logger(__name__)

async def submit_job(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Submit a tool execution job for async processing.
    Returns the Job ID.
    """
    logger.info(f"Submitting async job for tool: {tool_name}")
    job_id = await job_queue.enqueue_job(tool_name, arguments)
    return job_id

async def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status and result of an async job.
    """
    try:
        status = await job_queue.get_job_status(job_id)
        if not status:
            return {"status": "NOT_FOUND", "error": "Job ID not found"}
        return status
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return {"status": "ERROR", "error": str(e)}
