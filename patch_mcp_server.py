"""
Run this from your project root AFTER patch_tools_email.py:
  python patch_mcp_server.py

Registers gmail_get_attachment in mcp_server.py if missing.
Safe to run multiple times.
"""
import os
import sys

# Try common locations
CANDIDATES = [
    "mcp_server.py",
    os.path.join("enterprise-mcp-server", "mcp_server.py"),
    os.path.join("enterprise-mcp-server", "app", "mcp_server.py"),
]

TARGET = None
for c in CANDIDATES:
    if os.path.exists(c):
        TARGET = c
        break

if not TARGET:
    print("ERROR: Could not find mcp_server.py")
    print("Run from your project root, or edit mcp_server.py manually:")
    print('  mcp.add_tool(email.gmail_get_attachment)')
    sys.exit(1)

content = open(TARGET, encoding="utf-8").read()

if "gmail_get_attachment" in content:
    print("ALREADY REGISTERED — gmail_get_attachment already in mcp_server.py")
    sys.exit(0)

# Insert after gmail_move_to_folder line
OLD = "mcp.add_tool(email.gmail_move_to_folder)"
NEW = "mcp.add_tool(email.gmail_move_to_folder)\nmcp.add_tool(email.gmail_get_attachment)  # attachment download"

if OLD not in content:
    print(f"WARNING: Could not find '{OLD}' in {TARGET}")
    print("Add this line manually after gmail_move_to_folder:")
    print("  mcp.add_tool(email.gmail_get_attachment)")
    sys.exit(1)

content = content.replace(OLD, NEW)
open(TARGET, "w", encoding="utf-8").write(content)

print(f"PATCHED OK — gmail_get_attachment registered in:")
print(f"  {TARGET}")
print()
print("Next steps:")
print("  1. Restart python mcp.py  ← mandatory")
print("  2. Restart python main.py")
