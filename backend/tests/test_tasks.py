"""
Tests for the Celery background worker tasks — Phase 7.
"""

import pytest
from datetime import datetime
from unittest import mock
from unittest.mock import patch, MagicMock

from app.workers.tasks import run_agent_task, _get_sync_session
from app.database.models import Job

@pytest.fixture
def sync_db_session(setup_test_db):
    """Reuse the async session's underlying SQLite DB but via the sync engine."""
    # This is a bit tricky because setup_test_db is async.
    # For a simple mock test, we can just mock out _get_sync_session and return 
    # a MagicMock or rely on the async session if we patch the task to use it.
    pass

@patch("app.workers.tasks._get_sync_session")
@patch("app.workers.tasks._run_agent_pipeline")
def test_run_agent_task_success(mock_pipeline, mock_get_session):
    """Test successful execution of a background task."""
    mock_pipeline.return_value = "Task completed successfully"
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    
    # Mock the database job
    mock_job = MagicMock(spec=Job)
    mock_job.id = "test-job-1"
    mock_job.status = "pending"
    mock_job.input = "Do some work"
    
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_job
    
    # Run task
    result = run_agent_task(job_id="test-job-1")
    
    # Assertions
    assert result == {"status": "completed", "job_id": "test-job-1"}
    assert mock_job.status == "completed"
    assert mock_job.result == "Task completed successfully"
    mock_session.commit.assert_called()
    mock_pipeline.assert_called_once_with("Do some work", session=mock.ANY, trace=mock.ANY)

@patch("app.workers.tasks._get_sync_session")
@patch("app.workers.tasks._run_agent_pipeline")
def test_run_agent_task_failure(mock_pipeline, mock_get_session):
    """Test background task failure."""
    mock_pipeline.side_effect = Exception("LLM connection failed")
    
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    
    mock_job = MagicMock(spec=Job)
    mock_job.id = "test-job-2"
    mock_job.status = "pending"
    mock_job.input = "Do some work"
    
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_job
    
    # Run task
    result = run_agent_task(job_id="test-job-2")
    
    assert result["status"] == "failed"
    assert result["job_id"] == "test-job-2"
    assert "LLM connection failed" in result["error"]
    assert mock_job.status == "failed"
    mock_session.commit.assert_called()

@patch("app.workers.tasks._get_sync_session")
def test_run_agent_task_cancelled(mock_get_session):
    """Test that cancelled jobs are skipped."""
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    
    mock_job = MagicMock(spec=Job)
    mock_job.id = "test-job-3"
    mock_job.status = "cancelled"
    
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    mock_filter.first.return_value = mock_job
    
    result = run_agent_task(job_id="test-job-3")
    
    assert result == {"status": "cancelled"}
    # Should not transition to running or call pipeline
    assert mock_job.status == "cancelled"
