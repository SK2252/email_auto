"""
Debug test for the full LangGraph orchestrator pipeline.
Tests if apply_label_node is being invoked and labels are applied.
"""
import asyncio
import json
import logging
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup path
mcp_path = os.path.join(os.path.dirname(__file__), "enterprise-mcp-server")
if mcp_path not in sys.path:
    sys.path.insert(0, mcp_path)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n=== FULL ORCHESTRATOR PIPELINE TEST ===\n")
    
    # Bootstrap labels
    from utils.gmail_label_manager import bootstrap_labels
    await bootstrap_labels()
    print("[OK] Labels bootstrapped\n")
    
    # Get a test email from inbox
    from app.infrastructure.external.gmail_client import get_gmail_service
    service = get_gmail_service()
    
    results = service.users().messages().list(userId="me", q="in:inbox", maxResults=1).execute()
    messages = results.get("messages", [])
    
    if not messages:
        print("[ERROR] No messages in inbox")
        return
    
    message_id = messages[0]["id"]
    msg_data = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    
    print(f"[*] Testing with Gmail message ID: {message_id}\n")
    
    # Create raw_email structure as intake_agent would create it
    raw_email = {
        "email_id":    message_id,
        "thread_id":   msg_data.get("threadId"),
        "sender":      "test@example.com",
        "recipient":   "me@gmail.com",
        "subject":     "Test Email",
        "received_at": "2026-03-14T10:00:00Z",
        "body":        "This is a test email body",
        "attachments": [],
        "label_ids":   msg_data.get("labelIds", []),
        "truncated":   False,
        "source":      "gmail"
    }
    
    # Run through orchestrator pipeline
    print("[*] Running through orchestrator pipeline...")
    from agents.orchestrator import run_pipeline
    
    try:
        result = await run_pipeline(raw_email, source="gmail")
        
        print("\n[OK] Pipeline completed")
        print(f"[*] Final step: {result.get('current_step')}")
        print(f"[*] Agent statuses:")
        for agent, status in result.get('agent_statuses', {}).items():
            print(f"    {agent}: {status}")
        
        # Check if apply_label was marked as completed
        if "AG-00 (labeler)" in result.get('agent_statuses', {}):
            print(f"\n[OK] AG-00 (labeler) was invoked: {result['agent_statuses']['AG-00 (labeler)']}")
        else:
            print(f"\n[WARNING] AG-00 (labeler) was NOT found in agent statuses")
        
        # Now check if label was actually applied
        print(f"\n[*] Checking if label was applied to Gmail message...")
        msg = service.users().messages().get(userId="me", id=message_id, format="minimal").execute()
        new_labels = msg.get("labelIds", [])
        
        labels_resp = service.users().labels().list(userId="me").execute()
        label_map = {lbl["id"]: lbl["name"] for lbl in labels_resp.get("labels", [])}
        label_names = [label_map.get(lid, lid) for lid in new_labels]
        
        # Check for any of our managed labels
        managed_prefix = ["Billing", "IT Support", "HR", "Complaint", "Query", "Escalation", "Other"]
        applied_labels = [l for l in label_names if any(l.startswith(p) for p in managed_prefix)]
        
        if applied_labels:
            print(f"[SUCCESS] Found {len(applied_labels)} applied labels: {applied_labels}")
        else:
            print(f"[WARNING] No managed labels found on message")
            print(f"         Current labels: {label_names}")
        
        # Check classification result
        print(f"\n[*] Classification result:")
        classification = result.get("classification_result", {})
        print(f"    Category: {classification.get('category', 'N/A')}")
        print(f"    Priority: {classification.get('priority', 'N/A')}")
        print(f"    Confidence: {classification.get('confidence', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n[ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
