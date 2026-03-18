import os
import re

MAPPINGS = {
    # Core
    r"app\.config": "app.core.config",
    r"app\.celery_config": "app.core.celery_app",
    r"app\.observability\.logging_config": "app.core.logging",
    r"app\.utils\.error_codes": "app.core.exceptions",
    r"app\.observability\.metrics": "app.core.metrics",
    r"app\.observability\.health_checks": "app.core.health_checks",
    r"app\.orchestrator\.job_queue": "app.core.job_queue",
    r"app\.orchestrator\.worker": "app.core.worker",
    # API
    r"app\.api\.endpoints\.health": "app.api.routers.health",
    r"app\.api\.endpoints\.admin": "app.api.routers.v1.admin",
    r"app\.api\.endpoints\.gmail_extension": "app.api.routers.v1.gmail",
    r"app\.mcp\.server": "app.api.routers.v1.mcp",
    # Domains - Auth
    r"app\.security\.admin": "app.domains.auth.admin",
    r"app\.security\.api_key": "app.domains.auth.api_key",
    r"app\.security\.file_validator": "app.domains.auth.file_validator",
    r"app\.security\.rbac": "app.domains.auth.rbac",
    r"app\.security": "app.domains.auth",
    # Domains - Document AI
    r"app\.mcp\.tools\.document": "app.domains.document_ai.tools_document",
    r"app\.mcp\.tools\.excel": "app.domains.document_ai.tools_excel",
    r"app\.mcp\.tools\.filesystem": "app.domains.document_ai.tools_filesystem",
    r"app\.mcp\.tools\.job_orchestrator": "app.domains.document_ai.job_orchestrator",
    # Domains - Email AI
    r"app\.mcp\.tools\.email": "app.domains.email_ai.tools_email",
    r"app\.orchestrator\.auto_organize_job": "app.domains.email_ai.workers.auto_organize",
    r"app\.orchestrator\.follow_up_job": "app.domains.email_ai.workers.follow_up",
    # Infrastructure
    r"app\.infrastructure\.gmail_client": "app.infrastructure.external.gmail_client",
    r"app\.infrastructure\.redis_client": "app.infrastructure.cache.redis_client",
    r"app\.infrastructure\.session_manager": "app.infrastructure.cache.session_manager",
    r"app\.db\.engine": "app.infrastructure.database.engine",
    r"app\.db\.models": "app.infrastructure.database.models",
    r"app\.db\.repository": "app.infrastructure.database.repositories.base",
    r"app\.db": "app.infrastructure.database"
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old_regex, new_path in MAPPINGS.items():
        # Match 'from app.config import' -> 'from app.core.config import'
        # Also 'import app.config' -> 'import app.core.config'
        content = re.sub(r'\b' + old_regex + r'\b', new_path, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

def main():
    base_dir = r"d:\agent share\src\enterprise-mcp-server\app"
    for root, dirs, files in os.walk(base_dir):
        if "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                process_file(os.path.join(root, file))
                
if __name__ == "__main__":
    main()
