import sys
import os
import logging

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "enterprise-mcp-server"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.domains.email_ai.workers.auto_organize import _auto_organize_inbox_sync

if __name__ == "__main__":
    print("Testing synchronous email organization...")
    try:
        # We use a very small max_results to just test connectivity and logic
        stats = _auto_organize_inbox_sync("default_user", "me", query="is:unread", max_results=2)
        print(f"Success! Stats: {stats}")
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
