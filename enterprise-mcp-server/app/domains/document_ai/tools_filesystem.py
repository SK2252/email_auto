"""
Filesystem MCP Tools.
Provides secure file operations restricted to allowed directories.
Functions are decorated with @server.tool() for MCP exposure.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from app.core.config import settings
from app.core.logging import get_logger
from app.domains.auth.file_validator import file_validator, FileValidationError

logger = get_logger(__name__)

# Initialize FastMCP server for filesystem tools
# Note: In the final architecture, tool_server.py might aggregate these,
# but FastMCP makes it easy to define them.
# The main server will mount these tools.

async def list_directory(directory: str) -> List[str]:
    """
    List files and directories within a given directory.
    Restricted to configured allowed paths.
    """
    try:
        # 1. Security Check
        safe_path = file_validator.validate_path(directory)
        
        if not safe_path.is_dir():
            return [f"Error: {directory} is not a directory"]

        # 2. Implementation
        items = []
        for item in safe_path.iterdir():
            # Skip hidden files/dirs if needed? For now, list all.
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")
            
        logger.info("Listed directory", path=str(safe_path), count=len(items))
        return sorted(items)
        
    except FileValidationError as e:
        logger.warning("Access denied", path=directory, error=e.message)
        return [f"Access denied: {e.message}"]
    except Exception as e:
        logger.error("List directory failed", path=directory, error=str(e))
        return [f"Error listing directory: {str(e)}"]


async def search_files(directory: str, pattern: str) -> List[str]:
    """
    Search for files matching a pattern (glob) inside a directory (recursive).
    """
    try:
        start_path = file_validator.validate_path(directory)
        
        results = []
        # Recursive search using rglob
        for path in start_path.rglob(pattern):
            if path.is_file():
                results.append(str(path.absolute()))
                
        logger.info("Search files", directory=str(start_path), pattern=pattern, matches=len(results))
        return results[:100]  # Limit results
        
    except FileValidationError as e:
        return [f"Access denied: {e.message}"]
    except Exception as e:
        return [f"Error searching files: {str(e)}"]


async def get_file_info(path: str) -> str:
    """
    Get metadata about a file (size, modified time).
    """
    try:
        safe_path = file_validator.validate_path(path)
        if not safe_path.exists():
            return f"Error: File not found: {path}"
            
        stats = safe_path.stat()
        modified = datetime.fromtimestamp(stats.st_mtime).isoformat()
        size_kb = stats.st_size / 1024
        
        return (
            f"File: {safe_path.name}\n"
            f"Path: {safe_path}\n"
            f"Size: {size_kb:.2f} KB\n"
            f"Modified: {modified}\n"
            f"Type: {'Directory' if safe_path.is_dir() else 'File'}"
        )
    except FileValidationError as e:
        return f"Access denied: {e.message}"
    except Exception as e:
        return f"Error getting info: {str(e)}"


async def read_file(path: str) -> str:
    """
    Read the contents of a text file.
    Enforces size limits and allowed extensions via file_validator logic.
    """
    try:
        safe_path = file_validator.validate_path(path)
        
        if not safe_path.is_file():
             return f"Error: Not a file: {path}"
        
        # Additional size check is handled by file_validator (max_file_size)
        # But we double check if needed or rely on validator.
        # Validator checks size if file exists.
        
        # Read content
        try:
            content = safe_path.read_text(encoding='utf-8')
            logger.info("Read file", path=str(safe_path), size=len(content))
            return content
        except UnicodeDecodeError:
            return "Error: File is not valid UTF-8 text (binary file?)"
            
    except FileValidationError as e:
        return f"Access denied: {e.message}"
    except Exception as e:
        logger.error("Read file failed", path=path, error=str(e))
        return f"Error reading file: {str(e)}"


async def write_file(path: str, content: str) -> str:
    """
    Write content to a file. Overwrites if exists.
    """
    try:
        # validate_output_path allows creating new files (doesn't check strict extension whitelist if configured nicely, 
        # but here we use validate_path to enforce extensions for write too).
        # Assuming user wants strict extension control.
        # However, file_validator logic checks if file exists for size.
        # For new file, validate_path ensures parent dir is allowed.
        # Wait, validate_path checks existence usually?
        # file_validator.validate_path:
        # 1. Resolve
        # 2. Check allowed dir
        # 3. Check symlink
        # 4. Check extension
        # 5. Check size (IF file exists)
        # So it works for new files too.
        
        safe_path = file_validator.validate_path(path)
        
        # Ensure parent directory exists
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        safe_path.write_text(content, encoding='utf-8')
        logger.info("Wrote file", path=str(safe_path))
        return f"Successfully wrote to {path}"
        
    except FileValidationError as e:
        return f"Access denied: {e.message}"
    except Exception as e:
        return f"Error writing file: {str(e)}"
