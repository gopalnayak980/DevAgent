"""
File Modification Detection & Proposal Creation — Phase 11.4 Chat Integration.

Detects file modification intent from user chat messages, extracts the
target file and proposed changes, then creates a persistent
FileChangeProposal via the existing change service.

This module bridges the chat pipeline to the Phase 11.4 safe file
modification system:  PROPOSE → DIFF → HUMAN APPROVAL → APPLY.

The AI / agent NEVER modifies workspace files directly.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace
from app.workspace.change_repository import FileChangeProposalRepository
from app.workspace.change_service import (
    FileChangeProposalService,
    ProposalAccessDeniedError,
)
from app.workspace.file_service import (
    WorkspaceFileService,
    PathTraversalError,
    FileNotFoundInWorkspaceError,
    IsADirectoryError as WsIsADirectoryError,
    FileTooLargeError,
    FileEncodingError,
)
from app.workspace.repository import WorkspaceRepository
from app.workspace.service import (
    WorkspaceService,
    WorkspaceNotFoundError,
    WorkspaceAccessDeniedError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regex patterns for detecting file modification intent
# ---------------------------------------------------------------------------

# Pattern: explicit "modify <file>" or "change <file>" or "update <file>" or "edit <file>"
_MODIFY_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"(?:modify|change|update|edit|replace|alter|propose)\s+"
        r"(?:the\s+)?(?:a\s+)?(?:file\s+)?(?:change\s+to\s+)?['\"]?([a-zA-Z0-9_\-\.\/\\]+\.\w+)['\"]?",
        re.IGNORECASE,
    ),
    # "in <file>" patterns
    re.compile(
        r"(?:modify|change|update|edit|replace|alter|propose)\s+(?:.*?)\s+in\s+"
        r"['\"]?([a-zA-Z0-9_\-\.\/\\]+\.\w+)['\"]?",
        re.IGNORECASE,
    ),
]

# Pattern: "change <old> to <new>" within a message
_CHANGE_TO_PATTERN = re.compile(
    r"change\s*:\s*\n?\s*(.+?)\s*\n?\s*to\s*:\s*\n?\s*(.+?)(?:\n|$)",
    re.IGNORECASE | re.DOTALL,
)

# Pattern for inline code blocks with content
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:\w+)?\s*\n(.*?)```",
    re.DOTALL,
)

# Pattern for quoted strings that represent code lines
_QUOTED_LINE_PATTERN = re.compile(
    r'["\'](.+?)["\']',
)


@dataclass
class FileModificationRequest:
    """Parsed file modification details from user message."""
    file_path: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None


def detect_file_modification_intent(message: str) -> bool:
    """Check if the user's message requests a file modification.

    Returns True if the message contains explicit file modification keywords
    combined with a file path reference.
    """
    normalised = message.lower().strip()

    # Must contain modification keywords
    mod_keywords = [
        "modify", "change", "update", "edit", "replace", "alter",
        "proposed change", "propose", "proposal",
    ]
    has_mod_keyword = any(kw in normalised for kw in mod_keywords)
    if not has_mod_keyword:
        return False

    # Must reference a file path (contains a dot extension)
    for pattern in _MODIFY_PATTERNS:
        if pattern.search(message):
            return True

    return False


def extract_file_path(message: str) -> Optional[str]:
    """Extract the target file path from the user's message."""
    for pattern in _MODIFY_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip().strip("'\"")
    return None


def extract_change_pair(message: str) -> tuple[Optional[str], Optional[str]]:
    """Extract old content and new content from user's 'change X to Y' pattern.

    Returns (old_content, new_content) or (None, None) if not found.
    """
    match = _CHANGE_TO_PATTERN.search(message)
    if match:
        old = match.group(1).strip().strip("'\"`")
        new = match.group(2).strip().strip("'\"`")
        return old, new

    return None, None


def apply_text_replacement(original_content: str, old_text: str, new_text: str) -> Optional[str]:
    """Apply a simple text replacement in the original content.

    Returns the new full file content if the old_text was found,
    or None if the old_text was not found in the original.
    """
    if old_text not in original_content:
        return None
    return original_content.replace(old_text, new_text, 1)


async def create_proposal_from_chat(
    session: AsyncSession,
    user_id: str,
    workspace_id: str,
    user_message: str,
) -> Optional[dict]:
    """Detect file modification intent and create a persistent proposal.

    This is the main integration point between chat and the Phase 11.4
    file change proposal system.

    Returns a dict with proposal metadata if a proposal was created,
    or None if no file modification was detected or creation failed.
    """
    if not detect_file_modification_intent(user_message):
        return None

    file_path = extract_file_path(user_message)
    if not file_path:
        logger.debug("File modification intent detected but no file path found.")
        return None

    old_text, new_text = extract_change_pair(user_message)
    if not old_text or not new_text:
        logger.debug(
            "File modification intent detected for '%s' but could not extract "
            "change pair (old → new).",
            file_path,
        )
        return None

    # Resolve workspace
    ws_service = WorkspaceService(WorkspaceRepository(session))
    try:
        workspace = await ws_service.get_workspace(
            workspace_id=workspace_id,
            user_id=user_id,
        )
    except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
        logger.warning(
            "Workspace '%s' not found or access denied for user '%s'.",
            workspace_id, user_id,
        )
        return None

    # Read current file content
    file_service = WorkspaceFileService(workspace)
    try:
        file_info = file_service.read_file(file_path)
    except (PathTraversalError, FileNotFoundInWorkspaceError,
            WsIsADirectoryError, FileTooLargeError, FileEncodingError) as exc:
        logger.warning(
            "Cannot read file '%s' in workspace '%s': %s",
            file_path, workspace_id, exc,
        )
        return None

    original_content = file_info["content"]

    # Apply the text replacement
    proposed_content = apply_text_replacement(original_content, old_text, new_text)
    if proposed_content is None:
        logger.info(
            "Old text not found in file '%s'. Cannot create proposal.",
            file_path,
        )
        return None

    # No-op check: if proposed content is identical
    if proposed_content == original_content:
        logger.info("Proposed content is identical to original. No proposal created.")
        return None

    # Create the persistent proposal via the Phase 11.4 service
    change_service = FileChangeProposalService(FileChangeProposalRepository(session))
    try:
        proposal = await change_service.create_proposal(
            workspace=workspace,
            user_id=user_id,
            file_path=file_path,
            proposed_content=proposed_content,
        )
    except (ProposalAccessDeniedError, PathTraversalError,
            FileNotFoundInWorkspaceError, FileTooLargeError,
            FileEncodingError) as exc:
        logger.warning("Failed to create file change proposal: %s", exc)
        return None

    logger.info(
        "Created file change proposal id=%s from chat for file '%s' in workspace '%s'",
        proposal.id, file_path, workspace_id,
    )

    return {
        "id": proposal.id,
        "workspace_id": proposal.workspace_id,
        "file_path": proposal.file_path,
        "status": proposal.status,
        "diff": proposal.diff,
    }
