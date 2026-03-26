import sys
import os

# Emulate run_mcp_server.py sys.path setup
sys.path.insert(0, os.path.join(os.getcwd(), "enterprise-mcp-server"))
sys.path.insert(0, os.getcwd())

try:
    print("Attempting to import mcp_server.main...")
    from mcp_server.main import mcp
    print("✅ Import SUCCESS")
except Exception as e:
    print(f"❌ Import FAILED: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
