
import json
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.infrastructure.cache.redis_client import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

JOB_QUEUE_KEY = "mcp:jobs:queue"
JOB_STATUS_PREFIX = "mcp:jobs:status:"
JOB_RESULT_TTL = 3600  # 1 hour

class JobQueue:
    """
    Redis-backed Job Queue for async tool execution.
    """
    
    @staticmethod
    async def enqueue_job(tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Submit a job to the queue. Returns Job ID.
        """
        client = await get_redis()
        if not client:
             raise Exception("Redis not available")
             
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "tool": tool_name,
            "args": arguments,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            # 1. Store initial status
            await client.set(f"{JOB_STATUS_PREFIX}{job_id}", json.dumps(job_data), ex=JOB_RESULT_TTL)
            
            # 2. Push to queue (Right Push)
            await client.rpush(JOB_QUEUE_KEY, job_id)
            
            logger.info("Job enqueued", job_id=job_id, tool=tool_name)
            return job_id
            
        except Exception as e:
            logger.error("Failed to enqueue job", error=str(e))
            raise

    @staticmethod
    async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status/result.
        """
        client = await get_redis()
        if not client: return None
        
        data = await client.get(f"{JOB_STATUS_PREFIX}{job_id}")
        if data:
            try:
                return json.loads(data)
            except:
                return None
        return None

    @staticmethod
    async def update_job_status(job_id: str, status: str, result: Any = None, error: str = None):
        """
        Update job status (Running/Completed/Failed).
        """
        client = await get_redis()
        if not client: return

        key = f"{JOB_STATUS_PREFIX}{job_id}"
        data_str = await client.get(key)
        
        if not data_str:
            logger.warning("Attempted to update non-existent job", job_id=job_id)
            return
            
        try:
            data = json.loads(data_str)
        except:
             return

        data["status"] = status
        data["updated_at"] = datetime.utcnow().isoformat()
        
        if result:
            data["result"] = result
        if error:
            data["error"] = error
            
        await client.set(key, json.dumps(data), ex=JOB_RESULT_TTL)

    @staticmethod
    async def dequeue_job() -> Optional[str]:
        """
        Blocking pop from queue. Returns Job ID.
        """
        client = await get_redis()
        if not client:
            return None
            
        try:
            # BLPOP returns (key, value) tuple
            result = await client.blpop(JOB_QUEUE_KEY, timeout=5)
            if result:
                return result[1] # decode_responses=True handled by client
        except Exception as e:
            # logger.error("Dequeue error", error=str(e))
            return None
        return None

job_queue = JobQueue()
