# Command 1
import mcp_server.main
print('main.py import OK')

# Command 2
from mcp_server.main import mcp
import asyncio

async def count_tools():
    tools = await mcp.list_tools()
    print(f'Registered tools: {len(tools)}')
    names = sorted([t.name for t in tools])
    for name in names:
        print(f'  - {name}')
    assert len(tools) == 31, f'Expected 31 tools, got {len(tools)}'
    print('Tool count OK — exactly 31 tools')

asyncio.run(count_tools())
