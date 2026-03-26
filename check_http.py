import httpx
import asyncio

async def check():
    async with httpx.AsyncClient() as client:
        try:
            print("Checking http://127.0.0.1:9000/ ...")
            resp = await client.get("http://127.0.0.1:9000/", timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text}")
            
            print("\nChecking http://127.0.0.1:9000/mcp/sse ...")
            try:
                async with client.stream("GET", "http://127.0.0.1:9000/mcp/sse", timeout=10) as stream:
                    print(f"Status: {stream.status_code}")
                    if stream.status_code == 200:
                        print(" Success: MCP SSE endpoint found.")
                    else:
                        print(f" Error: Unexpected status {stream.status_code}")
            except Exception as e:
                print(f" Stream Error: {e}")
                
        except Exception as e:
            print(f" Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
