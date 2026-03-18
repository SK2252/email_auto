"""
Debug script to simulate the polling loop and see if labels are applied when emails are ingested
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
    print("\n=== SIMULATING POLLING LOOP ===\n")
    
    # Bootstrap
    from utils.gmail_label_manager import bootstrap_labels
    await bootstrap_labels()
    print("[OK] Labels bootstrapped\n")
    
    # Run one iteration of polling
    from agents.intake_agent import poll_and_ingest
    from app.infrastructure.external.gmail_client import get_gmail_service
    import time
    
    print("[*] Starting polling iteration...")
    start_time = time.time()
    
    # Capture messages before polling
    service = get_gmail_service()
    results_before = service.users().messages().list(userId="me", q="in:inbox", maxResults=5).execute()
    messages_before = {m["id"] for m in results_before.get("messages", [])}
    print(f"[*] Messages in inbox before polling: {len(messages_before)}")
    if messages_before:
        print(f"    Sample IDs: {list(messages_before)[:3]}")
    
    try:
        await poll_and_ingest()
        print("[OK] Polling completed successfully")
    except Exception as e:
        logger.error(f"Polling failed: {e}", exc_info=True)
        print(f"[ERROR] Polling failed: {e}")
    
    elapsed = time.time() - start_time
    print(f"\n[*] Polling took {elapsed:.2f} seconds")
    
    # Check which messages have labels NOW
    print("\n[*] Checking for labels on messages_in inbox...")
    results_after = service.users().messages().list(userId="me", q="in:inbox", maxResults=10).execute()
    messages_after = results_after.get("messages", [])
    
    labels_resp = service.users().labels().list(userId="me").execute()
    label_map = {lbl["id"]: lbl["name"] for lbl in labels_resp.get("labels", [])}
    
    print(f"[*] Checking {len(messages_after)} messages in inbox...")
    labeled_count = 0
    for i, msg_meta in enumerate(messages_after[:5]):
        msg_id = msg_meta["id"]
        msg = service.users().messages().get(userId="me", id=msg_id, format="minimal").execute()
        label_ids = msg.get("labelIds", [])
        label_names = [label_map.get(lid, lid) for lid in label_ids]
        
        managed_labels = [l for l in label_names if any(l.startswith(p) for p in ["Billing", "IT Support", "HR", "Complaint", "Query", "Escalation", "Other"])]
        
        if managed_labels:
            print(f"  [{i}] ID={msg_id}: {managed_labels}")
            labeled_count += 1
    
    if labeled_count == 0:
        print(f"  No managed labels found on any of the first 5 messages")

if __name__ == "__main__":
    asyncio.run(main())
