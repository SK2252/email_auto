"""
Debug script to test the entire pipeline: 
1. Fetch an unanswered email from Gmail
2. Run through the classification stage
3. Apply label
4. Verify label appears on the email
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("\n=== FULL PIPELINE LABEL TEST ===\n")
    
    from mcp_tools.gmail_client import gmail_client
    from utils.gmail_label_manager import apply_classification_label, _label_cache, _managed_label_ids
    from app.infrastructure.external.gmail_client import get_gmail_service
    from config.settings import settings
    import redis
    
    # 1. Bootstrap labels
    print("[*] Bootstrapping labels...")
    from utils.gmail_label_manager import bootstrap_labels
    await bootstrap_labels()
    print("[OK] Labels bootstrapped")
    
    # 2. Get an email from Gmail inbox
    print("\n[*] Fetching emails from Gmail inbox...")
    service = get_gmail_service()
    
    # Try to get any message from INBOX
    results = service.users().messages().list(userId="me", q="in:inbox", maxResults=5).execute()
    messages = results.get("messages", [])
    
    if not messages:
        print("[ERROR] No messages found in inbox")
        return
    
    print(f"[OK] Found {len(messages)} messages in inbox")
    
    # Take first message
    message_meta = messages[0]
    message_id = message_meta["id"]
    print(f"[*] Testing with message ID: {message_id}")
    
    # Fetch full message
    msg_data = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers_dict = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
    
    subject = headers_dict.get("Subject", "[no subject]")
    sender = headers_dict.get("From", "[unknown]")
    body = ""
    body_parts = msg_data.get("payload", {}).get("parts", [])
    for part in body_parts:
        if part.get("mimeType") == "text/plain":
            body = part.get("body", {}).get("data", "")[:200]
            break
    
    print(f"[OK] Subject: {subject}")
    print(f"[OK] From: {sender}")
    print(f"[OK] Body preview: {body[:100] if body else '(empty)'}...")
    
    # 3. Check current labels on message
    print(f"\n[*] Checking current labels...")
    msg = service.users().messages().get(userId="me", id=message_id, format="minimal").execute()
    current_label_ids = msg.get("labelIds", [])
    
    # Get label names
    labels_resp = service.users().labels().list(userId="me").execute()
    label_map = {lbl["id"]: lbl["name"] for lbl in labels_resp.get("labels", [])}
    current_labels = [label_map.get(lid, lid) for lid in current_label_ids]
    print(f"[OK] Current labels: {current_labels}")
    
    # 4. Test apply_classification_label
    print(f"\n[*] Testing label application...")
    redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    
    test_email_type = "billing"
    test_priority = "high"
    
    print(f"[*] Applying label: {test_email_type}/{test_priority}")
    success = await apply_classification_label(
        message_id=message_id,
        service=service,
        email_type=test_email_type,
        priority=test_priority,
        redis_client=redis_client,
    )
    
    if success:
        print(f"[OK] Label application returned True")
    else:
        print(f"[ERROR] Label application returned False")
    
    # 5. Verify label was applied
    print(f"\n[*] Verifying label application...")
    msg = service.users().messages().get(userId="me", id=message_id, format="minimal").execute()
    new_label_ids = msg.get("labelIds", [])
    new_labels = [label_map.get(lid, lid) for lid in new_label_ids]
    print(f"[OK] Labels after application: {new_labels}")
    
    # Check if expected label is there
    expected = "Billing/High"
    found = expected in new_labels
    print(f"\n[RESULT] Expected label '{expected}': {'FOUND' if found else 'NOT FOUND'}")
    
    if found:
        print("[SUCCESS] Label was successfully applied!")
    else:
        print("[FAILURE] Label was NOT applied to the message")

if __name__ == "__main__":
    asyncio.run(main())
