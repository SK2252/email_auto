"""
fix_deploy.py — Auto-deploy all pending fixes to email_auto project.
Run from D:\\email_auto\\ :
    python fix_deploy.py
"""
import os
import sys
import shutil
import ast

ROOT     = os.path.dirname(os.path.abspath(__file__))
OUTPUTS  = ROOT  # this script lives alongside the fixed files

# ---------------------------------------------------------------------------
# Files to deploy: (source_in_outputs, destination_in_project)
# ---------------------------------------------------------------------------
DEPLOYS = [
    ("gmail_client.py",         os.path.join("mcp_tools", "gmail_client.py")),
    ("routing_agent.py",        os.path.join("agents",    "routing_agent.py")),
    ("orchestrator.py",         os.path.join("agents",    "orchestrator.py")),
    ("gmail_label_manager.py",  os.path.join("utils",     "gmail_label_manager.py")),
    ("intake_agent.py",         os.path.join("agents",    "intake_agent.py")),
    ("audit_agent.py",          os.path.join("agents",    "audit_agent.py")),
]

# ---------------------------------------------------------------------------
# Checks to verify each file after deploy
# ---------------------------------------------------------------------------
CHECKS = {
    "gmail_client.py": [
        ("fetch_attachment method exists",
         lambda c: "async def fetch_attachment" in c),
        ("calls gmail_get_attachment tool",
         lambda c: '"gmail_get_attachment"' in c),
        ("no asyncio.run inside class",
         lambda c: "asyncio.run(gmail_client" not in c),
    ],
    "routing_agent.py": [
        ("uses new_event_loop not get_event_loop",
         lambda c: "asyncio.new_event_loop()" in c and
                   "asyncio.get_event_loop()" not in c),
        ("loop.close() in finally",
         lambda c: "loop.close()" in c),
        ("message_ids as list",
         lambda c: "message_ids=[email_id]" in c),
        ("folder_label param correct",
         lambda c: "folder_label=folder" in c),
    ],
    "orchestrator.py": [
        ("uses gmail_message_id variable",
         lambda c: "gmail_message_id" in c),
        ("external_id as first lookup",
         lambda c: 'parsed_email.get("external_id")' in c),
        ("no direct state.get email_id for label",
         lambda c: 'message_id = state.get("email_id")' not in c),
    ],
    "gmail_label_manager.py": [
        ("general_query maps to query not it",
         lambda c: '"general_query": "query"' in c and
                   '"general_query": "it"' not in c),
        ("general_inquiry mapped",
         lambda c: '"general_inquiry": "query"' in c),
        ("negative_feedback mapped",
         lambda c: '"negative_feedback": "complaint"' in c),
    ],
    "intake_agent.py": [
        ("download_and_store is async",
         lambda c: "async def download_and_store" in c),
        ("gmail_message_id param exists",
         lambda c: "gmail_message_id" in c),
        ("fetch_attachment called",
         lambda c: "await gmail_client.fetch_attachment" in c),
        ("base64 urlsafe decode used",
         lambda c: "base64.urlsafe_b64decode" in c),
        ("old stub comment removed",
         lambda c: "In production: download via Gmail API" not in c),
    ],
    "audit_agent.py": [
        ("orphan guard exists",
         lambda c: "SELECT 1 FROM emails WHERE email_id" in c),
        ("early return on orphan",
         lambda c: "audit_event_discarded_orphan" in c),
        ("new_event_loop in persist",
         lambda c: "asyncio.new_event_loop()" in c),
        ("no asyncio.run persist call",
         lambda c: "asyncio.run(self._async_persist_to_db" not in c),
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")

def syntax_ok(path):
    try:
        ast.parse(open(path, encoding="utf-8").read())
        return True
    except SyntaxError as e:
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  fix_deploy.py — Email Auto Deployment Script{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Project root: {ROOT}\n")

    total_pass  = 0
    total_fail  = 0
    deploy_fail = []

    for src_name, dest_rel in DEPLOYS:
        src  = os.path.join(OUTPUTS, src_name)
        dest = os.path.join(ROOT, dest_rel)

        header(f"FILE: {dest_rel}")

        # ── Source exists? ──────────────────────────────────────────────
        if not os.path.exists(src):
            fail(f"Source not found: {src}")
            fail("SKIPPED — run from outputs folder or re-download fixed file")
            deploy_fail.append(src_name)
            total_fail += 1
            continue

        # ── Syntax check on source ──────────────────────────────────────
        if not syntax_ok(src):
            fail(f"Syntax error in source file — NOT deployed")
            deploy_fail.append(src_name)
            total_fail += 1
            continue

        # ── Backup existing file ────────────────────────────────────────
        if os.path.exists(dest):
            backup = dest + ".bak"
            shutil.copy2(dest, backup)
            warn(f"Backed up existing → {os.path.basename(backup)}")

        # ── Deploy ──────────────────────────────────────────────────────
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        ok(f"Deployed → {dest_rel}")

        # ── Content checks ──────────────────────────────────────────────
        content = open(dest, encoding="utf-8").read()
        checks  = CHECKS.get(src_name, [])
        file_ok = True

        for label, fn in checks:
            try:
                if fn(content):
                    ok(label)
                    total_pass += 1
                else:
                    fail(label)
                    total_fail += 1
                    file_ok = False
            except Exception as e:
                fail(f"{label} — check error: {e}")
                total_fail += 1
                file_ok = False

        if not file_ok:
            deploy_fail.append(src_name)

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  SUMMARY{RESET}")
    print(f"{'='*55}")
    print(f"  Checks passed : {GREEN}{total_pass}{RESET}")
    print(f"  Checks failed : {RED}{total_fail}{RESET}")

    if deploy_fail:
        print(f"\n  {RED}FAILED files:{RESET}")
        for f in deploy_fail:
            print(f"    ✗ {f}")
        print(f"\n  {YELLOW}Fix the above files then re-run this script.{RESET}")
    else:
        print(f"\n  {GREEN}{BOLD}ALL FILES DEPLOYED AND VERIFIED ✓{RESET}")
        print(f"\n  {BOLD}Next steps:{RESET}")
        print(f"    1. Restart main.py  →  Ctrl+C then: python main.py")
        print(f"    2. Send test email with attachment")
        print(f"    3. Confirm log shows: attachment_downloaded bytes=...")

    print(f"\n{'='*55}\n")
    return 0 if not deploy_fail else 1


if __name__ == "__main__":
    sys.exit(main())