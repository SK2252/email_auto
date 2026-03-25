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
            # 1. Initialize
            print("Sending initialize request...")
            init_data = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "verify-script", "version": "1.0"}
                }
            }
            response = await client.post(
                "http://localhost:9000/mcp",
                json=init_data,
                headers=headers,
                timeout=10.0
            )
            print(f"Init Status: {response.status_code}")
            session_id = response.headers.get("mcp-session-id")
            print(f"Session ID: {session_id}")
            
            if not session_id:
                print("Error: No session ID returned in headers")
                return

            # 2. List tools
            print("Sending tools/list request...")
            list_headers = headers.copy()
            list_headers["mcp-session-id"] = session_id
            
            list_data = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            response = await client.post(
                "http://localhost:9000/mcp",
                json=list_data,
                headers=list_headers,
                timeout=10.0
            )
            print(f"List Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                print(f"Registered tools count: {len(tools)}")
                names = sorted([t.get("name") for t in tools])
                for name in names:
                    print(f"  - {name}")
            else:
                print(f"Error Response: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
