import asyncio
import asyncpg
import sys
import os

# Ensure the paths are correct for imports
sys.path.insert(0, r"D:\email_auto\enterprise-mcp-server")
sys.path.insert(0, r"D:\email_auto")

from config.settings import settings

async def test():
    try:
        # Use uppercase DATABASE_URL as defined in config/settings.py
        url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        print(f"Testing connection to: {url[:20]}...")
        
        # Use a timeout of 10 seconds for initial connection
        conn = await asyncio.wait_for(asyncpg.connect(url), timeout=10)
        print('Supabase connected SUCCESS')
        await conn.close()
    except Exception as e:
        print(f"Supabase connection failed ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test())
