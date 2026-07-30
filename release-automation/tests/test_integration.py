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

    def test_redis_version_subcommand(self):
        """Test redis-version compatibility subcommand used by CI."""
        result = self.runner.invoke(app, ["redis-version", "major", "8.2.1"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "8"

    def test_invalid_major_version(self):
        """Test handling of invalid major version."""
        result = self.runner.invoke(app, ["generate-stackbrew-content", "0"])
        assert result.exit_code != 0

    @patch("stackbrew_generator.cli.GitClient")
    def test_no_tags_found(self, mock_git_client_class):
        """Test handling when no tags are found."""
        # Mock git client to return no tags
        mock_git_client = Mock()
        mock_git_client_class.return_value = mock_git_client
        mock_git_client.list_remote_tags.return_value = []

        result = self.runner.invoke(app, ["generate-stackbrew-content", "99"])
        assert result.exit_code == 1
        assert "No versions found for major version 99" in result.stderr

    @patch("stackbrew_generator.cli.GitClient")
    @patch(
        "stackbrew_generator.version_filter.VersionFilter.get_actual_major_redis_versions"
    )
    def test_no_versions_found(self, mock_get_versions, mock_git_client_class):
        """Test handling when no versions are found."""
        mock_git_client = Mock()
        mock_git_client.get_highest_remote_ga_major_version.return_value = 8
        mock_git_client_class.return_value = mock_git_client
        mock_get_versions.return_value = []

        result = self.runner.invoke(app, ["generate-stackbrew-content", "8"])
        assert result.exit_code == 1
        assert "No versions found" in result.stderr

    def test_help_output(self):
        """Test help output."""
        result = self.runner.invoke(app, ["generate-stackbrew-content", "--help"])
        assert result.exit_code == 0
        assert "Generate stackbrew library content" in result.stdout
        assert "--remote" in result.stdout
        assert "--verbose" in result.stdout
