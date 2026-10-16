"""
Workspace File Change Proposal Service — Phase 11.4: Safe File Modification + Human Approval.

Every modification to a workspace file MUST follow:
    PROPOSE → DIFF → HUMAN APPROVAL → APPLY

The AI / agent must NEVER directly modify workspace files without human approval.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.database.models import FileChangeProposal, Workspace
from app.workspace.change_repository import FileChangeProposalRepository
from app.workspace.file_service import (
    WorkspaceFileService,
    MAX_FILE_SIZE_BYTES,
    PathTraversalError,
    FileNotFoundInWorkspaceError,
    IsADirectoryError,
    FileTooLargeError,
    FileEncodingError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProposalNotFoundError(Exception):
    """Raised when a proposal does not exist or user doesn't own it."""
    pass


class ProposalAccessDeniedError(Exception):
    """Raised when a user tries to access a proposal they do not own."""
    pass


class ProposalStatusError(Exception):
    """Raised when an operation is invalid for the proposal's current status."""
    pass


class StaleFileError(Exception):
    """Raised when the target file has changed since the proposal was created."""
    pass


class ProposalExecutionError(Exception):
    """Raised when applying the proposal to disk fails."""
    pass


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def calculate_content_hash(content: str) -> str:
    """Compute deterministic SHA-256 hex digest of UTF-8 encoded text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_unified_diff(original: str, proposed: str, file_path: str) -> str:
    """Generate a standard unified diff between original and proposed content."""
    original_lines = original.splitlines(keepends=True)
    proposed_lines = proposed.splitlines(keepends=True)

    diff = "".join(
        difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
    )
    return diff


# ---------------------------------------------------------------------------
# Proposal Service
# ---------------------------------------------------------------------------


class FileChangeProposalService:
    """Service orchestrating safe file modification proposals and approvals."""

    def __init__(self, repository: FileChangeProposalRepository) -> None:
        self.repository = repository

    async def create_proposal(
        self,
        workspace: Workspace,
        user_id: str,
        file_path: str,
        proposed_content: str,
    ) -> FileChangeProposal:
        """Create a new file change proposal.

        Validations:
        1. Workspace ownership enforced (user_id must match workspace.user_id).
        2. Safe relative path validation (traversal blocked).
        3. Target file must exist and be a regular file.
        4. Target file size must not exceed MAX_FILE_SIZE_BYTES.
        5. Target file must be decodable as UTF-8.
        6. Proposed content size must not exceed MAX_FILE_SIZE_BYTES.
        7. SHA-256 hashes generated for both original and proposed content.
        8. Exact unified diff generated and persisted.
        9. Status set to 'pending'.
        """
        if workspace.user_id != user_id:
            raise ProposalAccessDeniedError("You do not own this workspace.")

        if not file_path or not file_path.strip():
            raise FileNotFoundInWorkspaceError("File path must not be empty.")

        # Proposed content size check
        proposed_bytes = proposed_content.encode("utf-8")
        if len(proposed_bytes) > MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"Proposed content is {len(proposed_bytes)} bytes, which exceeds the "
                f"{MAX_FILE_SIZE_BYTES // 1024} KB limit."
            )

        # Read existing file safely via WorkspaceFileService
        file_service = WorkspaceFileService(workspace)
        file_info = file_service.read_file(file_path)
        original_content = file_info["content"]
        clean_relative_path = file_info["path"]

        # Calculate hashes
        orig_hash = calculate_content_hash(original_content)
        prop_hash = calculate_content_hash(proposed_content)

        # Generate exact unified diff
        diff = generate_unified_diff(original_content, proposed_content, clean_relative_path)

        proposal = FileChangeProposal(
            workspace_id=workspace.id,
            user_id=user_id,
            file_path=clean_relative_path,
            original_content_hash=orig_hash,
            proposed_content_hash=prop_hash,
            original_content=original_content,
            proposed_content=proposed_content,
            diff=diff,
            status="pending",
        )

        saved = await self.repository.create(proposal)
        logger.info(
            "Created change proposal id=%s workspace_id=%s file=%s user_id=%s",
            saved.id, workspace.id, clean_relative_path, user_id,
        )
        return saved

    async def get_proposal(
        self,
        workspace: Workspace,
        user_id: str,
        proposal_id: str,
    ) -> FileChangeProposal:
        """Retrieve a single proposal, enforcing ownership and workspace match."""
        if workspace.user_id != user_id:
            raise ProposalAccessDeniedError("You do not own this workspace.")

        proposal = await self.repository.get_by_id(proposal_id)
        if (
            proposal is None
            or proposal.workspace_id != workspace.id
            or proposal.user_id != user_id
        ):
            raise ProposalNotFoundError(f"Proposal '{proposal_id}' not found.")

        return proposal

    async def list_proposals(
        self,
        workspace: Workspace,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[FileChangeProposal]:
        """List proposals for a workspace owned by the authenticated user."""
        if workspace.user_id != user_id:
            raise ProposalAccessDeniedError("You do not own this workspace.")

        return await self.repository.list_by_workspace(workspace.id, status=status)

    async def reject_proposal(
        self,
        workspace: Workspace,
        user_id: str,
        proposal_id: str,
    ) -> FileChangeProposal:
        """Explicitly reject a proposal. Files are NOT modified."""
        proposal = await self.get_proposal(workspace, user_id, proposal_id)

        if proposal.status != "pending":
            raise ProposalStatusError(
                f"Cannot reject proposal with status '{proposal.status}'. "
                f"Only pending proposals can be rejected."
            )

        proposal.status = "rejected"
        proposal.rejected_at = datetime.utcnow()
        updated = await self.repository.update(proposal)

        logger.info(
            "Rejected change proposal id=%s workspace_id=%s file=%s user_id=%s",
            updated.id, workspace.id, updated.file_path, user_id,
        )
        return updated

    async def approve_and_apply_proposal(
        self,
        workspace: Workspace,
        user_id: str,
        proposal_id: str,
    ) -> FileChangeProposal:
        """Approve and apply a pending proposal atomically.

        Security & Integrity:
        1. User ownership and workspace match enforced.
        2. Proposal must be in 'pending' status.
        3. Stale file protection: Re-reads current file and checks SHA-256 against
           original_content_hash. If different, aborts and marks proposal as failed.
        4. Atomic write: Writes proposed content to a temporary file in the same
           directory, fsyncs, and uses os.replace to prevent partial writes.
        5. Updates status to 'applied', records approved_at and applied_at.
        """
        proposal = await self.get_proposal(workspace, user_id, proposal_id)

        if proposal.status != "pending":
            raise ProposalStatusError(
                f"Cannot approve proposal with status '{proposal.status}'. "
                f"Only pending proposals can be approved."
            )

        # Resolve target path safely
        file_service = WorkspaceFileService(workspace)
        try:
            target_path = file_service._resolve_safe_path(proposal.file_path)
        except PathTraversalError as exc:
            proposal.status = "failed"
            await self.repository.update(proposal)
            raise ProposalExecutionError(f"Invalid path: {exc}") from exc

        if not target_path.exists() or not target_path.is_file():
            proposal.status = "failed"
            await self.repository.update(proposal)
            raise ProposalExecutionError(
                f"Target file '{proposal.file_path}' no longer exists as a regular file."
            )

        # Stale file check
        try:
            current_content = target_path.read_text(encoding="utf-8", errors="strict")
        except Exception as exc:
            proposal.status = "failed"
            await self.repository.update(proposal)
            raise ProposalExecutionError(f"Cannot read current file: {exc}") from exc

        current_hash = calculate_content_hash(current_content)
        if current_hash != proposal.original_content_hash:
            proposal.status = "failed"
            await self.repository.update(proposal)
            logger.warning(
                "Stale file detected for proposal id=%s: expected hash=%s got=%s",
                proposal.id, proposal.original_content_hash, current_hash,
            )
            raise StaleFileError(
                "File has been modified since this proposal was created. "
                "The proposal is stale and cannot be safely applied."
            )

        # Atomic write
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target_path.parent,
            prefix=".tmp_devagent_",
            delete=False,
        )
        temp_path = Path(temp_file.name)
        try:
            temp_file.write(proposal.proposed_content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()

            # Atomically replace destination
            os.replace(temp_path, target_path)
        except Exception as exc:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            proposal.status = "failed"
            await self.repository.update(proposal)
            logger.error("Atomic write failed for proposal id=%s: %s", proposal.id, exc)
            raise ProposalExecutionError(f"Failed to atomically write file: {exc}") from exc

        now = datetime.utcnow()
        proposal.status = "applied"
        proposal.approved_at = now
        proposal.applied_at = now
        updated = await self.repository.update(proposal)

        logger.info(
            "Approved and applied change proposal id=%s workspace_id=%s file=%s user_id=%s",
            updated.id, workspace.id, updated.file_path, user_id,
        )
        return updated
