import uvicorn
import sys
import os

# Ensure the paths are correct for imports
sys.path.insert(0, os.path.join(os.getcwd(), "enterprise-mcp-server"))
sys.path.insert(0, os.getcwd())

if __name__ == "__main__":
    print("Starting Enterprise MCP Server on http://localhost:9000")
    print("API Docs: http://localhost:9000/docs")
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=9000, log_level="info")
