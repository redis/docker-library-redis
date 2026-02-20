"""Tests for generate-image-tags CLI command."""

from unittest.mock import patch

from typer.testing import CliRunner

from stackbrew_generator.cli import app

runner = CliRunner()

SAMPLE_STACKBREW_OUTPUT = """\
Tags: 8.6.0, 8.6, 8, 8.6.0-trixie, 8.6-trixie, 8-trixie, latest, trixie
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, riscv64, ppc64le, s390x
GitCommit: abc123
GitFetch: refs/tags/v8.6.0
Directory: debian

Tags: 8.6.0-alpine, 8.6-alpine, 8-alpine, 8.6.0-alpine3.23, 8.6-alpine3.23, 8-alpine3.23, alpine, alpine3.23
Architectures: amd64, arm32v6, arm32v7, arm64v8, i386, ppc64le, riscv64, s390x
GitCommit: abc123
GitFetch: refs/tags/v8.6.0
Directory: alpine"""

SAMPLE_RC_OUTPUT = """\
Tags: 8.6.0-rc1, 8.6.0-rc1-trixie
Architectures: amd64, arm32v5, arm32v7, arm64v8, i386, riscv64, ppc64le, s390x
GitCommit: def456
GitFetch: refs/tags/v8.6.0-rc1
Directory: debian

Tags: 8.6.0-rc1-alpine, 8.6.0-rc1-alpine3.23
Architectures: amd64, arm32v6, arm32v7, arm64v8, i386, ppc64le, riscv64, s390x
GitCommit: def456
GitFetch: refs/tags/v8.6.0-rc1
Directory: alpine"""


class TestGenerateImageTags:
    """Tests for the generate-image-tags command."""

    def test_debian_ga_latest(self):
        """Debian GA version that is latest gets full tags including 'latest'."""
        with patch("stackbrew_generator.cli._generate_stackbrew_content", return_value=SAMPLE_STACKBREW_OUTPUT):
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "debian"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0" in tags
            assert "8.6" in tags
            assert "8" in tags
            assert "latest" in tags
            distro_tags = [t for t in tags if "trixie" in t]
            assert len(distro_tags) > 0

    def test_alpine_ga_latest(self):
        """Alpine GA version that is latest gets alpine-prefixed tags."""
        with patch("stackbrew_generator.cli._generate_stackbrew_content", return_value=SAMPLE_STACKBREW_OUTPUT):
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "alpine"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0" not in tags
            assert "latest" not in tags
            assert "alpine" in tags
            alpine_version_tags = [t for t in tags if t.startswith("8.6.0-alpine")]
            assert len(alpine_version_tags) > 0

    def test_milestone_version(self):
        """Milestone version should not get mainline or major tags."""
        with patch("stackbrew_generator.cli._generate_stackbrew_content", return_value=SAMPLE_RC_OUTPUT):
            result = runner.invoke(app, ["generate-image-tags", "8.6.0-rc1", "debian"])
            assert result.exit_code == 0
            tags = [t.strip() for t in result.stdout.strip().split(",")]
            assert "8.6.0-rc1" in tags
            assert "8.6" not in tags
            assert "8" not in tags

    def test_invalid_version(self):
        """Invalid version exits with error."""
        result = runner.invoke(app, ["generate-image-tags", "invalid", "debian"])
        assert result.exit_code == 1

    def test_version_not_found(self):
        """Version that doesn't match any entry returns empty output."""
        with patch("stackbrew_generator.cli._generate_stackbrew_content", return_value=SAMPLE_STACKBREW_OUTPUT):
            result = runner.invoke(app, ["generate-image-tags", "8.6.0", "nonexistent"])
            assert result.exit_code == 0
            assert result.stdout.strip() == ""

    def test_no_versions_found(self):
        """No versions found for major version exits with error."""
        with patch("stackbrew_generator.cli._generate_stackbrew_content", side_effect=SystemExit(1)):
            result = runner.invoke(app, ["generate-image-tags", "9.0.0", "debian"])
            assert result.exit_code == 1
