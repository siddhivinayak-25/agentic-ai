import os
import sqlite3
import hashlib
from pathlib import Path
from server.tools.sandbox import WORKSPACE_ROOT

DB_PATH = Path(__file__).parent.parent / "workspace.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def db_init():
    """Initialise SQLite tables and FTS5 search index."""
    with get_db_connection() as conn:
        # File registry for change detection
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Source chunks
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY(file_path) REFERENCES files(path) ON DELETE CASCADE
            );
        """)
        # FTS5 Virtual Table for full-text search
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    content,
                    file_path unindexed,
                    start_line unindexed,
                    end_line unindexed
                );
            """)
        except sqlite3.OperationalError as e:
            # If FTS5 is not loaded/compiled in this sqlite version (rare in modern python)
            # fallback to standard table with LIKE search, but modern Python has FTS5 by default.
            raise RuntimeError(f"Failed to initialise SQLite FTS5 extension: {e}")

def get_file_hash(filepath: Path) -> str:
    """Compute SHA256 of file content."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def is_text_file(filepath: Path) -> bool:
    """Check if the file is a text file based on extension and content."""
    # Exclude common binary files
    ignored_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tar",
        ".gz", ".exe", ".dll", ".so", ".dylib", ".pyc", ".db", ".sqlite", ".woff",
        ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".wav", ".avi", ".mov"
    }
    if filepath.suffix.lower() in ignored_extensions:
        return False
    
    # Check for null bytes in initial chunk
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return False
    except Exception:
        return False
        
    return True

def should_ignore(filepath: Path) -> bool:
    """Filter out build outputs, VCS systems, and virtual environments."""
    parts = filepath.relative_to(WORKSPACE_ROOT).parts
    ignored_dirs = {
        "node_modules", ".git", ".venv", "venv", "env", "dist", "build", 
        "__pycache__", ".agent_tmp", "media"
    }
    # Check if any parent directory is ignored
    for part in parts:
        if part in ignored_dirs or part.startswith("."):
            return True
    return False

def index_workspace() -> dict:
    """Scan the workspace, update SQLite index for new/modified files, clean deleted files."""
    db_init()
    
    indexed_count = 0
    skipped_count = 0
    deleted_count = 0
    
    # Find all active files on disk
    disk_files = {}
    for p in WORKSPACE_ROOT.rglob("*"):
        if p.is_file() and not should_ignore(p) and is_text_file(p):
            rel_path = str(p.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
            disk_files[rel_path] = p

    with get_db_connection() as conn:
        # 1. Clean up index for files no longer on disk
        cursor = conn.execute("SELECT path FROM files")
        db_paths = [row[0] for row in cursor.fetchall()]
        
        for db_path in db_paths:
            if db_path not in disk_files:
                conn.execute("DELETE FROM files WHERE path = ?", (db_path,))
                conn.execute("DELETE FROM chunks_fts WHERE file_path = ?", (db_path,))
                deleted_count += 1

        # 2. Index new/modified files
        for rel_path, full_path in disk_files.items():
            current_hash = get_file_hash(full_path)
            
            # Check if already indexed with same hash
            cursor = conn.execute("SELECT hash FROM files WHERE path = ?", (rel_path,))
            row = cursor.fetchone()
            
            if row and row[0] == current_hash:
                skipped_count += 1
                continue
                
            # Update files registry first to satisfy foreign key constraints
            conn.execute(
                "INSERT OR REPLACE INTO files (path, hash, last_indexed) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (rel_path, current_hash)
            )

            # Clear any old chunks for this file
            conn.execute("DELETE FROM chunks WHERE file_path = ?", (rel_path,))
            conn.execute("DELETE FROM chunks_fts WHERE file_path = ?", (rel_path,))
            
            # Read and chunk file contents
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                skipped_count += 1
                continue
                
            lines = content.splitlines()
            chunk_size = 50  # Index in blocks of 50 lines
            
            for i in range(0, len(lines), chunk_size):
                chunk_lines = lines[i:i + chunk_size]
                chunk_text = "\n".join(chunk_lines)
                start_line = i + 1
                end_line = min(len(lines), i + chunk_size)
                
                # Insert chunk metadata
                conn.execute(
                    "INSERT INTO chunks (file_path, start_line, end_line, content) VALUES (?, ?, ?, ?)",
                    (rel_path, start_line, end_line, chunk_text)
                )
                
                # Insert virtual FTS text
                conn.execute(
                    "INSERT INTO chunks_fts (content, file_path, start_line, end_line) VALUES (?, ?, ?, ?)",
                    (chunk_text, rel_path, start_line, end_line)
                )
            
            indexed_count += 1
            
        conn.commit()
        
    return {
        "status": "ok",
        "files_indexed": indexed_count,
        "files_skipped": skipped_count,
        "files_deleted_from_index": deleted_count
    }

def search_code(query: str, limit: int = 15) -> list[dict]:
    """Search workspace code chunks using SQLite FTS5 matching."""
    db_init()
    results = []
    
    with get_db_connection() as conn:
        # SQLite FTS5 rank: lower is better (usually negative values for good matches)
        cursor = conn.execute("""
            SELECT file_path, start_line, end_line, content, rank
            FROM chunks_fts
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        for row in cursor.fetchall():
            results.append({
                "file": row[0],
                "start_line": int(row[1]),
                "end_line": int(row[2]),
                "snippet": row[3],
                "score": float(row[4])
            })
            
    return results
