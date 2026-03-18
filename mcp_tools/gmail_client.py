import logging
import json
from typing import Optional, List, Any, Dict
from mcp import ClientSession
from mcp.client.sse import sse_client

# Structured logging setup
logger = logging.getLogger(__name__)

class GmailClient:
    """
    Thin wrapper over Enterprise MCP Gmail tools via SSE protocol.
    Provides a consistent interface for agents to interact with Gmail.
    """

    def __init__(self, server_url: str = "http://localhost:9000/mcp/sse"):
        self.server_url = server_url

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generic helper to call a tool via MCP SSE."""
        try:
            async with sse_client(self.server_url) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    
                    # Convert CallToolResult to dict
                    if hasattr(result, "content") and result.content:
                        # Assuming the tool returns a JSON string in its content
                        try:
                            # Typically FastMCP tools return results that get wrapped in text content
                            return json.loads(result.content[0].text)
                        except (IndexError, AttributeError, json.JSONDecodeError):
                            return {"status": "OK", "data": result.content}
                    return {"status": "OK", "data": result}
        except Exception as e:
            logger.error(json.dumps({
                "event": f"mcp_call_failed",
                "tool": name,
                "error": str(e)
            }))
            return {"status": "ERROR", "error": str(e)}

    async def poll_inbox(self) -> Dict[str, Any]:
        """Find threads where we haven't replied yet."""
        return await self._call_tool("gmail_list_unanswered", {})

    async def fetch_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch full content of a specific message."""
        return await self._call_tool("gmail_fetch_message", {"message_id": message_id})

    async def fetch_thread(self, thread_id: str) -> Dict[str, Any]:
        """Fetch all messages in a conversation thread."""
        return await self._call_tool("gmail_fetch_thread", {"thread_id": thread_id})

    async def send_reply(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a real email reply (or a new email if thread_id is None)."""
        args = {"to": to, "subject": subject, "body": body}
        if thread_id:
            args["thread_id"] = thread_id
        return await self._call_tool("gmail_send_email", args)

    async def create_draft(self, to: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a draft response in Gmail."""
        args = {"to": to, "subject": subject, "body": body}
        if thread_id:
            args["thread_id"] = thread_id
        return await self._call_tool("gmail_create_draft", args)

    async def move_to_folder(self, message_id: str, folder_label: str) -> Dict[str, Any]:
        """Move a message to a specific label (folder)."""
        return await self._call_tool("gmail_move_to_folder", {
            "message_ids": [message_id],
            "folder_label": folder_label
        })

    async def archive_message(self, message_id: str) -> Dict[str, Any]:
        """Archive a message (removes from INBOX)."""
        return await self._call_tool("gmail_archive_messages", {
            "message_ids": [message_id]
        })

    async def fetch_attachment(self, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Fetch raw attachment bytes (base64url) from Gmail via MCP tool."""
        return await self._call_tool("gmail_get_attachment", {
            "message_id": message_id,
            "attachment_id": attachment_id,
        })

# Singleton instance for app-wide use
gmail_client = GmailClient()
