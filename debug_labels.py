"""
Diagnostic script to check Gmail label creation and application.
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

from utils.gmail_label_manager import bootstrap_labels, _label_cache, _managed_label_ids

async def main():
    print("\n=== GMAIL LABEL DIAGNOSTIC ===\n")
    
    # 1. Check if Gmail API is accessible
    try:
        from app.infrastructure.external.gmail_client import get_gmail_service, execute_gmail_api
        print("[OK] Gmail API module imported successfully")
    except ImportError as e:
        print(f"[ERROR] Failed to import Gmail API: {e}")
        return
    
    try:
        service = get_gmail_service()
        print(f"[OK] Gmail service initialized: {service}")
    except Exception as e:
        print(f"[ERROR] Failed to get Gmail service: {e}")
        return
    
    # 2. Check existing labels
    try:
        resp = execute_gmail_api(service.users().labels().list(userId="me"))
        existing_labels = resp.get("labels", [])
        print(f"\n[OK] Found {len(existing_labels)} existing labels in Gmail:")
        for lbl in existing_labels[:10]:  # Show first 10
            print(f"  - {lbl['name']} (ID: {lbl['id']})")
        if len(existing_labels) > 10:
            print(f"  ... and {len(existing_labels) - 10} more")
    except Exception as e:
        print(f"[ERROR] Failed to fetch existing labels: {e}")
        return
    
    # 3. Check for our managed labels (before bootstrap)
    our_labels = [lbl for lbl in existing_labels if any(cat in lbl['name'] for cat in [
        'Billing', 'IT Support', 'HR', 'Complaint', 'Query', 'Escalation', 'Other'
    ])]
    print(f"\n[OK] Found {len(our_labels)} managed labels already in Gmail")
    
    # 4. Run bootstrap
    print(f"\n--- Running bootstrap_labels() ---")
    try:
        await bootstrap_labels()
        print("[OK] bootstrap_labels() completed")
    except Exception as e:
        print(f"[ERROR] bootstrap_labels() failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Check cache
    print(f"\n[OK] Cache after bootstrap:")
    print(f"  _label_cache size: {len(_label_cache)}")
    print(f"  _managed_label_ids size: {len(_managed_label_ids)}")
    
    if _label_cache:
        print(f"\n  First 5 cached labels:")
        for i, (name, id_) in enumerate(list(_label_cache.items())[:5]):
            print(f"    {name} -> {id_}")
    
    # 6. Check if labels now exist in Gmail
    try:
        resp = execute_gmail_api(service.users().labels().list(userId="me"))
        existing_labels_after = resp.get("labels", [])
        print(f"\n[OK] Labels in Gmail after bootstrap: {len(existing_labels_after)}")
        
        # Check for specific labels
        test_labels = ["Billing", "Billing/High", "IT Support", "IT Support/Medium"]
        for test_label in test_labels:
            found = any(lbl['name'] == test_label for lbl in existing_labels_after)
            print(f"  {test_label}: {'FOUND' if found else 'NOT FOUND'}")
    except Exception as e:
        print(f"[ERROR] Failed to check labels after bootstrap: {e}")

if __name__ == "__main__":
    asyncio.run(main())
