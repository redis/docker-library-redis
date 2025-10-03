"""Tests for git operations."""

from unittest.mock import Mock, patch

from stackbrew_generator.git_operations import GitClient


class TestGitClient:
    """Tests for GitClient class."""

    @patch('stackbrew_generator.git_operations.console')
    @patch.object(GitClient, '_run_command')
    def test_list_remote_tags(self, mock_run_command, mock_console):
        """
        Test that list_remote_tags returns the expected format for peeled refs.

        For tags with ^{} suffix, use the commit hash from that line.
        For tags without ^{} suffix, use the commit hash from the tag line.
        """
        mock_result = Mock()
        mock_result.stdout = """101262a8cf05b98137d88bc17e77db90c24cc783\trefs/tags/v8.0.3
2277e5ead99f0caacbd90e0d04693adb27ebfaa6\trefs/tags/v8.0.4^{}
c0125f5be8786d556a9d3edd70f51974fe045c1a\trefs/tags/v8.0.4
f76d8a1cc979be6202aed93efddd2a0ebbfa0209\trefs/tags/v8.2.2
c5846c13383c8b284897ff171e0c946868ed4c8c\trefs/tags/v8.2.2^{}"""
        mock_run_command.return_value = mock_result

        client = GitClient()
        result = client.list_remote_tags(8)

        # Expected behavior:
        # - v8.0.3 has no peeled ref, so use the tag commit
        # - v8.0.4 has a peeled ref, so use the peeled commit (2277e5ead99f0caacbd90e0d04693adb27ebfaa6)
        # - v8.2.2 has a peeled ref, so use the peeled commit (c5846c13383c8b284897ff171e0c946868ed4c8c)
        expected_result = [
            ("101262a8cf05b98137d88bc17e77db90c24cc783", "refs/tags/v8.0.3"),  # No peeled ref
            ("2277e5ead99f0caacbd90e0d04693adb27ebfaa6", "refs/tags/v8.0.4"),  # Use peeled ref
            ("c5846c13383c8b284897ff171e0c946868ed4c8c", "refs/tags/v8.2.2")   # Use peeled ref
        ]

        assert result == expected_result
