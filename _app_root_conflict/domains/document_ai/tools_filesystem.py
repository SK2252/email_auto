import os
from pathlib import Path
from typing import Any, Dict, List, Optional

def _resolve_path(path: str) -> Path:
    """Resolve a path safely."""
    # Note: For security in production, you might want to restrict this to allowed directories
    return Path(path).resolve()

async def list_directory(directory_path: str) -> List[Dict[str, Any]]:
    """
    List the contents of a directory.
    
    Args:
        directory_path: The absolute or relative path to the directory to list.
        
    Returns:
        List of dictionaries containing file/directory information.
    """
    p = _resolve_path(directory_path)
    if not p.is_dir():
        raise ValueError(f"Path is not a directory or does not exist: {p}")
        
    results = []
    for item in p.iterdir():
        try:
            stat = item.stat()
            results.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "absolute_path": str(item)
            })
        except OSError:
            # Skip items we can't access
            continue
    return results

async def search_files(directory_path: str, pattern: str) -> List[str]:
    """
    Search for files matching a glob pattern in a directory (recursive).
    
    Args:
        directory_path: The starting directory to search in.
        pattern: The glob pattern to match (e.g., '*.yaml', '**/*.py').
        
    Returns:
        List of matching absolute file paths.
    """
    p = _resolve_path(directory_path)
    if not p.is_dir():
        raise ValueError(f"Path is not a directory or does not exist: {p}")
        
    matches = p.rglob(pattern) if "**" in pattern else p.glob(pattern)
    return [str(m) for m in matches if m.is_file()]

async def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific file.
    
    Args:
        file_path: The path to the file.
        
    Returns:
        Dictionary with file statistics.
    """
    p = _resolve_path(file_path)
    if not p.exists():
        raise ValueError(f"Path does not exist: {p}")
        
    stat = p.stat()
    return {
        "name": p.name,
        "is_dir": p.is_dir(),
        "is_file": p.is_file(),
        "is_symlink": p.is_symlink(),
        "size_bytes": stat.st_size,
        "created_time": stat.st_ctime,
        "modified_time": stat.st_mtime,
        "absolute_path": str(p),
        "extension": p.suffix
    }

async def read_file(file_path: str, lines: Optional[int] = None) -> str:
    """
    Read the contents of a text file.
    
    Args:
        file_path: The path to the file to read.
        lines: Optional number of lines to read from the beginning.
        
    Returns:
        The text content of the file.
    """
    p = _resolve_path(file_path)
    if not p.is_file():
        raise ValueError(f"Path is not a file or does not exist: {p}")
        
    with p.open("r", encoding="utf-8") as f:
        if lines is not None and lines > 0:
            content_lines = [next(f) for _ in range(lines)]
            return "".join(content_lines)
        return f.read()

async def write_file(file_path: str, content: str, overwrite: bool = False) -> Dict[str, str]:
    """
    Write text content to a file.
    
    Args:
        file_path: The path where the file should be written.
        content: The text content to write.
        overwrite: If False, will raise an error if the file already exists.
        
    Returns:
        Confirmation message with the absolute path.
    """
    p = _resolve_path(file_path)
    
    if p.exists() and not overwrite:
        raise ValueError(f"File already exists at {p}. Set overwrite=True to replace it.")
        
    # Create parent directories if they don't exist
    p.parent.mkdir(parents=True, exist_ok=True)
        
    with p.open("w", encoding="utf-8") as f:
        f.write(content)
        
    return {"status": "success", "message": f"Successfully wrote to {p}", "path": str(p)}
