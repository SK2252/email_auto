from datetime import datetime
import uuid

def generate_case_id() -> str:
    """
    Generates a case reference in the format: CASE-{YYYYMMDD}-{uuid[:6]}
    """
    date_str = datetime.now().strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:6]
    return f"CASE-{date_str}-{short_uuid}"
