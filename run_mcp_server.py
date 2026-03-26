import uvicorn
import os
import sys
import warnings

# Suppress google-api-core FutureWarning
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core.*")

# Ensure the paths are correct for imports
sys.path.insert(0, os.path.join(os.getcwd(), "enterprise-mcp-server"))
sys.path.insert(0, os.getcwd())

if __name__ == "__main__":
    print("Starting Enterprise MCP Server on http://localhost:9000")
    print("API Docs: http://localhost:9000/docs")
    
    try:
        from app.api.main import app
        uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
