# Duplicate ACK Issue - Root Cause & Fix

## Problem
The system was sending **multiple duplicate acknowledgements** to users for the same email thread. Screenshots showed:
- Original email from user at 3:22 PM
- First ACK with CASE-20260327-c272ba at 3:22 PM
- Second ACK with CASE-20260327-54d12b at 5:27 PM (2 hours later)
- Multiple ACKs with different case IDs in the same thread

## Root Causes

### 1. **Disabled Deduplication Logic** (CRITICAL)
**File:** `agents/intake_agent.py` lines 38-47

The `is_duplicate()` function had its core logic commented out:
```python
# if row:
#     return True
# # Check 2: same sender+subject within last 10 minutes
# if sender and subject:
#     row = await conn.fetchrow(...)
#     if row:
#         return True
return row is not None  # ← WRONG: only checks external_id, not sender+subject
```

**Impact:** Emails with the same sender+subject were not detected as duplicates, allowing re-processing.

### 2. **Processing Last Message Instead of First Unprocessed**
**File:** `agents/intake_agent.py` lines 77-78

```python
# Take the LAST message in the thread
last_message = messages[-1]
```

**Problem:** 
- When the system sends an ACK reply, it becomes a new message in the thread
- Next polling cycle fetches the thread again and sees the ACK as the "last" message
- The ACK reply is then processed as a new email, triggering another ACK
- This creates an infinite loop of ACK replies

### 3. **No Check for Existing ACKs**
**File:** `agents/intake_agent.py` lines 520-530

The system had no guard to prevent sending multiple ACKs to the same thread:
```python
# --- ST-E1-05: Case ID + ACK ---
case_id  = generate_case_id()
ack_sent = False
try:
    ack_sent = await ack_engine.send(parsed, case_id)  # Always sends, no check
```

## Solutions Applied

### Fix 1: Re-enable Deduplication Logic
**File:** `agents/intake_agent.py` lines 23-50

Uncommented the sender+subject dedup check:
```python
async def is_duplicate(external_id: str, sender: str = "", subject: str = "") -> bool:
    # Check 1: exact external_id match
    row = await conn.fetchrow("SELECT 1 FROM emails WHERE external_id = $1 LIMIT 1", external_id)
    if row:
        return True
    # Check 2: same sender+subject within last 10 minutes
    if sender and subject:
        row = await conn.fetchrow(
            """SELECT 1 FROM emails
               WHERE sender = $1 AND subject = $2
               AND created_at > NOW() - INTERVAL '10 minutes'
               LIMIT 1""",
            sender, subject
        )
        if row:
            return True
    return False
```

### Fix 2: Process First Unprocessed Message, Not Last
**File:** `agents/intake_agent.py` lines 68-90

Changed polling logic to iterate through messages and find the first unprocessed one:
```python
# Process ONLY the first unprocessed message in the thread
# (not the last, which may be our own ACK reply)
message_to_process = None
for msg in messages:
    msg_id = msg.get("id")
    if not msg_id:
        continue
    # Check if this message was already processed
    if not await is_duplicate(msg_id):
        message_to_process = msg
        break

if not message_to_process:
    logger.info(json.dumps({"event": "thread_all_messages_processed", "thread_id": thread_id}))
    continue

message_id = message_to_process.get("id")
```

**Benefits:**
- Skips already-processed messages (including our own ACK replies)
- Processes emails in chronological order
- Prevents infinite ACK loops

### Fix 3: Guard Against Duplicate ACKs
**File:** `agents/intake_agent.py` lines 520-545

Added check to skip ACK if one was already sent to this thread:
```python
# Check if ACK was already sent to this thread
thread_id = parsed.get("thread_id", "")
ack_already_sent = False
if thread_id:
    try:
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT 1 FROM emails WHERE thread_id = $1 AND ack_sent = true LIMIT 1",
                thread_id
            )
            ack_already_sent = row is not None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(json.dumps({"event": "ack_check_failed", "thread_id": thread_id, "error": str(e)}))

if not ack_already_sent:
    try:
        ack_sent = await ack_engine.send(parsed, case_id)
    except DeadLetterError as exc:
        send_to_dead_letter_queue({...}, str(exc))
else:
    logger.info(json.dumps({"event": "ack_skipped_already_sent", "thread_id": thread_id, "case_id": case_id}))
```

## Expected Behavior After Fix

1. **First email arrives** → System processes it, sends ONE ACK with case ID
2. **Polling cycle runs again** → Dedup check catches the original email (sender+subject match)
3. **ACK reply is in thread** → First unprocessed message check skips it (already in DB)
4. **No duplicate ACKs** → Thread-level ACK guard prevents re-sending

## Testing

To verify the fix:
1. Send a test email to the system
2. Verify ONE ACK is sent with a case reference
3. Wait 5+ minutes and check polling logs
4. Confirm logs show `intake_skip_duplicate` or `thread_all_messages_processed`
5. Verify NO additional ACKs are sent

## Logging Events

New/updated log events to monitor:
- `thread_all_messages_processed` - All messages in thread already processed
- `ack_skipped_already_sent` - ACK guard prevented duplicate
- `intake_skip_duplicate` - Dedup check caught duplicate
- `ack_check_failed` - Error checking for existing ACKs (non-fatal)
