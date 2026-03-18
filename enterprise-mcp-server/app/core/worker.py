
import asyncio
import traceback
from typing import Any
from app.core.job_queue import job_queue
from app.core.logging import get_logger

logger = get_logger(__name__)

STOP_WORKER = False

async def worker_loop(mcp_server: Any):
    """
    Background loop to process jobs from queue.
    """
    global STOP_WORKER
    logger.info("Worker loop started")
    
    while not STOP_WORKER:
        try:
            # 1. Dequeue (blocking wait)
            # The dequeue method uses blpop which blocks, but we need to check STOP_WORKER.
            # dequeue_job currently has 5s timeout.
            
            job_id = await job_queue.dequeue_job()
            
            if not job_id:
                await asyncio.sleep(0.1) # Brief pause
                continue
                
            logger.info("Processing job", job_id=job_id)
            
            # 2. Get Job Details
            job_data = await job_queue.get_job_status(job_id)
            if not job_data:
                logger.error("Job data not found for ID", job_id=job_id)
                continue
                
            tool_name = job_data.get("tool")
            args = job_data.get("args", {})
            
            # 3. Update Status to RUNNING
            await job_queue.update_job_status(job_id, "RUNNING")
            
            # 4. Execute Tool
            try:
                # Use mcp_server.call_tool?
                # FastMCP doesn't expose call_tool directly in public API easily?
                # It has `call_tool(name, arguments)`.
                # We need to find the tool function.
                
                # FastMCP stores tools in self._tool_manager or similar?
                # Actually FastMCP (0.4.1) has `call_tool(name: str, arguments: dict)` method.
                # Let's verify this assumption. 
                # If not, we iterate capabilities.
                
                result = await mcp_server.call_tool(tool_name, arguments=args)
                
                # Result is List[Content]. We serialize it.
                # For simplicity, we just store the first text block if exist.
                # Or JSON serialize the whole result structure.
                
                output = None
                if result and result.content:
                     if hasattr(result.content[0], "text"):
                         output = result.content[0].text
                     else:
                         output = str(result.content)
                
                await job_queue.update_job_status(job_id, "COMPLETED", result=output)
                logger.info("Job completed", job_id=job_id)
                
            except Exception as e:
                logger.error(f"Job execution failed: {tool_name}", error=str(e), traceback=traceback.format_exc())
                await job_queue.update_job_status(job_id, "FAILED", error=str(e))
                
        except Exception as e:
            logger.error("Worker loop crash", error=str(e))
            await asyncio.sleep(5) # Backoff
            
    logger.info("Worker loop stopped")

def stop_worker():
    global STOP_WORKER
    STOP_WORKER = True
