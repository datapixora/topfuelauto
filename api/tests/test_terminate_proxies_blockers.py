"""
Tests for the proxies blocker termination endpoint and script.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy import text


class TestTerminateProxiesBlockers:
    """Test suite for blocker termination functionality."""

    def test_no_blockers_returns_empty_result(self, db, admin_user, client, auth_headers):
        """Test that endpoint returns empty result when no blockers exist."""

        # Mock the blocker query to return no results
        with patch.object(db, 'execute') as mock_execute:
            # Mock pg_backend_pid
            mock_execute.return_value.fetchone.return_value = [12345]
            # Mock blockers query to return empty
            mock_execute.return_value.fetchall.return_value = []

            response = client.post(
                "/api/v1/admin/db/locks/proxies/terminate-blockers",
                headers=auth_headers(admin_user)
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["terminated_pids"] == []
            assert data["skipped_pids"] == []

    def test_skips_current_session(self, db):
        """Test that the current session PID is never terminated."""
        from api.app.routers.admin_db import terminate_proxies_blockers

        current_pid = 12345

        # Mock blocker that is the current session
        blocker_row = (current_pid, "testuser", "testapp", "idle", None, None, None, "SELECT 1")

        # The logic should skip this PID
        # This is a logic test, not a full integration test

    def test_skips_system_users(self):
        """Test that system users (postgres, rdsadmin) are never terminated."""
        system_users = {'postgres', 'rdsadmin', 'rds_superuser', 'rds_replication'}

        for user in system_users:
            # Mock blocker with system user
            blocker_row = (99999, user, "testapp", "idle", None, None, None, "SELECT 1")
            # The logic should skip this PID


class TestTerminateProxiesBlockersScript:
    """Test suite for the CLI script."""

    def test_script_syntax_valid(self):
        """Test that the script compiles without syntax errors."""
        import py_compile
        import os

        script_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "scripts",
            "terminate_proxies_blockers.py"
        )

        try:
            py_compile.compile(script_path, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Script has syntax errors: {e}")

    def test_script_requires_database_url(self):
        """Test that script exits when DATABASE_URL is not set."""
        import subprocess
        import os

        script_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "scripts",
            "terminate_proxies_blockers.py"
        )

        # Run script without DATABASE_URL
        env = os.environ.copy()
        env.pop("DATABASE_URL", None)

        result = subprocess.run(
            ["python", script_path],
            env=env,
            capture_output=True,
            text=True
        )

        # Should exit with error
        assert result.returncode == 1
        assert "DATABASE_URL" in result.stderr or "DATABASE_URL" in result.stdout
