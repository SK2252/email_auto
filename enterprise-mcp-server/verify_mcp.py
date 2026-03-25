import httpx
import json

BASE_URL = "http://localhost:9001/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

def post_mcp(method, params=None, session_id=None, req_id=1, notify=False):
    """Send a JSON-RPC request. notify=True for fire-and-forget notifications."""
    if notify:
        # Notifications have no "id" field
        body = {"jsonrpc": "2.0", "method": method}
    else:
        body = {"jsonrpc": "2.0", "method": method, "id": req_id}

    if params:
        body["params"] = params

    extra = {"mcp-session-id": session_id} if session_id else {}
    result_lines = []
    returned_sid = None

    try:
        with httpx.Client(timeout=15.0) as client:
            with client.stream(
                "POST", BASE_URL, headers={**HEADERS, **extra}, json=body
            ) as r:
                returned_sid = r.headers.get("mcp-session-id")
                status = r.status_code
                try:
                    for line in r.iter_lines():
                        result_lines.append(line)
                except httpx.RemoteProtocolError:
                    pass  # normal early-close for FastMCP
    except Exception as e:
        print(f"  Request error: {e}")
        return None, [], 0

    return returned_sid, result_lines, status


def parse_event(lines):
    for line in lines:
        if line.startswith("data:"):
            data = line[5:].strip()
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    pass
    return None


def main():
    session_id = None

    # ── Step 1: initialize ─────────────────────────────────────────────────
    print("\n[1] initialize")
    sid, lines, status = post_mcp(
        "initialize",
        params={
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "verify-script", "version": "1.0"},
        },
    )
    print(f"  Status : {status}")
    print(f"  Session: {sid}")

    parsed = parse_event(lines)
    if parsed:
        info = parsed.get("result", {})
        print(f"  Server : {info.get('serverInfo')}")
        print(f"  Proto  : {info.get('protocolVersion')}")
    else:
        print(f"  Body   : (empty — normal for FastMCP 1.26)")

    session_id = sid

    if not session_id:
        print("\n  ERROR: No session ID returned. Check server is running.")
        return

    # ── Step 2: notifications/initialized (mandatory ACK) ──────────────────
    print("\n[2] notifications/initialized  (handshake ACK)")
    _, _, status = post_mcp(
        "notifications/initialized",
        session_id=session_id,
        notify=True,   # no id field — fire and forget
    )
    print(f"  Status : {status}  (200 or 202 = OK)")

    # ── Step 3: tools/list ─────────────────────────────────────────────────
    print("\n[3] tools/list")
    _, lines, status = post_mcp(
        "tools/list",
        session_id=session_id,
        req_id=2,
    )
    print(f"  Status : {status}")

    parsed = parse_event(lines)
    if parsed:
        tools = parsed.get("result", {}).get("tools", [])
        print(f"  Total tools: {len(tools)}")
        for t in tools:
            print(f"    ✓ {t['name']}")
    else:
        print(f"  Raw lines: {lines}")


if __name__ == "__main__":
    main()