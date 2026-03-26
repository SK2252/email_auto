import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "enterprise-mcp-server"))

from mcp_server.main import _mcp_app, app as mcp_cors_app

print("Type of _mcp_app:", type(_mcp_app))
print("Type of mcp_cors_app:", type(mcp_cors_app))

# Check if _mcp_app has routes (Starlette Router)
if hasattr(_mcp_app, 'routes'):
    print("\nRoutes in _mcp_app:")
    for r in _mcp_app.routes:
        print(f"  {getattr(r, 'path', '?')} methods={getattr(r, 'methods', '?')}")
else:
    print("_mcp_app has no .routes attribute")

# Check if _mcp_app has a router
if hasattr(_mcp_app, 'router'):
    print("\nRoutes in _mcp_app.router:")
    for r in _mcp_app.router.routes:
        print(f"  {getattr(r, 'path', '?')} methods={getattr(r, 'methods', '?')}")
