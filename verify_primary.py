import asyncio
import json
from mcp_tools.gmail_client import gmail_client

async def verify_primary_filter():
    print("Testing 'category:primary' filter...")
    
    # Test 1: List threads with category:primary
    # We'll use the search tool if available, or just call list_unanswered which now has it
    result = await gmail_client._call_tool("gmail_list_unanswered", {})
    
    if result.get("status") == "OK":
        threads = result.get("data", {}).get("threads", [])
        print(f"Found {len(threads)} unanswered threads in Primary.")
        for t in threads[:3]:
            print(f"- {t['subject']} (From: {t['last_sender']})")
    else:
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(verify_primary_filter())
