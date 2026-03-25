# Technical Analysis: FastMCP Session Persistence Failure

This analysis investigates why `POST /mcp` requests return `404 Session not found` after a successful `initialize` handshake in FastMCP 1.26.0.

## 1. System Analysis (Internal Source Review)

### Task 1 & 2: `FastMCP.streamable_http_app()` & `stateless_http`
- **Location**: `.venv/Lib/site-packages/mcp/server/fastmcp/server.py`
- **Findings**:
  - `streamable_http_app()` **does** lazily initialize the session manager:
    ```python
    if self._session_manager is None:
        self._session_manager = StreamableHTTPSessionManager(..., stateless=self.settings.stateless_http)
    ```
  - `stateless_http=False` is correctly propagated to the manager.
  - **Re-instantiation Risk**: Every call to `streamable_http_app()` returns a **new Starlette app instance**, but they share the **same singleton session manager** if called on the same `FastMCP` object. However, the lifespan handler `session_manager.run()` can only be called **once**. Calling `streamable_http_app()` twice and running both would crash.

### Task 3 & 4: Session Manager Lifecycle
- **Location**: `.venv/Lib/site-packages/mcp/server/streamable_http_manager.py`
- **Findings**:
  - **Storage**: Sessions are stored in a standard dictionary `self._server_instances`.
  - **Persistence**: This dictionary is **in-memory only**. Any process restart, worker recycle, or `uvicorn` reload wipes all sessions.
  - **The 404 Trigger**:
    - Line 283-291: Returns `404 Session not found` if a session ID is provided but not found in `self._server_instances`.
    - **Cleanup Logic (The Bug)**: In `_handle_stateful_request`, the `run_server` task has a `finally` block (lines 259-271) that **removes the session from the dictionary** as soon as the low-level server loop (`self.app.run`) finishes.
    - **The Race**: If the client's `initialize` request closes the connection prematurely, or if the server crashes during tool registration (common with 31 tools and async lifespans), the loop exits, the `finally` block runs, and the session is deleted.

### Task 5: EventStore
- **Findings**: By default, `event_store` is `None`. Without an `EventStore`, sessions are not resumable across process boundaries or restarts.

---

## 2. Hypothesis Verification

1.  **Does `streamable_http_app()` create a new manager every call?**  
    **Correction**: No, it caches it in `self._session_manager`. However, it creates a new `Starlette` app every time, which is inefficient and can cause lifespan conflicts if called incorrectly.
2.  **Is `stateless_http=False` ignored?**  
    **Correction**: No, it is read correctly, but the "state" is fragile (in-memory).
3.  **Is an EventStore required?**  
    **Correction**: Not for basic operation, but **highly recommended** for stability in multi-request flows.
4.  **`mcp.run` vs `uvicorn.run`?**  
    **Correction**: They are identical. `mcp.run` simply invokes `uvicorn.run(mcp.streamable_http_app())`.

---

## 3. Root Cause: Why you get a 404

The `404` occurs because the session task started during `initialize` **terminated immediately**.
- In your logs, `initialize` returned `Raw lines: []`. This means the SSE stream closed before any data was sent.
- Because the stream closed, the server's `run_server` loop exited.
- This triggered the cleanup code: `del self._server_instances[new_session_id]`.
- Your subsequent `tools/list` request used the ID, but the server had already forgotten it.

---

## 4. Corrected Implementation (The Fix)

To fix this, you must ensure the `FastMCP` instance and its `session_manager` are stable and properly initialized.

### Recommended `mcp_server/main.py`
```python
import os
import uvicorn
from mcp.server.fastmcp import FastMCP

# 1. Create the instance ONCE at module level
mcp = FastMCP(
    "Enterprise MCP Server",
    instructions=get_instructions(),
    lifespan=lifespan,
    stateless_http=False,  # Persistence enabled
    json_response=False,   # SSE mode (standard for MCP)
)

# 2. Create the APP object once
# This ensures the session manager is initialized and the app is stable
app = mcp.streamable_http_app()

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9001"))
    
    # 3. Pass the APP OBJECT directly to uvicorn
    # Do NOT call mcp.streamable_http_app() inside uvicorn.run
    uvicorn.run(
        app, 
        host=host,
        port=port,
        log_level="info",
        # workers=1  # Important: SSE/Streamable HTTP requires a single worker for in-memory sessions
    )
```

### Critical Verification Steps
1.  **Kill Lingering Processes**: Windows often holds the port even after `Ctrl+C`. Use `netstat -ano | findstr :9001` then `taskkill /F /PID <PID>`.
2.  **Use a Single Worker**: If you use `gunicorn` or multiple `uvicorn` workers, Worker 1 will create the session and Worker 2 will return 404.
3.  **Verify Handshaking**: Your `verify_mcp.py` must stay connected to the SSE stream to keep the session alive if no `EventStore` is used.
