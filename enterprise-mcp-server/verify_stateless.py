import httpx
import asyncio
import json

async def main():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    async with httpx.AsyncClient() as client:
        try:
            print("Sending tools/list request...")
            list_data = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
            response = await client.post(
                "http://localhost:9000/mcp",
                json=list_data,
                headers=headers,
                timeout=10.0
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("SUCCESS: Received JSON response!")
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                print(f"Registered tools count: {len(tools)}")
            else:
                print(f"Error Response: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
