"""
Workspace File Service — Phase 11.3: Safe File Reading & Code Analysis.

Provides secure, read-only file access within a user-owned workspace.

Security model:
    authenticated user
          ↓
    owned workspace (root_path stored in DB)
          ↓
    validated relative path (must stay inside workspace root_path)
          ↓
    safe resolved path (symlinks resolved, traversal blocked)

Never accepts arbitrary filesystem paths from callers.
Never exposes absolute filesystem paths in responses.
Never follows symlinks that escape the workspace.
Never reads files exceeding MAX_FILE_SIZE_BYTES.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path
from typing import List

from app.database.models import Workspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 1 MB maximum file size for reading
MAX_FILE_SIZE_BYTES: int = 1024 * 1024

# Files/directories to skip when listing (hidden + dangerous system entries)
_SKIP_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".DS_Store",
        "Thumbs.db",
        "node_modules",   # skip for performance — can contain thousands of files
    }
)

# Language detection map — extension → language identifier
_EXTENSION_MAP: dict[str, str] = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rb": "ruby",
    ".rs": "rust",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".env": "bash",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".bat": "batch",
    ".ps1": "powershell",
    ".md": "markdown",
    ".rst": "text",
    ".txt": "text",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".dockerfile": "dockerfile",
    ".r": "r",
    ".lua": "lua",
    ".vim": "vim",
}


# ---------------------------------------------------------------------------
# Application-level exceptions
# ---------------------------------------------------------------------------


class FileNotFoundInWorkspaceError(Exception):
    """Raised when a file path does not exist within the workspace."""
    pass


class IsADirectoryError(Exception):
    """Raised when a file path resolves to a directory, not a regular file."""
    pass


class PathTraversalError(Exception):
    """Raised when a path attempts to escape the workspace root."""
    pass


class FileTooLargeError(Exception):
    """Raised when a file exceeds the maximum allowed size."""
    pass


class FileEncodingError(Exception):
    """Raised when a file cannot be decoded as UTF-8 text."""
    pass


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def detect_language(filename: str) -> str:
    """Deterministically detect code language from a file extension.

    Uses a static extension-to-language map. Does NOT call any LLM.
    Returns "text" for unknown extensions.

    Args:
        filename: The filename (e.g. "App.jsx", "config.yaml").

    Returns:
        A lowercase language identifier string (e.g. "javascript", "python").
    """
    ext = Path(filename).suffix.lower()
    return _EXTENSION_MAP.get(ext, "text")


# ---------------------------------------------------------------------------
# WorkspaceFileService
# ---------------------------------------------------------------------------


class WorkspaceFileService:
    """Read-only, security-hardened filesystem access within a workspace.

    All paths are:
    1. Treated as relative — never accepted as absolute.
    2. Resolved against workspace.root_path.
    3. Verified to remain within workspace.root_path (traversal blocked).
    4. Checked against symlink escapes (resolved path must stay inside root).

    The caller is responsible for ensuring the workspace is owned by the
    authenticated user before passing it to this service.
    """

    def __init__(self, workspace: Workspace) -> None:
        """
        Args:
            workspace: The user-owned workspace. Its root_path is the boundary.
        """
        self._workspace_root = Path(workspace.root_path).resolve()
        self._workspace = workspace

    # ------------------------------------------------------------------
    # Path validation (private)
    # ------------------------------------------------------------------

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve and validate a user-supplied relative path.

        Performs multi-layer traversal protection:
        1. Rejects empty paths.
        2. Rejects paths that look like absolute paths.
        3. Resolves the path against the workspace root.
        4. Verifies the resolved path is inside the workspace root
           (blocks ../  variants, encoded traversal, and symlink escapes).

        Args:
            relative_path: A workspace-relative path, e.g. "src/App.jsx".

        Returns:
            The resolved absolute Path (guaranteed inside workspace root).

        Raises:
            PathTraversalError: If the path escapes the workspace root.
        """
        if not relative_path and relative_path != "":
            raise PathTraversalError("Path must not be None.")

        # Strip leading/trailing whitespace
        cleaned = relative_path.strip()

        # Reject absolute paths immediately — covers Unix /etc/passwd
        if os.path.isabs(cleaned):
            raise PathTraversalError(
                "Absolute paths are not permitted. Use a workspace-relative path."
            )

        # Reject Windows drive-letter absolute paths (e.g. C:\Windows or C:/Windows)
        # These are not caught by os.path.isabs on non-Windows hosts.
        import re as _re
        if _re.match(r'^[A-Za-z]:', cleaned):
            raise PathTraversalError(
                "Absolute paths are not permitted. Use a workspace-relative path."
            )

        # Construct the candidate path relative to the workspace root
        # Using Path division safely combines the paths
        candidate = (self._workspace_root / cleaned).resolve()

        # Verify the resolved path is inside the workspace root.
        # .resolve() normalises symlinks, so symlink escapes are also blocked.
        try:
            candidate.relative_to(self._workspace_root)
        except ValueError:
            raise PathTraversalError(
                "The requested path is outside the workspace boundary. "
                "Path traversal is not permitted."
            )

        return candidate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_directory(
        self,
        relative_path: str = "",
        recursive: bool = False,
    ) -> dict:
        """List files and directories within the workspace.

        Args:
            relative_path: Workspace-relative path to list. Empty string
                           means the workspace root.
            recursive: If True, recurse into subdirectories.

        Returns:
            A dict with keys "files" and "directories", each a list of
            entry dicts with "name", "path", "type", and (for files) "size".
            Paths in entries are always workspace-relative.

        Raises:
            PathTraversalError: If relative_path escapes the workspace.
            FileNotFoundInWorkspaceError: If the path does not exist.
            IsADirectoryError: Not raised here (listing a directory is valid).
        """
        target = self._resolve_safe_path(relative_path)

        if not target.exists():
            raise FileNotFoundInWorkspaceError(
                f"Path '{relative_path}' does not exist in the workspace."
            )

        if not target.is_dir():
            raise FileNotFoundInWorkspaceError(
                f"Path '{relative_path}' is not a directory."
            )

        files: List[dict] = []
        directories: List[dict] = []

        if recursive:
            self._collect_recursive(target, files, directories)
        else:
            self._collect_flat(target, files, directories)

        # Sort predictably: directories by name, then files by name
        directories.sort(key=lambda e: e["name"].lower())
        files.sort(key=lambda e: e["name"].lower())

        return {
            "workspace_id": self._workspace.id,
            "path": relative_path,
            "files": files,
            "directories": directories,
        }

    def _should_skip(self, name: str) -> bool:
        """Return True if this entry should be excluded from listings."""
        # Skip hidden files/dirs starting with . (except empty path "")
        # and known system/dangerous directories
        return name in _SKIP_NAMES or name.startswith(".")

    def _make_relative(self, absolute: Path) -> str:
        """Convert an absolute path to a workspace-relative path string."""
        try:
            return str(absolute.relative_to(self._workspace_root)).replace("\\", "/")
        except ValueError:
            # Should never happen after _resolve_safe_path validation
            raise PathTraversalError("Path escaped workspace root unexpectedly.")

    def _collect_flat(
        self,
        target: Path,
        files: List[dict],
        directories: List[dict],
    ) -> None:
        """Collect immediate children of target (non-recursive)."""
        try:
            entries = list(target.iterdir())
        except PermissionError:
            return  # Skip unreadable directories silently

        for entry in entries:
            if self._should_skip(entry.name):
                continue

            rel_path = self._make_relative(entry)

            if entry.is_dir(follow_symlinks=False):
                directories.append({
                    "name": entry.name,
                    "path": rel_path,
                    "type": "directory",
                })
            elif entry.is_file(follow_symlinks=False):
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                files.append({
                    "name": entry.name,
                    "path": rel_path,
                    "type": "file",
                    "size": size,
                })

    def _collect_recursive(
        self,
        target: Path,
        files: List[dict],
        directories: List[dict],
    ) -> None:
        """Collect all children recursively."""
        for entry in target.rglob("*"):
            if self._should_skip(entry.name):
                continue

            # Validate that rglob didn't follow a symlink outside root
            try:
                entry.resolve().relative_to(self._workspace_root)
            except ValueError:
                continue  # Skip symlinks that escape the workspace

            rel_path = self._make_relative(entry)

            if entry.is_dir(follow_symlinks=False):
                directories.append({
                    "name": entry.name,
                    "path": rel_path,
                    "type": "directory",
                })
            elif entry.is_file(follow_symlinks=False):
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                files.append({
                    "name": entry.name,
                    "path": rel_path,
                    "type": "file",
                    "size": size,
                })

    def read_file(self, relative_path: str) -> dict:
        """Read a text file within the workspace.

        Args:
            relative_path: Workspace-relative path to the file,
                           e.g. "src/App.jsx".

        Returns:
            A dict with "workspace_id", "path", "content", "size", "language".

        Raises:
            PathTraversalError: If the path escapes the workspace root.
            FileNotFoundInWorkspaceError: If the file does not exist.
            IsADirectoryError: If the path resolves to a directory.
            FileTooLargeError: If the file exceeds MAX_FILE_SIZE_BYTES.
            FileEncodingError: If the file cannot be decoded as UTF-8.
        """
        if not relative_path or not relative_path.strip():
            raise FileNotFoundInWorkspaceError("File path must not be empty.")

        target = self._resolve_safe_path(relative_path)

        if not target.exists():
            raise FileNotFoundInWorkspaceError(
                f"File '{relative_path}' does not exist in the workspace."
            )

        if target.is_dir():
            raise IsADirectoryError(
                f"'{relative_path}' is a directory, not a file."
            )

        if not target.is_file():
            raise FileNotFoundInWorkspaceError(
                f"'{relative_path}' is not a regular file."
            )

        try:
            file_size = target.stat().st_size
        except OSError as exc:
            raise FileNotFoundInWorkspaceError(
                f"Cannot access file '{relative_path}'."
            ) from exc

        if file_size > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File '{relative_path}' is {file_size} bytes, which exceeds the "
                f"{MAX_FILE_SIZE_BYTES // 1024} KB limit."
            )

        try:
            content = target.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise FileEncodingError(
                f"File '{relative_path}' contains non-UTF-8 content and cannot "
                f"be displayed as text."
            ) from exc
        except OSError as exc:
            raise FileNotFoundInWorkspaceError(
                f"Cannot read file '{relative_path}'."
            ) from exc

        # Use the actual resolved name to detect language
        language = detect_language(target.name)

        # Use the cleaned relative path in the response — never the absolute path
        clean_path = self._make_relative(target)

        return {
            "workspace_id": self._workspace.id,
            "path": clean_path,
            "content": content,
            "size": file_size,
            "language": language,
        }
