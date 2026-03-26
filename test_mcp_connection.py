import asyncio
import json
import os
import sys

# Ensure imports work from project root
sys.path.insert(0, os.path.join(os.getcwd(), "enterprise-mcp-server"))

async def test_connection():
    print("Testing MCP Connection via Unified Endpoint...")
    from mcp_tools.gmail_client import gmail_client
    
    # Attempt to call a simple tool
    print("Calling gmail_fetch_profile tool...")
    result = await gmail_client._call_tool("gmail_fetch_profile", {"user_id": "me"})
    
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if result.get("status") == "OK":
        print("\n✅ Verification SUCCESS: Agent can communicate with the unified MCP server.")
    else:
        print("\n❌ Verification FAILED: Could not reach the MCP server.")
        if "404" in str(result.get("error")):
            print("ERROR: Endpoint /mcp/sse not found. Check if mounting succeeded.")
        elif "Connection refused" in str(result.get("error")):
            print("ERROR: Server is not running on port 9000.")

if __name__ == "__main__":
    asyncio.run(test_connection())
