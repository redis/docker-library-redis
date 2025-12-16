"""Tests for update-stackbrew-file command."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from stackbrew_generator.cli import app
from stackbrew_generator.models import RedisVersion, Distribution, DistroType, Release


class TestUpdateStackbrewFile:
    """Tests for update-stackbrew-file command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_update_stackbrew_file_basic(self):
        """Test basic stackbrew file update functionality."""
        # Create a sample stackbrew file
        sample_content = """# This file was generated via https://github.com/redis/docker-library-redis/blob/abc123/generate-stackbrew-library.sh

Maintainers: David Maier <david.maier@redis.com> (@dmaier-redislabs),
             Yossi Gottlieb <yossi@redis.com> (@yossigo)
GitRepo: https://github.com/redis/docker-library-redis.git

Tags: 8.2.1, 8.2, 8, 8.2.1-bookworm, 8.2-bookworm, 8-bookworm, latest, bookworm
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, mips64le, ppc64le, s390x
GitCommit: old123commit
GitFetch: refs/tags/v8.2.1
Directory: debian

Tags: 8.2.1-alpine, 8.2-alpine, 8-alpine, 8.2.1-alpine3.22, 8.2-alpine3.22, 8-alpine3.22, alpine, alpine3.22
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, riscv64, ppc64le, s390x
GitCommit: old123commit
GitFetch: refs/tags/v8.2.1
Directory: alpine

Tags: 7.4.0, 7.4, 7, 7.4.0-bookworm, 7.4-bookworm, 7-bookworm
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, mips64le, ppc64le, s390x
GitCommit: old456commit
GitFetch: refs/tags/v7.4.0
Directory: debian
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_content)
            input_file = Path(f.name)

        try:
            with patch('stackbrew_generator.cli.DistributionDetector') as mock_detector_class, \
                 patch('stackbrew_generator.cli.GitClient') as mock_git_client_class, \
                 patch('stackbrew_generator.cli.VersionFilter') as mock_version_filter_class:

                # Mock git client
                mock_git_client = Mock()
                mock_git_client_class.return_value = mock_git_client

                # Mock distribution detector
                mock_distribution_detector = Mock()
                mock_detector_class.return_value = mock_distribution_detector

                # Mock version filter
                mock_version_filter = Mock()
                mock_version_filter_class.return_value = mock_version_filter

                # Mock the version filter to return Redis 8.x versions
                mock_version_filter.get_actual_major_redis_versions.return_value = [
                    (RedisVersion.parse("8.2.2"), "new123commit", "refs/tags/v8.2.2")
                ]

                # Mock releases
                mock_releases = [
                    Release(
                        commit="new123commit",
                        version=RedisVersion.parse("8.2.2"),
                        distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                        git_fetch_ref="refs/tags/v8.2.2"
                    )
                ]
                mock_distribution_detector.prepare_releases_list.return_value = mock_releases

                # Run the command with output to file
                result = self.runner.invoke(app, [
                    "update-stackbrew-file",
                    "8",
                    "--input", str(input_file),
                    "--output", str(input_file),
                    "--verbose"
                ])

                assert result.exit_code == 0

                # Check that the file was updated
                updated_content = input_file.read_text()

                # Should still have the header
                assert "Maintainers: David Maier" in updated_content
                assert "GitRepo: https://github.com/redis/docker-library-redis.git" in updated_content

                # Should have new Redis 8.x content
                assert "new123commit" in updated_content
                assert "8.2.2" in updated_content

                # Should still have Redis 7.x content (unchanged)
                assert "7.4.0" in updated_content
                assert "old456commit" in updated_content

                # Should not have old Redis 8.x content
                assert "old123commit" not in updated_content
                assert "8.2.1" not in updated_content

        finally:
            input_file.unlink()

    def test_update_stackbrew_file_nonexistent_input(self):
        """Test error handling for nonexistent input file."""
        result = self.runner.invoke(app, [
            "update-stackbrew-file",
            "8",
            "--input", "/nonexistent/file.txt"
        ])

        assert result.exit_code == 1
        assert "Input file does not exist" in result.stderr

    def test_update_stackbrew_file_no_versions_found(self):
        """Test error handling when no versions are found."""
        sample_content = """# Header
Maintainers: Test
GitRepo: https://example.com
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_content)
            input_file = Path(f.name)

        try:
            with patch('stackbrew_generator.cli.GitClient') as mock_git_client_class, \
                 patch('stackbrew_generator.cli.VersionFilter') as mock_version_filter_class:

                mock_git_client = Mock()
                mock_git_client_class.return_value = mock_git_client

                mock_version_filter = Mock()
                mock_version_filter_class.return_value = mock_version_filter
                mock_version_filter.get_actual_major_redis_versions.return_value = []

                result = self.runner.invoke(app, [
                    "update-stackbrew-file",
                    "9",
                    "--input", str(input_file)
                ])

                assert result.exit_code == 1
                assert "No versions found for Redis 9.x" in result.stderr

        finally:
            input_file.unlink()

    def test_update_stackbrew_file_with_output_option(self):
        """Test using separate output file."""
        sample_content = """# Header
Maintainers: Test
GitRepo: https://example.com

Tags: 8.1.0, 8.1, 8.1.0-bookworm, 8.1-bookworm
Architectures: amd64
GitCommit: old123
GitFetch: refs/tags/v8.1.0
Directory: debian
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as input_f, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as output_f:

            input_f.write(sample_content)
            input_file = Path(input_f.name)
            output_file = Path(output_f.name)

        try:
            with patch('stackbrew_generator.cli.DistributionDetector') as mock_detector_class, \
                 patch('stackbrew_generator.cli.GitClient') as mock_git_client_class, \
                 patch('stackbrew_generator.cli.VersionFilter') as mock_version_filter_class:

                # Setup mocks
                mock_git_client = Mock()
                mock_git_client_class.return_value = mock_git_client

                mock_distribution_detector = Mock()
                mock_detector_class.return_value = mock_distribution_detector

                mock_version_filter = Mock()
                mock_version_filter_class.return_value = mock_version_filter
                mock_version_filter.get_actual_major_redis_versions.return_value = [
                    (RedisVersion.parse("8.2.0"), "new456commit", "refs/tags/v8.2.0")
                ]

                mock_releases = [
                    Release(
                        commit="new456commit",
                        version=RedisVersion.parse("8.2.0"),
                        distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                        git_fetch_ref="refs/tags/v8.2.0"
                    )
                ]
                mock_distribution_detector.prepare_releases_list.return_value = mock_releases

                result = self.runner.invoke(app, [
                    "update-stackbrew-file",
                    "8",
                    "--input", str(input_file),
                    "--output", str(output_file)
                ])

                assert result.exit_code == 0

                # Original file should be unchanged
                original_content = input_file.read_text()
                assert "old123" in original_content

                # Output file should have updated content
                updated_content = output_file.read_text()
                assert "new456commit" in updated_content
                assert "8.2.0" in updated_content
                assert "old123" not in updated_content

        finally:
            input_file.unlink()
            output_file.unlink()

    def test_update_stackbrew_file_stdout_output(self):
        """Test outputting to stdout when no output file is specified."""
        sample_content = """# Header
Maintainers: Test
GitRepo: https://example.com

Tags: 8.1.0, 8.1, 8.1.0-bookworm, 8.1-bookworm
Architectures: amd64
GitCommit: old123
GitFetch: refs/tags/v8.1.0
Directory: debian
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_content)
            input_file = Path(f.name)

        try:
            with patch('stackbrew_generator.cli.DistributionDetector') as mock_detector_class, \
                 patch('stackbrew_generator.cli.GitClient') as mock_git_client_class, \
                 patch('stackbrew_generator.cli.VersionFilter') as mock_version_filter_class:

                # Setup mocks
                mock_git_client = Mock()
                mock_git_client_class.return_value = mock_git_client

                mock_distribution_detector = Mock()
                mock_detector_class.return_value = mock_distribution_detector

                mock_version_filter = Mock()
                mock_version_filter_class.return_value = mock_version_filter
                mock_version_filter.get_actual_major_redis_versions.return_value = [
                    (RedisVersion.parse("8.2.0"), "new789commit", "refs/tags/v8.2.0")
                ]

                mock_releases = [
                    Release(
                        commit="new789commit",
                        version=RedisVersion.parse("8.2.0"),
                        distribution=Distribution(type=DistroType.DEBIAN, name="bookworm"),
                        git_fetch_ref="refs/tags/v8.2.0"
                    )
                ]
                mock_distribution_detector.prepare_releases_list.return_value = mock_releases

                result = self.runner.invoke(app, [
                    "update-stackbrew-file",
                    "8",
                    "--input", str(input_file)
                ])

                assert result.exit_code == 0

                # Should output to stdout
                assert "new789commit" in result.stdout
                assert "8.2.0" in result.stdout

                # Original file should be unchanged
                original_content = input_file.read_text()
                assert "old123" in original_content

        finally:
            input_file.unlink()
