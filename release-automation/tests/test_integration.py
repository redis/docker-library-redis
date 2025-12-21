"""Integration tests for the stackbrew generator."""

import pytest
from unittest.mock import Mock, patch

from stackbrew_generator.cli import app
from stackbrew_generator.models import RedisVersion, Distribution, DistroType
from typer.testing import CliRunner


class TestIntegration:
    """Integration tests for the complete workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "stackbrew-library-generator" in result.stderr

    def test_invalid_major_version(self):
        """Test handling of invalid major version."""
        result = self.runner.invoke(app, ["generate-stackbrew-content", "0"])
        assert result.exit_code != 0

    @patch('stackbrew_generator.cli.GitClient')
    def test_no_tags_found(self, mock_git_client_class):
        """Test handling when no tags are found."""
        # Mock git client to return no tags
        mock_git_client = Mock()
        mock_git_client_class.return_value = mock_git_client
        mock_git_client.list_remote_tags.return_value = []

        result = self.runner.invoke(app, ["generate-stackbrew-content", "99"])
        assert result.exit_code == 1
        assert "No versions found for major version 99" in result.stderr

    @patch('stackbrew_generator.version_filter.VersionFilter.get_actual_major_redis_versions')
    def test_no_versions_found(self, mock_get_versions):
        """Test handling when no versions are found."""
        # Mock git client to return no tags
        mock_get_versions.return_value = []

        result = self.runner.invoke(app, ["generate-stackbrew-content", "8"])
        #assert result.exit_code == 1
        assert "No versions found" in result.stderr

    def test_help_output(self):
        """Test help output."""
        result = self.runner.invoke(app, ["generate-stackbrew-content", "--help"])
        assert result.exit_code == 0
        assert "Generate stackbrew library content" in result.stdout
        assert "--remote" in result.stdout
        assert "--verbose" in result.stdout
