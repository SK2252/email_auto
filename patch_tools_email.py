"""
Run this from your project root:
  python patch_tools_email.py

It appends gmail_get_attachment to tools_email.py if missing.
Safe to run multiple times — checks before appending.
"""
import os
import sys

TARGET = os.path.join(
    os.path.dirname(__file__),
    "enterprise-mcp-server", "app", "domains", "email_ai", "tools_email.py"
)

if not os.path.exists(TARGET):
    # Try alternate path
    TARGET = os.path.join(
        os.path.dirname(__file__),
        "app", "domains", "email_ai", "tools_email.py"
    )

if not os.path.exists(TARGET):
    print(f"ERROR: Could not find tools_email.py")
    print("Run this script from your project root directory.")
    sys.exit(1)

content = open(TARGET, encoding="utf-8").read()

if "gmail_get_attachment" in content:
    print("ALREADY PATCHED — gmail_get_attachment already exists in tools_email.py")
    sys.exit(0)

PATCH = '''

# ===========================================================================
# ATTACHMENT DOWNLOAD TOOL — added by patch_tools_email.py
# ===========================================================================

async def gmail_get_attachment(
    message_id: str = "",
    attachment_id: str = "",
    user_id: str = "me",
) -> Dict[str, Any]:
    """
    Download raw attachment bytes (base64url) from Gmail API.

    Args:
        message_id:    Gmail message ID containing the attachment
        attachment_id: Attachment ID from gmail_fetch_message response
        user_id:       Gmail user ID (use "me" for authenticated user)

    Returns:
        Dict with status and base64url-encoded data field.
        Decode with: base64.urlsafe_b64decode(data["data"] + "==")
    """
    if not message_id:
        return _error_result("gmail_get_attachment", "message_id is required")
    if not attachment_id:
        return _error_result("gmail_get_attachment", "attachment_id is required")

    try:
        service = get_gmail_service()

        att = execute_gmail_api(
            service.users().messages().attachments().get(
                userId=user_id,
                messageId=message_id,
                id=attachment_id,
            )
        )

        data_b64 = att.get("data", "")
        size     = att.get("size", 0)

        if not data_b64:
            return _error_result("gmail_get_attachment", "Empty attachment data returned by Gmail API")

        logger.info(
            "Fetched Gmail attachment",
            message_id=message_id,
            attachment_id=attachment_id,
            size=size,
        )

        return _safe_result("gmail_get_attachment", {
            "message_id":    message_id,
            "attachment_id": attachment_id,
            "size":          size,
            "data":          data_b64,
        })

    except GmailClientError as e:
        logger.error("gmail_get_attachment failed", error=str(e))
        return _error_result("gmail_get_attachment", str(e))
'''

with open(TARGET, "a", encoding="utf-8") as f:
    f.write(PATCH)

print(f"PATCHED OK — gmail_get_attachment appended to:")
print(f"  {TARGET}")
print()
print("Next steps:")
print("  1. Restart python mcp.py")
print("  2. Restart python main.py")
